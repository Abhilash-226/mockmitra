"""
Gemini Vision-based PYQ Extractor.
Extracts questions from PDF exam papers using Google's Gemini Vision API.
"""
import json
import base64
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
import difflib
import re

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Please install google-genai: pip install google-genai")
    raise

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Please install PyMuPDF: pip install pymupdf")
    raise

from .config import ExamConfig, GEMINI_API_KEY
from .utils import parse_pdf_filename, generate_paper_id, sanitize_text, estimate_section


class GeminiExtractor:
    """
    Extracts questions from PDF papers using Gemini Vision.
    """
    
    def __init__(self, exam_config: ExamConfig, api_key: Optional[str] = None):
        self.config = exam_config
        
        # Load backend settings for GCP/API keys
        from app.core.config import settings
        
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.project = settings.GOOGLE_CLOUD_PROJECT
        self.location = settings.GOOGLE_CLOUD_LOCATION
        
        # Initialize Gemini client
        try:
            if self.project:
                print(f"Initializing Extractor via Vertex AI (Project: {self.project})")
                self.client = genai.Client(
                    vertexai=True,
                    project=self.project,
                    location=self.location
                )
                self.model_name = "gemini-2.0-flash-001"
            else:
                print("Initializing Extractor via API Key")
                self.client = genai.Client(api_key=self.api_key)
                self.model_name = "gemini-1.5-flash"
        except Exception as e:
            print(f"Failed to initialize Gemini client: {e}")
            self.client = None
            
        # Ensure directories exist
        self.config.ensure_dirs()
    
    def _pdf_to_images(self, pdf_path: Path, dpi: int = 150) -> List[bytes]:
        """
        Convert PDF pages to images.
        
        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for conversion
        
        Returns:
            List of image bytes (PNG format)
        """
        doc = fitz.open(pdf_path)
        images = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Higher DPI = better quality but larger size
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            images.append(pix.tobytes("png"))
        
        doc.close()
        return images
    
    def _load_topics(self) -> Dict[str, Any]:
        """Load valid topics and build a section->subject reverse map."""
        result = {
            "hierarchy": {},
            "section_to_subject": {}
        }
        try:
            config_path = Path(__file__).parent.parent.parent.parent / "backend" / "exam_configs" / f"{self.config.code}.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    cfg = yaml.safe_load(f)
                    for subject in cfg.get('subjects', []):
                        sub_name = subject.get('name')
                        result["hierarchy"][sub_name] = {
                            "sections": {}
                        }
                        for section in subject.get('sections', []):
                            sec_name = section.get('name')
                            result["hierarchy"][sub_name]["sections"][sec_name] = section.get('topics', [])
                            # Reverse map for robust subject correction
                            result["section_to_subject"][sec_name.lower()] = sub_name
        except Exception as e:
            print(f"Warning: Could not load topics hierarchy: {e}")
        return result

    def _clean_math_syntax(self, text: str) -> str:
        """Fix common Gemini hallucinations in LaTeX and ensure formatting."""
        if not text: return text
        
        # 1. Fix 'frac(a, b)' or 'frac(a/b)' -> \frac{a}{b}
        # Matches: frac(5, 3), frac(5/3), frac ( 5 / 3 )
        text = re.sub(r'frac\s*\(\s*([^,/]+)\s*[/,]\s*([^)]+)\s*\)', r'\\frac{\1}{\2}', text)
        
        # 2. Fix 'sqrt(x)' -> \sqrt{x}
        text = re.sub(r'sqrt\s*\(([^)]+)\)', r'\\sqrt{\1}', text)
        
        # 3. Ensure math sequences are wrapped in $
        # Look for typical math symbols/keywords that aren't wrapped
        math_keywords = [r'\\frac', r'\\sqrt', r'\\alpha', r'\\beta', r'\\gamma', r'\\theta', r'\\infty', r'\\pm', r'\\times']
        for kw in math_keywords:
            # Wrap keyword and its following block if not already inside $...$
            # This is a bit simplified; better to detect blocks
            pass # Skipping complex auto-wrapping for now to avoid breaking text

        # 4. Fix double-wrapped math like $$...$$
        text = text.replace('$$', '$')
        
        # 5. Fix common hallucination: "Option A", "Option B" in options
        if text.strip() in ["Option A", "Option B", "Option C", "Option D", "Refer to Image"]:
            return "UNREADABLE_IMAGE"

        return text

    def _create_extraction_prompt(self, hierarchy: Dict[str, Any], last_question_text: str = "None", last_question_id: Optional[int] = None, target_id: Optional[int] = None) -> str:
        """Create the prompt for Gemini to extract questions with full hierarchy knowledge."""
        
        guidance = "STRICT SUBJECT/SECTION/TOPIC HIERARCHY:\n"
        for sub, data in hierarchy.items():
            guidance += f"- Subject: {sub}\n"
            for sec, topics in data["sections"].items():
                guidance += f"  - Section: {sec}\n"
                guidance += f"    - Valid Topics: {', '.join(topics)}\n"

        target_instruction = ""
        if target_id:
            target_instruction = f"FOCUS: You MUST find and extract ONLY Question Number {target_id}. Ignore other questions unless they provide context for this one."
        else:
            target_instruction = "TASK: Extract ALL questions that START on Image 1."

        continuity_id_str = f"Q{last_question_id}" if last_question_id else "None"

        return f"""You are an expert at extracting exam questions from scanned PDF images.

{guidance}

{target_instruction}

⚠ STRICT QUESTION BOUNDARY — READ CAREFULLY:
1. A question STRICTLY begins with the header "Question Number : X" (where X is the **original PDF question number**).
2. The valid question ID range is {self.config.id_range_start} to {self.config.id_range_end}. NEVER output a question with an ID outside this range.
3. You MUST extract the question number exactly as it appears in the PDF header "Question Number : X".
4. ONLY extract questions whose header "Question Number : X" is visually present on Image 1.
5. DO NOT invent, guess, or hallucinate question numbers. If you cannot see a header clearly, skip that question.
6. "Prior Text": Any text ABOVE the first header on Image 1 belongs to question {continuity_id_str} (use pre_header_options).
7. "Cross-Page Options": If Image 1 starts with options before any header, they belong to {continuity_id_str}.
8. From Image 2: Only use it to get the REMAINDER of a question that STARTED on Image 1.
9. DO NOT re-extract the last question: ID {continuity_id_str}, text preview: "{last_question_text}"

CONTENT RULES:
10. Clean Text: Do NOT include "Question Number", "Question Id", or any metadata in the "text" field.
11. Subject/Section/Topic: Must match the STRICT HIERARCHY above.
12. LaTeX (VITAL): Use $...$ for ALL math. Standard LaTeX only: \\\\frac{{a}}{{b}}, \\\\sqrt{{x}}, \\\\alpha, \\\\infty, \\\\pm.
13. Options: Extract all 4 options as A, B, C, D. DO NOT use placeholders like "Option A". If an option is purely an image that cannot be described, use "IMAGE_CONTENT".
14. NO Telugu: Extract ONLY English text. Ignore Telugu script.
15. If a question is incomplete (cut off at bottom of Image 2), add "status": "incomplete".

OUTPUT FORMAT (strict JSON):
{{
  "pre_header_options": {{ "A": "...", "B": "...", "C": "...", "D": "..." }},
  "questions": [
    {{
      "number": <exact PDF question number, integer>,
      "subject": "Mathematics",
      "section": "<exact section name>",
      "topic": "<exact topic slug>",
      "text": "<question text>",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "correct_answer": "A",
      "difficulty": "moderate"
    }}
  ]
}}
"""

    def extract_paper(self, pdf_filename: str, delay_between_pages: float = 3.0) -> Dict[str, Any]:
        """Extract and map questions using dynamic config."""
        topics_data = self._load_topics()
        subjects_topics = topics_data["hierarchy"]
        
        pdf_path = self.config.pdfs_dir / pdf_filename
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        year = int(pdf_filename.split('-')[0])
        shift = int(pdf_filename.split('-')[1].split('.')[0])
        paper_id = f"{self.config.code}_{year}_{shift}"
        
        print(f"\n🚀 Starting Extraction: {pdf_filename} (ID: {paper_id})")
        
        # Convert PDF to images
        images = self._pdf_to_images(pdf_path)
        print(f"  Total pages to process: {len(images)}")
        
        # ID-Based Storage: Dict keyed by question number
        all_questions_map = {}
        last_question_text = "None (Start of Exam)"
        last_question_id = None
        
        for i in range(len(images)):
            # Window: Current page + Next page for context
            window_bytes = [images[i]]
            if i + 1 < len(images):
                window_bytes.append(images[i+1])
            
            print(f"  Processing Page {i+1}/{len(images)} (with context)...")
            
            # Create prompt with last question context
            prompt = self._create_extraction_prompt(subjects_topics, last_question_text, last_question_id)
            
            result_data = self._extract_from_window_with_prompt(window_bytes, i, prompt)
            
            questions = result_data.get('questions', [])
            pre_header_opts = result_data.get('pre_header_options', {})

            # 1. Handle Pre-header Options (Merging into previous window's last ID)
            if pre_header_opts and last_question_id in all_questions_map:
                existing = all_questions_map[last_question_id]
                existing_opts = existing.get('options', {})
                if not isinstance(existing_opts, dict):
                    # Force existing options to dict if it was a list or something else
                    existing['options'] = {}
                    existing_opts = existing['options']
                
                # Merge options if they were missing or "placeholder"
                for k, v in pre_header_opts.items():
                    current_val = str(existing_opts.get(k, '')).strip()
                    if not current_val or current_val == "UNREADABLE_IMAGE":
                        existing_opts[k] = v
                print(f"    Merged {len(pre_header_opts)} pre-header options into ID {last_question_id}")

            # 2. Process New Questions
            if questions:
                id_min = self.config.id_range_start
                id_max = self.config.id_range_end
                for q in questions:
                    if not isinstance(q, dict):
                        print(f"    Warning: Skipping malformed question (not a dict): {q}")
                        continue
                    try:
                        q_num = int(q.get('number', 0))
                        
                        # STRICT: Reject questions outside the valid ID range
                        if q_num < id_min or q_num > id_max:
                            print(f"    ⚠ REJECTED Q{q_num}: outside valid range [{id_min}-{id_max}]")
                            continue
                        
                        # Auto-correct subject based on ID ranges
                        correct_subject = self.config.get_subject_for_id(q_num)
                        if correct_subject:
                            q['subject'] = correct_subject
                        
                        if q_num > 0:
                            # Rich Deduplication / Merging:
                            if q_num in all_questions_map:
                                existing = all_questions_map[q_num]
                                # Prefer "complete" over "incomplete"
                                if existing.get('status') == 'incomplete' and q.get('status') == 'complete':
                                    all_questions_map[q_num] = q
                                # Otherwise prefer the one with more text or filled options
                                elif len(str(q.get('options', {}))) > len(str(existing.get('options', {}))):
                                    all_questions_map[q_num] = q
                                elif len(q.get('text', '')) > len(existing.get('text', '')):
                                    all_questions_map[q_num] = q
                            else:
                                all_questions_map[q_num] = q
                    except (ValueError, TypeError, AttributeError):
                        continue
                
                # Update continuity hint for next page
                last_q = next((q for q in reversed(questions) if isinstance(q, dict)), None)
                if last_q:
                    last_question_text = last_q.get('text', 'Unknown')[:300]
                    last_question_id = int(last_q.get('number', 0))
            
            if i < len(images) - 1:
                time.sleep(delay_between_pages)
            
            # Save intermediate (Every Page)
            print(f"  --- Saving Page {i+1} Progress ---")
            self.save_extracted(self._build_paper_data(all_questions_map, year, shift, paper_id, pdf_filename, topics_data), for_backend=True)
        
        # Build final
        paper_data = self._build_paper_data(all_questions_map, year, shift, paper_id, pdf_filename, topics_data)
        
        # Auto-verification report
        self._verify_extraction_result(all_questions_map)
        
        return paper_data
    
    def _verify_extraction_result(self, questions_map: Dict[int, Any]) -> None:
        """Print a verification summary of the extracted questions."""
        id_min = self.config.id_range_start
        id_max = self.config.id_range_end
        expected_total = self.config.total_questions
        expected_ids = set(range(id_min, id_max + 1))
        found_ids = set(questions_map.keys())
        
        missing = sorted(expected_ids - found_ids)
        extra = sorted(found_ids - expected_ids)
        
        print(f"\n{'='*60}")
        print(f"📋 EXTRACTION VERIFICATION REPORT")
        print(f"{'='*60}")
        print(f"  Expected: {expected_total} questions (Q{id_min}-Q{id_max})")
        print(f"  Extracted: {len(found_ids)} questions")
        
        if missing:
            print(f"  ❌ MISSING ({len(missing)}): {missing}")
        else:
            print(f"  ✅ No missing questions")
        
        if extra:
            print(f"  ❌ EXTRA/OUT-OF-RANGE ({len(extra)}): {extra}")
        else:
            print(f"  ✅ No out-of-range questions")
        
        # Subject distribution
        subject_dist = {}
        for qid, q in questions_map.items():
            subj = q.get('subject', 'Unknown')
            subject_dist.setdefault(subj, []).append(qid)
        
        print(f"\n  Subject Distribution:")
        for subj, ids in sorted(subject_dist.items()):
            print(f"    {subj}: {len(ids)}q (Q{min(ids)}-Q{max(ids)})")
        
        if missing or extra:
            print(f"\n  ⚠ ACTION NEEDED: Run targeted extraction to fill gaps.")
        else:
            print(f"\n  ✅ EXTRACTION COMPLETE: All {expected_total} questions extracted.")
        print(f"{'='*60}\n")


    def _extract_from_window_with_prompt(self, images_bytes: List[bytes], page_num: int, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """Modified extraction handling multiple images."""
        contents = [prompt]
        for idx, img in enumerate(images_bytes):
            contents.append(f"Image {idx+1}:")
            contents.append(types.Part.from_bytes(data=img, mime_type="image/png"))
        
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents
                )
                if not response.text: return {"questions": []}
                
                # Cleanup markdown blocks
                content = response.text.strip()
                if "```json" in content:
                    content = content.split("```json")[-1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[-1].split("```")[0].strip()
                
                try:
                    data = json.loads(content)
                    return self._post_process_extraction(data, page_num)
                except json.JSONDecodeError:
                    # Retry logic...
                    fixed = re.sub(r'(?<!\\)\\(?!["\\/bfnrt])', r'\\\\', content)
                    try:
                        data = json.loads(fixed)
                        return self._post_process_extraction(data, page_num)
                    except:
                        raise 
                    
            except Exception as e:
                # 429 logic...
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    time.sleep(10 * (attempt + 1))
                    continue
                print(f"  Page {page_num+1} Error: {e}")
                return {"questions": []}
        return {"questions": []}

    def _post_process_extraction(self, data: Any, page_num: int) -> Dict[str, Any]:
        """Normalize and clean the extracted JSON data."""
        # Support both old (list) and new (dict) formats for compatibility
        if isinstance(data, list):
            data = {"questions": data}
        elif not isinstance(data, dict):
            return {"questions": []}

        questions = data.get("questions", [])
        if not isinstance(questions, list):
            questions = []
            data["questions"] = []

        print(f"  Page {page_num + 1}: Extracted {len(questions)} questions")

        # Post-process: Remove Telugu text and clean math
        telugu_pattern = re.compile(r'[\u0c00-\u0c7f]+')
        for q in questions:
            if not isinstance(q, dict): continue
            
            # Clean text
            if 'text' in q:
                q['text'] = telugu_pattern.sub('', str(q.get('text', ''))).strip()
                q['text'] = self._clean_math_syntax(q['text'])
            
            # Clean and Deduplicate options
            opts = q.get('options')
            if isinstance(opts, (dict, list)):
                new_opts = {}
                candidates = {} # { 'A': [val1, val2], ... }
                
                # Normalize keys to A, B, C, D
                if isinstance(opts, dict):
                    raw_items = opts.items()
                else: # list
                    raw_items = [(str(i+1), v) for i, v in enumerate(opts)]
                
                for k, v in raw_items:
                    k_str = str(k).strip().replace('✓', '').replace('*', '').replace('.', '').strip()
                    target_key = None
                    if k_str in ['A', 'B', 'C', 'D']:
                        target_key = k_str
                    elif k_str in ['1', '2', '3', '4']:
                        target_key = chr(64 + int(k_str))
                    
                    if target_key:
                        if target_key not in candidates: candidates[target_key] = []
                        val = self._clean_math_syntax(telugu_pattern.sub('', str(v)).strip())
                        candidates[target_key].append(val)
                
                # Pick best candidate for each key
                for k in ['A', 'B', 'C', 'D']:
                    vals = candidates.get(k, [])
                    if not vals:
                        new_opts[k] = "UNREADABLE_IMAGE"
                        continue
                    # Prefer non-placeholder values
                    valid = [v for v in vals if v and v not in ["IMAGE_CONTENT", "UNREADABLE_IMAGE"]]
                    new_opts[k] = valid[0] if valid else vals[0]
                
                q['options'] = new_opts
            else:
                q['options'] = {k: "UNREADABLE_IMAGE" for k in ['A', 'B', 'C', 'D']}

        # Clean pre_header_options too
        pre_opts = data.get('pre_header_options')
        if isinstance(pre_opts, dict):
            for k, v in pre_opts.items():
                if isinstance(v, str):
                    pre_opts[k] = telugu_pattern.sub('', v).strip()
                    pre_opts[k] = self._clean_math_syntax(pre_opts[k])
        else:
            data['pre_header_options'] = {} # Normalize to dict

        return data
    
    def save_extracted(self, paper_data: Dict[str, Any], for_backend: bool = True) -> Path:
        """
        Save extracted paper data to YAML.
        
        Args:
            paper_data: Extracted paper data
            for_backend: If True, also save to backend folder
        
        Returns:
            Path to saved file
        """
        paper_id = paper_data['id']
        filename = f"{paper_id}.yaml"
        
        # Save to extracted folder
        extracted_path = self.config.extracted_dir / filename
        with open(extracted_path, 'w', encoding='utf-8') as f:
            yaml.dump(paper_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print(f"  Saved to: {extracted_path}")
        
        # Also save to backend folder (ready for API)
        if for_backend:
            backend_path = self.config.backend_dir / filename
            with open(backend_path, 'w', encoding='utf-8') as f:
                yaml.dump(paper_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            print(f"  Backend copy: {backend_path}")
        
        return extracted_path
    
    def extract_and_save(self, pdf_filename: str) -> Path:
        """
        Extract a paper and save it.
        
        Args:
            pdf_filename: PDF filename
        
        Returns:
            Path to saved YAML
        """
        paper_data = self.extract_paper(pdf_filename)
        return self.save_extracted(paper_data)

    def targeted_extract(self, pdf_filename: str, question_id: int, page_hint: Optional[int] = None) -> List[Dict[str, Any]]:
        """Find a specific question in the PDF and extract it."""
        # ... (lines 400-420 unchanged) ...
        pdf_path = self.config.pdfs_dir / pdf_filename
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        doc = fitz.open(pdf_path)
        target_page = -1
        
        if page_hint is not None:
            target_page = page_hint - 1 # 0-indexed
        else:
            search_str = f"Question Number : {question_id}"
            print(f"  Searching for ID {question_id}...")
            for i in range(len(doc)):
                page = doc[i]
                if page.search_for(search_str):
                    target_page = i
                    break
        
        if target_page < 0 or target_page >= len(doc):
            print(f"  Warning: Question ID {question_id} could not be located.")
            doc.close()
            return []

        # High DPI for targeting
        dpi = 200
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        
        window_bytes = []
        # Get target page and next page for context/options
        for i in [target_page, target_page + 1]:
            if i < len(doc):
                pix = doc[i].get_pixmap(matrix=mat)
                window_bytes.append(pix.tobytes("png"))
        
        doc.close()

        topics_data = self._load_topics()
        prompt = self._create_extraction_prompt(topics_data["hierarchy"], target_id=question_id)
        
        print(f"  Targeted extract for ID {question_id} from Page {target_page + 1}...")
        result_data = self._extract_from_window_with_prompt(window_bytes, target_page, prompt)
        return result_data.get('questions', [])

    def fill_gaps(self, yaml_path: Path, missing_ids: List[int]) -> None:
        """Fill missing questions in an existing YAML file."""
        if not yaml_path.exists():
            print(f"Error: {yaml_path} not found.")
            return

        with open(yaml_path, 'r', encoding='utf-8') as f:
            paper_data = yaml.safe_load(f)

        pdf_filename = paper_data.get('source_pdf')
        if not pdf_filename:
            print("Error: source_pdf not found in YAML metadata.")
            return

        all_questions_map = {int(q['id']): q for q in paper_data.get('questions', [])}
        topics_data = self._load_topics()

        for q_id in missing_ids:
            try:
                questions = self.targeted_extract(pdf_filename, q_id)
                if questions:
                    for r in questions:
                        r_num = int(r.get('number', 0))
                        if r_num == q_id:
                            print(f"  Success: Extracted ID {q_id}")
                            all_questions_map[q_id] = r
            except Exception as e:
                print(f"  Error filling ID {q_id}: {e}")
            
            # Short sleep to respect rate limits
            time.sleep(2)

        # Rebuild and save
        year = paper_data['year']
        shift = paper_data['shift']
        paper_id = paper_data['id']
        
        updated_data = self._build_paper_data(all_questions_map, year, shift, paper_id, pdf_filename, topics_data)
        
        # Save back to same path
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(updated_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        print(f"\n✅ Gap filling complete. Updated {yaml_path}")
    
    def list_available_pdfs(self) -> List[str]:
        """List all PDF files available for extraction."""
        return sorted([f.name for f in self.config.pdfs_dir.glob("*.pdf")])
    
    def list_extracted(self) -> List[str]:
        """List all already-extracted papers."""
        return sorted([f.stem for f in self.config.extracted_dir.glob("*.yaml")])
    def _build_paper_data(self, questions_map: Dict[int, Dict[str, Any]], year: int, shift: int, paper_id: str, pdf_filename: str, topics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to build the paper structure from ID-mapped questions."""
        hierarchy = topics_data["hierarchy"]
        sec_to_sub = topics_data["section_to_subject"]
        
        processed = []
        # Sort by question number for stable YAML output
        for q_num in sorted(questions_map.keys()):
            q = questions_map[q_num]
            
            # Robust Subject/Section Matching
            extracted_subject = q.get('subject', 'Mathematics')
            extracted_section = q.get('section', q.get('topic', 'General'))
            
            # Default to extracted
            canonical_subject = extracted_subject
            canonical_section = extracted_section
            
            # 1. First, correct Section from hierarchy
            for sub_name, data in hierarchy.items():
                for sec_name in data["sections"].keys():
                    if extracted_section.lower() in sec_name.lower() or sec_name.lower() in extracted_section.lower():
                        canonical_section = sec_name
                        break
            
            # 2. Crucial: Override Subject based on Section Map
            if canonical_section.lower() in sec_to_sub:
                canonical_subject = sec_to_sub[canonical_section.lower()]
            
            # 3. FINAL AUTHORITY: Override subject based on question ID range
            # This supersedes any Gemini-hallucinated subject field
            id_based_subject = self.config.get_subject_for_id(q_num)
            if id_based_subject:
                canonical_subject = id_based_subject

            processed.append({
                "id": int(q_num), # Preserve original PDF ID
                "section": canonical_section,
                "topic": q.get('topic', 'general'),
                "text": sanitize_text(q.get('text', '')),
                "options": q.get('options', {}),
                "correct_answer": q.get('correct', 'A'),
                "difficulty": "moderate",
                "subject": canonical_subject
            })
        
        return {
            'id': paper_id,
            'exam': self.config.name,
            'year': year,
            'shift': shift,
            'date': None,
            'session': f"Shift {shift}",
            'source_pdf': pdf_filename,
            'metadata': {
                'total_questions': len(processed),
                'duration_minutes': self.config.duration_minutes,
                'marking_scheme': f"+{self.config.marks_per_question} for correct, 0 for wrong"
            },
            'sections': [
                {'code': 'MAT', 'name': 'Mathematics', 'question_count': len([q for q in processed if q['subject'] == 'Mathematics'])},
                {'code': 'PHY', 'name': 'Physics', 'question_count': len([q for q in processed if q['subject'] == 'Physics'])},
                {'code': 'CHE', 'name': 'Chemistry', 'question_count': len([q for q in processed if q['subject'] == 'Chemistry'])}
            ],
            'questions': processed
        }
    
    def _deduplicate_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate extractions using rich fuzzy similarity matching (Text + Options)."""
        if not questions: return []
        
        unique = []
        for q in questions:
            # Build a rich signature: Text + Options
            text = q.get('text', '').strip().lower()
            opts = q.get('options', {})
            opt_str = "".join(sorted([str(v).lower() for v in opts.values()]))
            
            q_sig = re.sub(r'[^a-zA-Z0-9]', '', text + opt_str)
            
            is_duplicate = False
            for existing in unique:
                e_text = existing.get('text', '').strip().lower()
                e_opts = existing.get('options', {})
                e_opt_str = "".join(sorted([str(v).lower() for v in e_opts.values()]))
                
                e_sig = re.sub(r'[^a-zA-Z0-9]', '', e_text + e_opt_str)
                
                # Higher threshold (0.95) to prevent merging similar but distinct questions
                if difflib.SequenceMatcher(None, q_sig, e_sig).ratio() > 0.95:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(q)
            else:
                print(f"  Note: Rich duplicate skipped: {text[:50]}...")
                
        return unique
