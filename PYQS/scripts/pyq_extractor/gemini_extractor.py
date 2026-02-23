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

    def _create_extraction_prompt(self, hierarchy: Dict[str, Any], last_question_text: str = "None") -> str:
        """Create the prompt for Gemini to extract questions with full hierarchy knowledge."""
        
        guidance = "STRICT SUBJECT/SECTION/TOPIC HIERARCHY:\n"
        for sub, data in hierarchy.items():
            guidance += f"- Subject: {sub}\n"
            for sec, topics in data["sections"].items():
                guidance += f"  - Section: {sec}\n"
                guidance += f"    - Valid Topics: {', '.join(topics)}\n"

        return f"""You are an expert at extracting exam questions from images.

{guidance}

TASK: Extract ALL questions that START on Image 1. 

STRICT RULES:
1. "Question Number/ID": You MUST extract the official question number (1-160) from the PDF. This is crucial for tracking.
2. "Start on Image 1": Only extract questions whose question number or initial text begins on Image 1. 
3. "Context from Image 2": If a question starts on Image 1 but ends on Image 2, use Image 2 to extract the remaining text and ALL options.
4. Clean Text: DO NOT include "Question Number", "Question Id", or other meta-headers in the "text" field.
4. Correct Format (STRICT):
   - 'subject': Must match a Subject name (e.g., "Mathematics").
   - 'section': Must match the EXACT Section name that owns the chosen topic.
   - 'topic': Must match the EXACT Topic slug from the list.
   - Example: If topic is 'matrices', section MUST be 'algebra' (or whatever the list says).
5. LaTeX: Use $...$. Double backslashes in JSON (\\\\text, \\\\frac).
6. Options: Extract all 4 options. If options are split across pages, ensure they are all captured correctly.

STRICT CONTINUITY:
The LAST question I successfully extracted was:
"{last_question_text}"
DO NOT re-extract this question. Start exactly AFTER it on Image 1.

OUTPUT FORMAT (JSON array):
[
  {{
    "number": 1,
    "subject": "Mathematics",
    "section": "Algebra",
    "topic": "matrices",
    "text": "The determinant of matrix...",
    "options": {{
      "A": "val1", "B": "val2", "C": "val3", "D": "val4"
    }},
    "correct": "C"
  }}
]
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
        
        for i in range(len(images)):
            # Window: Current page + Next page for context
            window_bytes = [images[i]]
            if i + 1 < len(images):
                window_bytes.append(images[i+1])
            
            print(f"  Processing Page {i+1}/{len(images)} (with context)...")
            
            # Create prompt with last question context
            prompt = self._create_extraction_prompt(subjects_topics, last_question_text)
            
            questions = self._extract_from_window_with_prompt(window_bytes, i, prompt)
            
            if questions:
                for q in questions:
                    try:
                        q_num = int(q.get('number', 0))
                        if q_num > 0:
                            # Rich Deduplication / Merging:
                            if q_num in all_questions_map:
                                existing = all_questions_map[q_num]
                                # Prefer the one with more text
                                if len(q.get('text', '')) > len(existing.get('text', '')):
                                    all_questions_map[q_num] = q
                            else:
                                all_questions_map[q_num] = q
                    except (ValueError, TypeError):
                        continue
                
                # Update continuity hint for next page
                last_question_text = questions[-1].get('text', 'Unknown')[:300]
            
            if i < len(images) - 1:
                time.sleep(delay_between_pages)
            
            # Save intermediate (Every Page)
            print(f"  --- Saving Page {i+1} Progress ---")
            self.save_extracted(self._build_paper_data(all_questions_map, year, shift, paper_id, pdf_filename, topics_data), for_backend=True)
        
        # Build final
        paper_data = self._build_paper_data(all_questions_map, year, shift, paper_id, pdf_filename, topics_data)
        return paper_data

    def _extract_from_window_with_prompt(self, images_bytes: List[bytes], page_num: int, prompt: str, max_retries: int = 3) -> List[Dict[str, Any]]:
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
                if not response.text: return []
                
                # Cleanup markdown blocks
                content = response.text.strip()
                if "```json" in content:
                    content = content.split("```json")[-1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[-1].split("```")[0].strip()
                
                try:
                    questions = json.loads(content)
                    if isinstance(questions, list):
                        print(f"  Page {page_num + 1}: Extracted {len(questions)} questions")
                        return questions
                    return []
                except json.JSONDecodeError:
                    # Retry with basic backslash fix
                    import re
                    fixed = re.sub(r'(?<!\\)\\(?!["\\/bfnrt])', r'\\\\', content)
                    try:
                        questions = json.loads(fixed)
                        if isinstance(questions, list):
                            print(f"  Page {page_num + 1}: Extracted {len(questions)} questions (after LaTeX repair)")
                            return questions
                    except:
                        raise # Re-raise to trigger retry loop
                    
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    time.sleep(10 * (attempt + 1))
                    continue
                print(f"  Page {page_num+1} Error: {e}")
                return []
        return []
    
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
