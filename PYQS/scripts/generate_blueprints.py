"""
PYQ to Blueprint Generator

This script extracts questions from PYQ PDFs and converts them directly into
blueprint format, ready for use with the question generator.

The key insight: PYQs are the PERFECT source for blueprints because:
1. They show exact question formats used in real exams
2. They include real answer options (no placeholders)
3. They demonstrate actual variable ranges used
4. They provide correct answer patterns

Flow:
1. Extract questions from PDF using Gemini Vision
2. Ask Gemini to identify concept, formula, and template structure
3. Cluster similar questions to create blueprint with multiple variants
4. Output valid blueprint YAML ready for question generation
"""
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import yaml

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


# Configuration
BASE_DIR = Path(__file__).parent.parent
EXAMS_DIR = BASE_DIR / "exams"
BLUEPRINT_OUTPUT_DIR = BASE_DIR.parent / "backend" / "blueprints"
PYQ_OUTPUT_DIR = BASE_DIR.parent / "backend" / "pyq_papers"
GEMINI_API_KEY = "AIzaSyCB7CHR6WRi1-Bs3qHmIb2cBdjUw5ekuzc"  # From existing config


@dataclass
class ExtractorConfig:
    """Configuration for PYQ extraction."""
    exam_code: str = "ts_eamcet"
    exam_name: str = "TS EAMCET"
    model: str = "gemini-2.5-flash"  # Using 2.5-flash (best availability)
    questions_per_batch: int = 5  # Questions to analyze together
    delay_between_calls: float = 3.0  # Delay between API calls
    mode: str = "both"  # "blueprint", "pyq", or "both"


class PYQExtractor:
    """
    Extracts questions from PYQ PDFs in dual mode:
    - Blueprint mode: Parameterized templates for AI generation
    - PYQ mode: Exact questions for practice mocks
    """
    
    def __init__(self, config: Optional[ExtractorConfig] = None):
        self.config = config or ExtractorConfig()
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        
    def _pdf_to_images(self, pdf_path: Path, dpi: int = 150) -> List[bytes]:
        """Convert PDF pages to images."""
        doc = fitz.open(pdf_path)
        images = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            images.append(pix.tobytes("png"))
        doc.close()
        return images
    
    def _extract_questions_prompt(self) -> str:
        """Prompt for extracting questions from a page image."""
        return """You are an expert at extracting exam questions from images.

TASK: Extract ALL questions from this TS EAMCET exam page image.

RULES:
1. Extract ONLY the English version (ignore Telugu if present)
2. Use LaTeX for math: $x^2$, $\\frac{a}{b}$, $\\sqrt{x}$, $\\int$
3. Each question has exactly 4 options
4. Identify the correct answer if marked
5. Classify section: MAT (Mathematics), PHY (Physics), CHE (Chemistry)
6. Identify the specific topic within the section

OUTPUT FORMAT (JSON array):
```json
[
  {
    "number": 1,
    "text": "If $\\sin x + \\cos x = \\sqrt{2}$, then $\\sin^4 x + \\cos^4 x$ equals",
    "options": {
      "A": "$\\frac{1}{2}$",
      "B": "$\\frac{1}{4}$",
      "C": "$1$",
      "D": "$\\frac{3}{4}$"
    },
    "correct": "A",
    "section": "MAT",
    "topic": "Trigonometry",
    "chapter": "Trigonometric Functions"
  }
]
```

If no questions on this page, return: []

Extract all questions:"""

    def _analyze_to_blueprint_prompt(self, questions: List[Dict]) -> str:
        """Prompt to convert extracted questions into blueprint format."""
        questions_json = json.dumps(questions, indent=2)
        
        return f"""You are an expert at creating question blueprints for exam question generation.

TASK: Analyze these extracted PYQ questions and create blueprint(s) in YAML format.

QUESTIONS:
{questions_json}

BLUEPRINT REQUIREMENTS:

1. **answer_type** - MUST be one of:
   - `numerical` - Answer is a computed number (requires formula)
   - `categorical` - Answer is a concept/name/property (requires answer_options)
   - `coordinate` - Answer is a point like (x, y)
   - `expression` - Answer is a math expression (requires answer_options)
   - `boolean` - True/False type

2. **For NUMERICAL questions:**
   - Extract the formula used to compute the answer
   - Identify variables and their typical ranges
   - Formula must use Python syntax: * not ×, sqrt() not √, ** not ^

3. **For CATEGORICAL questions:**
   - MUST include answer_options with exactly 4 choices
   - Options should be real from the PYQ, not placeholders

4. **Template with variables:**
   - Convert specific numbers to {{variable}} placeholders
   - Keep the mathematical structure

OUTPUT FORMAT (YAML):
```yaml
- id: SUBJ_CHAP_CONCEPT_01
  exam: TS_EAMCET
  subject: Mathematics  # or Physics/Chemistry
  chapter: Trigonometry
  concept: sin_cos_identity
  answer_type: numerical  # REQUIRED
  
  # Template with {{variables}}
  template_variants:
    - "If $\\sin x + \\cos x = {{k}}$, find $\\sin^4 x + \\cos^4 x$"
    - "Given $\\sin x + \\cos x = {{k}}$, calculate $\\sin^{{n}} x + \\cos^{{n}} x$"
  
  # Variable definitions
  variables:
    k:
      type: choice
      values: [1, "√2", "√3/2"]
    n:
      type: integer
      range: [2, 6]
  
  # Python-evaluable formula (for numerical)
  formula: "1 - (k**2 - 1)**2 / 2"
  
  # Unit (for numerical with units)
  answer_unit: dimensionless
  
  # For categorical - REQUIRED options
  answer_options:
    - "Option 1"
    - "Option 2"
    - "Option 3"
    - "Option 4"
  
  # Difficulty
  difficulty_level: moderate  # easy/moderate/hard
  
  # Time estimate
  constraints:
    steps: 3
    expected_time_sec: 60
  
  # Tags for filtering
  tags: [trigonometry, identity, pyq_2019]
```

IMPORTANT RULES:
- Every blueprint MUST have answer_type
- numerical questions MUST have formula (Python syntax)
- categorical/expression questions MUST have answer_options with 4 items
- No placeholder text like "Option A" - use actual content from PYQ
- If you cannot determine the formula, use categorical with the exact options from the question

Generate blueprint(s) for the given questions:"""

    def extract_questions_from_page(
        self, 
        image_bytes: bytes, 
        page_num: int,
        max_retries: int = 5
    ) -> List[Dict[str, Any]]:
        """Extract questions from a single page image."""
        prompt = self._extract_questions_prompt()
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.config.model,
                    contents=[prompt, image_part]
                )
                response_text = response.text
                
                # Extract JSON
                if '[' in response_text:
                    start = response_text.find('[')
                    end = response_text.rfind(']') + 1
                    questions = json.loads(response_text[start:end])
                    if isinstance(questions, list):
                        print(f"  Page {page_num}: Extracted {len(questions)} questions")
                        return questions
                
                print(f"  Page {page_num}: No questions found")
                return []
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                    # Exponential backoff: 30s, 60s, 120s, 240s, 480s
                    wait = 30 * (2 ** attempt)
                    print(f"  Page {page_num}: Rate limited. Waiting {wait}s... (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                    continue
                print(f"  Page {page_num}: Error - {e}")
                return []
        
        print(f"  Page {page_num}: Max retries exceeded")
        return []
    
    def convert_to_blueprints(
        self, 
        questions: List[Dict[str, Any]],
        source_info: str = ""
    ) -> List[Dict[str, Any]]:
        """Convert extracted questions to blueprint format using Gemini."""
        if not questions:
            return []
        
        prompt = self._analyze_to_blueprint_prompt(questions)
        
        try:
            response = self.client.models.generate_content(
                model=self.config.model,
                contents=[prompt]
            )
            response_text = response.text
            
            # Extract YAML
            if '```yaml' in response_text:
                start = response_text.find('```yaml') + 7
                end = response_text.find('```', start)
                yaml_str = response_text[start:end]
            elif '- id:' in response_text:
                yaml_str = response_text
            else:
                print("  No valid YAML found in response")
                return []
            
            blueprints = yaml.safe_load(yaml_str)
            
            if isinstance(blueprints, list):
                # Add source info to tags
                for bp in blueprints:
                    if 'tags' not in bp:
                        bp['tags'] = []
                    bp['tags'].append(f"pyq_{source_info}")
                
                print(f"  Generated {len(blueprints)} blueprints")
                return blueprints
            
            return []
            
        except Exception as e:
            print(f"  Blueprint conversion error: {e}")
            return []
    
    def save_as_pyq_mock(
        self,
        questions: List[Dict[str, Any]],
        pdf_path: Path,
        year: str,
        shift: int = 1
    ) -> Dict[str, Any]:
        """
        Save extracted questions as exact PYQ mock format.
        
        This creates a ready-to-use mock test with exact original questions
        for practicing past papers.
        """
        # Build PYQ mock structure
        pyq_mock = {
            "id": f"{self.config.exam_code}_{year}_{shift}",
            "exam": self.config.exam_name,
            "year": int(year),
            "shift": shift,
            "date": None,
            "session": f"Shift {shift}",
            "source_pdf": pdf_path.name,
            "metadata": {
                "total_questions": len(questions),
                "duration_minutes": 180,
                "marking_scheme": "+1 for correct, 0 for wrong"
            },
            "sections": [],
            "questions": []
        }
        
        # Group by section
        section_counts = {}
        for q in questions:
            section = q.get("section", "UNK")
            section_counts[section] = section_counts.get(section, 0) + 1
        
        # Build sections
        section_names = {
            "MAT": "Mathematics",
            "PHY": "Physics", 
            "CHE": "Chemistry"
        }
        for code, count in section_counts.items():
            pyq_mock["sections"].append({
                "code": code,
                "name": section_names.get(code, code),
                "question_count": count
            })
        
        # Build questions list
        for idx, q in enumerate(questions, 1):
            pyq_question = {
                "id": idx,
                "section": q.get("section", "UNK"),
                "topic": q.get("topic", "General"),
                "chapter": q.get("chapter", ""),
                "text": q.get("text", ""),
                "options": q.get("options", {}),
                "correct_answer": q.get("correct", ""),
                "difficulty": q.get("difficulty", "moderate"),
                "original_number": q.get("number", idx)
            }
            pyq_mock["questions"].append(pyq_question)
        
        return pyq_mock
    
    def _merge_pyq_mock(self, existing: Dict[str, Any], new_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge new questions into existing PYQ mock file."""
        # Get max existing ID
        max_id = max([q.get("id", 0) for q in existing.get("questions", [])] or [0])
        
        # Add new questions with incremented IDs
        for q in new_questions:
            max_id += 1
            q["id"] = max_id
            existing["questions"].append(q)
        
        # Update total count
        existing["metadata"]["total_questions"] = len(existing["questions"])
        
        # Recalculate section counts
        section_counts = {}
        for q in existing["questions"]:
            section = q.get("section", "UNK")
            section_counts[section] = section_counts.get(section, 0) + 1
        
        # Update sections
        section_names = {"MAT": "Mathematics", "PHY": "Physics", "CHE": "Chemistry"}
        existing["sections"] = [
            {"code": code, "name": section_names.get(code, code), "question_count": count}
            for code, count in section_counts.items()
        ]
        
        return existing
    
    def _merge_blueprints(self, existing_path: Path, new_blueprints: List[Dict]) -> List[Dict]:
        """Merge new blueprints with existing file."""
        existing = []
        if existing_path.exists():
            with open(existing_path, 'r', encoding='utf-8') as f:
                existing = yaml.safe_load(f) or []
        existing.extend(new_blueprints)
        return existing

    def process_pdf(
        self, 
        pdf_path: Path,
        blueprint_output: Optional[Path] = None,
        pyq_output: Optional[Path] = None,
        skip_pages: int = 0,  # Skip instruction pages
        start_page: Optional[int] = None,  # 1-indexed start page
        end_page: Optional[int] = None,  # 1-indexed end page (inclusive)
        append: bool = False,  # Append to existing file instead of overwriting
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Process a PDF and generate outputs based on mode.
        
        Args:
            pdf_path: Path to PDF file
            blueprint_output: Where to save blueprint YAML
            pyq_output: Where to save exact PYQ mock YAML
            skip_pages: Number of instruction pages to skip (legacy)
            start_page: Process from this page (1-indexed)
            end_page: Process until this page (1-indexed, inclusive)
        
        Returns:
            Tuple of (blueprints list, pyq_mock dict or None)
        """
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_path.name}")
        print(f"Mode: {self.config.mode.upper()}")
        print(f"{'='*60}")
        
        # Convert PDF to images
        print("Converting PDF to images...")
        images = self._pdf_to_images(pdf_path)
        total_pages = len(images)
        print(f"Total pages: {total_pages}")
        
        # Determine page range
        start_idx = (start_page - 1) if start_page else skip_pages
        end_idx = end_page if end_page else total_pages
        
        print(f"Processing pages {start_idx + 1} to {end_idx}")
        
        # Extract questions from each page
        all_questions = []
        print("\nExtracting questions...")
        
        for i in range(start_idx, min(end_idx, total_pages)):
            image_bytes = images[i]
            questions = self.extract_questions_from_page(image_bytes, i+1)
            all_questions.extend(questions)
            
            time.sleep(self.config.delay_between_calls)
        
        print(f"\nTotal questions extracted: {len(all_questions)}")
        
        if not all_questions:
            print("No questions extracted!")
            return ([], None)
        
        # Extract year from filename
        year_match = re.search(r'(\d{4})', pdf_path.name)
        year = year_match.group(1) if year_match else "unknown"
        
        all_blueprints = []
        pyq_mock = None
        
        # MODE: PYQ - Save exact questions
        if self.config.mode in ("pyq", "both"):
            print("\n--- Saving PYQ Mock (exact questions) ---")
            
            if pyq_output:
                pyq_output.parent.mkdir(parents=True, exist_ok=True)
                
                if append and pyq_output.exists():
                    # Load existing and merge
                    with open(pyq_output, 'r', encoding='utf-8') as f:
                        existing_mock = yaml.safe_load(f) or {}
                    
                    # Create questions in PYQ format
                    new_pyq_questions = []
                    for q in all_questions:
                        new_pyq_questions.append({
                            "section": q.get("section", "UNK"),
                            "topic": q.get("topic", "General"),
                            "chapter": q.get("chapter", ""),
                            "text": q.get("text", ""),
                            "options": q.get("options", {}),
                            "correct_answer": q.get("correct", ""),
                            "difficulty": q.get("difficulty", "moderate"),
                            "original_number": q.get("number", 0)
                        })
                    
                    pyq_mock = self._merge_pyq_mock(existing_mock, new_pyq_questions)
                    print(f"  Merged {len(all_questions)} new questions")
                else:
                    pyq_mock = self.save_as_pyq_mock(all_questions, pdf_path, year)
                
                with open(pyq_output, 'w', encoding='utf-8') as f:
                    yaml.dump(pyq_mock, f, 
                             default_flow_style=False, 
                             allow_unicode=True, 
                             sort_keys=False)
                print(f"PYQ Mock saved: {pyq_output}")
                print(f"  Total questions: {pyq_mock['metadata']['total_questions']}")
        
        # MODE: BLUEPRINT - Generate parameterized templates
        if self.config.mode in ("blueprint", "both"):
            print("\n--- Generating Blueprints (parameterized) ---")
            
            # Group by section
            sections = {}
            for q in all_questions:
                section = q.get('section', 'UNK')
                if section not in sections:
                    sections[section] = []
                sections[section].append(q)
            
            for section, questions in sections.items():
                print(f"\n  Section: {section} ({len(questions)} questions)")
                
                # Process in batches
                for i in range(0, len(questions), self.config.questions_per_batch):
                    batch = questions[i:i + self.config.questions_per_batch]
                    print(f"    Batch {i//self.config.questions_per_batch + 1}: {len(batch)} questions")
                    
                    blueprints = self.convert_to_blueprints(batch, source_info=year)
                    all_blueprints.extend(blueprints)
                    
                    time.sleep(self.config.delay_between_calls)
            
            print(f"\nTotal blueprints generated: {len(all_blueprints)}")
            
            if blueprint_output and all_blueprints:
                blueprint_output.parent.mkdir(parents=True, exist_ok=True)
                
                if append and blueprint_output.exists():
                    # Merge with existing
                    all_blueprints = self._merge_blueprints(blueprint_output, all_blueprints)
                    print(f"  Merged blueprints, total: {len(all_blueprints)}")
                
                with open(blueprint_output, 'w', encoding='utf-8') as f:
                    yaml.dump(all_blueprints, f, 
                             default_flow_style=False, 
                             allow_unicode=True, 
                             sort_keys=False)
                print(f"Blueprints saved: {blueprint_output}")
        
        return (all_blueprints, pyq_mock)
    
    def process_pdf_full(
        self,
        pdf_path: Path,
        blueprint_output: Optional[Path] = None,
        pyq_output: Optional[Path] = None,
        start_page: int = 2,
        batch_size: int = 5,  # Pages per batch
    ) -> Tuple[int, int]:
        """
        Process entire PDF page by page, appending to the same output files.
        
        Args:
            pdf_path: Path to PDF
            blueprint_output: Blueprint YAML output path
            pyq_output: PYQ mock YAML output path
            start_page: First page to process (1-indexed)
            batch_size: Number of pages per API call batch
            
        Returns:
            Tuple of (total_questions, total_blueprints)
        """
        print(f"\n{'='*60}")
        print(f"FULL PDF EXTRACTION: {pdf_path.name}")
        print(f"Mode: {self.config.mode.upper()}")
        print(f"{'='*60}")
        
        # Get total pages
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        print(f"Total pages: {total_pages}")
        print(f"Starting from page: {start_page}")
        print(f"Batch size: {batch_size} pages")
        
        # Clear existing files for fresh start
        if pyq_output and pyq_output.exists():
            pyq_output.unlink()
            print(f"Cleared existing: {pyq_output.name}")
        if blueprint_output and blueprint_output.exists():
            blueprint_output.unlink()
            print(f"Cleared existing: {blueprint_output.name}")
        
        total_questions = 0
        total_blueprints = 0
        
        # Process in batches
        current_page = start_page
        batch_num = 1
        
        while current_page <= total_pages:
            end_page = min(current_page + batch_size - 1, total_pages)
            
            print(f"\n{'─'*40}")
            print(f"Batch {batch_num}: Pages {current_page}-{end_page}")
            print(f"{'─'*40}")
            
            try:
                blueprints, pyq_mock = self.process_pdf(
                    pdf_path,
                    blueprint_output=blueprint_output,
                    pyq_output=pyq_output,
                    start_page=current_page,
                    end_page=end_page,
                    append=True  # Always append for full processing
                )
                
                if blueprints:
                    total_blueprints += len(blueprints)
                if pyq_mock:
                    total_questions = pyq_mock["metadata"]["total_questions"]
                
                print(f"  Running total - Questions: {total_questions}, Blueprints: {total_blueprints}")
                
            except Exception as e:
                print(f"  Error in batch {batch_num}: {e}")
            
            current_page = end_page + 1
            batch_num += 1
        
        print(f"\n{'='*60}")
        print("EXTRACTION COMPLETE")
        print(f"  Total questions extracted: {total_questions}")
        print(f"  Total blueprints generated: {total_blueprints}")
        print(f"{'='*60}")
        
        return (total_questions, total_blueprints)

    def process_all_pdfs(
        self,
        exam_code: str = "ts_eamcet",
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Process all PDFs for an exam.
        
        Args:
            exam_code: Exam code (folder name)
            limit: Max PDFs to process (for testing)
        
        Returns:
            Stats dict
        """
        pdfs_dir = EXAMS_DIR / exam_code / "pdfs"
        blueprint_dir = BLUEPRINT_OUTPUT_DIR / exam_code / "pyq_generated"
        pyq_dir = PYQ_OUTPUT_DIR / exam_code
        blueprint_dir.mkdir(parents=True, exist_ok=True)
        pyq_dir.mkdir(parents=True, exist_ok=True)
        
        pdfs = sorted(pdfs_dir.glob("*.pdf"))
        if limit:
            pdfs = pdfs[:limit]
        
        print(f"Found {len(pdfs)} PDFs to process")
        
        stats = {
            'pdfs_processed': 0,
            'questions_extracted': 0,
            'blueprints_generated': 0,
            'pyq_mocks_generated': 0,
        }
        
        for pdf_path in pdfs:
            # Extract year from filename
            year_match = re.search(r'(\d{4})', pdf_path.name)
            year = year_match.group(1) if year_match else "unknown"
            
            bp_output = blueprint_dir / f"{pdf_path.stem}_blueprints.yaml"
            pyq_output = pyq_dir / f"{exam_code}_{year}_1.yaml"
            
            # Skip if already processed (check both outputs)
            if bp_output.exists() and pyq_output.exists():
                print(f"Skipping {pdf_path.name} (already processed)")
                continue
            
            try:
                blueprints, pyq_mock = self.process_pdf(
                    pdf_path, 
                    blueprint_output=bp_output if self.config.mode in ('blueprint', 'both') else None,
                    pyq_output=pyq_output if self.config.mode in ('pyq', 'both') else None,
                    skip_pages=1
                )
                stats['pdfs_processed'] += 1
                stats['blueprints_generated'] += len(blueprints) if blueprints else 0
                stats['pyq_mocks_generated'] += 1 if pyq_mock else 0
            except Exception as e:
                print(f"Error processing {pdf_path.name}: {e}")
        
        return stats


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extract questions from PYQ PDFs in dual mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  blueprint  - Generate parameterized templates for AI mock generation
  pyq        - Save exact questions for past paper practice  
  both       - Generate both outputs (default)

Examples:
  python generate_blueprints.py 2024.pdf --mode blueprint
  python generate_blueprints.py 2024.pdf --mode pyq --start 2 --pages 50
  python generate_blueprints.py 2024.pdf --full --mode both  # Process entire PDF
        """
    )
    parser.add_argument('pdf', nargs='?', help='Specific PDF to process')
    parser.add_argument('--exam', default='ts_eamcet', help='Exam code')
    parser.add_argument('--mode', choices=['blueprint', 'pyq', 'both'], default='both',
                        help='Extraction mode: blueprint, pyq, or both (default: both)')
    parser.add_argument('--full', action='store_true', 
                        help='Process entire PDF page by page, saving to same file')
    parser.add_argument('--batch-size', type=int, default=5, dest='batch_size',
                        help='Pages per batch when using --full (default: 5)')
    parser.add_argument('--all', action='store_true', help='Process all PDFs')
    parser.add_argument('--limit', type=int, help='Limit PDFs (for testing)')
    parser.add_argument('--test', action='store_true', help='Test with one PDF')
    parser.add_argument('--start', type=int, default=2, help='Start page (1-indexed, default=2 to skip instructions)')
    parser.add_argument('--end', type=int, help='End page (1-indexed, inclusive)')
    parser.add_argument('--pages', type=int, default=10, help='Number of pages to process (default=10)')
    parser.add_argument('--shift', type=int, default=1, help='Exam shift number (default=1)')
    
    args = parser.parse_args()
    
    # Create config with mode
    config = ExtractorConfig(
        exam_code=args.exam,
        mode=args.mode
    )
    extractor = PYQExtractor(config)
    
    if args.test:
        # Test with first PDF, only first 5 pages
        pdfs_dir = EXAMS_DIR / args.exam / "pdfs"
        pdfs = sorted(pdfs_dir.glob("*.pdf"))
        if pdfs:
            test_pdf = pdfs[0]
            bp_out = BLUEPRINT_OUTPUT_DIR / args.exam / "pyq_generated" / f"{test_pdf.stem}_test.yaml"
            pyq_out = PYQ_OUTPUT_DIR / args.exam / f"{test_pdf.stem}_test.yaml"
            extractor.process_pdf(test_pdf, bp_out, pyq_out, start_page=2, end_page=6)
    
    elif args.all:
        stats = extractor.process_all_pdfs(args.exam, args.limit)
        print(f"\n{'='*60}")
        print("COMPLETE")
        print(f"PDFs processed: {stats['pdfs_processed']}")
        print(f"Blueprints generated: {stats['blueprints_generated']}")
    
    elif args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            pdf_path = EXAMS_DIR / args.exam / "pdfs" / args.pdf
        
        if pdf_path.exists():
            # Extract year from filename
            year_match = re.search(r'(\d{4})', pdf_path.name)
            year = year_match.group(1) if year_match else "unknown"
            
            # Define output paths based on mode
            blueprint_output = None
            pyq_output = None
            
            if args.mode in ('blueprint', 'both'):
                if args.full:
                    blueprint_output = BLUEPRINT_OUTPUT_DIR / args.exam / "pyq_generated" / f"{pdf_path.stem}_full_blueprints.yaml"
                else:
                    end_page = args.end if args.end else (args.start + args.pages - 1)
                    blueprint_output = BLUEPRINT_OUTPUT_DIR / args.exam / "pyq_generated" / f"{pdf_path.stem}_p{args.start}-{end_page}_blueprints.yaml"
            
            if args.mode in ('pyq', 'both'):
                pyq_output = PYQ_OUTPUT_DIR / args.exam / f"{args.exam}_{year}_{args.shift}.yaml"
            
            if args.full:
                # Process entire PDF page by page
                print(f"Full PDF extraction mode")
                print(f"Batch size: {args.batch_size} pages")
                
                extractor.process_pdf_full(
                    pdf_path,
                    blueprint_output=blueprint_output,
                    pyq_output=pyq_output,
                    start_page=args.start,
                    batch_size=args.batch_size
                )
            else:
                # Process specified page range
                end_page = args.end if args.end else (args.start + args.pages - 1)
                print(f"Processing pages {args.start} to {end_page}")
                print(f"Mode: {args.mode.upper()}")
                
                extractor.process_pdf(
                    pdf_path, 
                    blueprint_output=blueprint_output,
                    pyq_output=pyq_output,
                    start_page=args.start, 
                    end_page=end_page
                )
        else:
            print(f"PDF not found: {pdf_path}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
