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
        self.api_key = api_key or GEMINI_API_KEY
        
        # Initialize Gemini client
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-1.5-flash"  # Use 1.5 flash for better quota
        
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
    
    def _create_extraction_prompt(self) -> str:
        """Create the prompt for Gemini to extract questions."""
        sections_info = ", ".join([f"{s['name']} ({s['code']})" for s in self.config.sections])
        
        return f"""You are an expert at extracting exam questions from images.

EXAM: {self.config.name}
SECTIONS: {sections_info}
EXPECTED DISTRIBUTION: {self.config.section_questions}

TASK: Extract ALL questions from this exam page image. 

RULES:
1. Extract ONLY the English version of each question (ignore Telugu/Hindi if present)
2. For math equations, use LaTeX notation: $x^2$, $\\frac{{a}}{{b}}$, $\\int$, $\\sum$
3. Each question has 4 options (labeled 1,2,3,4 or A,B,C,D)
4. Identify the correct answer if marked, otherwise set to null
5. Estimate the section (MAT/PHY/CHE) based on content

OUTPUT FORMAT (JSON array):
```json
[
  {{
    "number": 1,
    "text": "Question text here with $LaTeX$ for math",
    "options": {{
      "A": "Option 1 text",
      "B": "Option 2 text", 
      "C": "Option 3 text",
      "D": "Option 4 text"
    }},
    "correct": "A",
    "section": "MAT",
    "topic": "Calculus"
  }}
]
```

If no questions are found on this page (e.g., instructions page), return an empty array: []

Extract all questions visible in the image:"""
    
    def _extract_from_image(self, image_bytes: bytes, page_num: int, max_retries: int = 3) -> List[Dict[str, Any]]:
        """
        Extract questions from a single page image using Gemini.
        
        Args:
            image_bytes: PNG image bytes
            page_num: Page number (for logging)
            max_retries: Maximum retry attempts on rate limit errors
        
        Returns:
            List of extracted questions
        """
        prompt = self._create_extraction_prompt()
        
        # Create image part for new Gemini API
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/png"
        )
        
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[prompt, image_part]
                )
                response_text = response.text
                
                # Extract JSON from response
                # Look for JSON array in the response
                if '[' in response_text and ']' in response_text:
                    start = response_text.find('[')
                    end = response_text.rfind(']') + 1
                    json_str = response_text[start:end]
                    
                    try:
                        questions = json.loads(json_str)
                        if isinstance(questions, list):
                            print(f"  Page {page_num + 1}: Extracted {len(questions)} questions")
                            return questions
                    except json.JSONDecodeError as e:
                        print(f"  Page {page_num + 1}: JSON parse error - {e}")
                
                # If no valid JSON found
                print(f"  Page {page_num + 1}: No questions found")
                return []
                
            except Exception as e:
                error_str = str(e)
                # Check for rate limit error (429)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    # Parse retry delay from error if available
                    wait_time = 60  # Default wait
                    if "retry in" in error_str.lower():
                        import re
                        match = re.search(r'retry in (\d+(?:\.\d+)?)', error_str.lower())
                        if match:
                            wait_time = float(match.group(1)) + 2  # Add buffer
                    
                    if attempt < max_retries - 1:
                        print(f"  Page {page_num + 1}: Rate limited. Waiting {wait_time:.0f}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                
                print(f"  Page {page_num + 1}: API error - {e}")
                return []
        
        return []
    
    def extract_paper(self, pdf_filename: str, delay_between_pages: float = 5.0) -> Dict[str, Any]:
        """
        Extract all questions from a PDF paper.
        
        Args:
            pdf_filename: Name of PDF file (in exam's pdfs folder)
            delay_between_pages: Delay between API calls in seconds (default 5s for Gemini free tier: 15 req/min)
        
        Returns:
            Complete paper data structure
        """
        pdf_path = self.config.pdfs_dir / pdf_filename
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        year, shift = parse_pdf_filename(pdf_filename)
        paper_id = generate_paper_id(self.config.code, year, shift)
        
        print(f"\nExtracting: {pdf_filename}")
        print(f"  Paper ID: {paper_id}")
        
        # Convert PDF to images
        print("  Converting PDF to images...")
        images = self._pdf_to_images(pdf_path)
        print(f"  Total pages: {len(images)}")
        
        # Extract questions from each page
        all_questions = []
        print("  Extracting questions...")
        
        for i, image_bytes in enumerate(images):
            questions = self._extract_from_image(image_bytes, i)
            all_questions.extend(questions)
            
            # Rate limiting
            if i < len(images) - 1:
                time.sleep(delay_between_pages)
        
        # Assign proper question numbers and validate
        print(f"  Total questions extracted: {len(all_questions)}")
        
        # Re-number questions sequentially
        for i, q in enumerate(all_questions):
            q['number'] = i + 1
            
            # Estimate section if not provided
            if not q.get('section'):
                q['section'] = estimate_section(i + 1, self.config.section_questions)
            
            # Clean up text
            q['text'] = sanitize_text(q.get('text', ''))
            
            # Ensure options are properly formatted
            if 'options' in q and isinstance(q['options'], dict):
                q['options'] = {
                    k: sanitize_text(str(v)) 
                    for k, v in q['options'].items()
                }
        
        # Build section summary
        sections = []
        for sec in self.config.sections:
            sec_questions = [q for q in all_questions if q.get('section') == sec['code']]
            sections.append({
                'code': sec['code'],
                'name': sec['name'],
                'question_count': len(sec_questions)
            })
        
        # Build final paper structure
        paper_data = {
            'id': paper_id,
            'exam': self.config.name,
            'year': year,
            'shift': shift,
            'date': None,  # Can be filled manually
            'session': f"Shift {shift}",
            'source_pdf': pdf_filename,
            'metadata': {
                'total_questions': len(all_questions),
                'duration_minutes': self.config.duration_minutes,
                'marking_scheme': f"+{self.config.marks_per_question} for correct, -{self.config.negative_marks} for wrong"
            },
            'sections': sections,
            'questions': all_questions
        }
        
        return paper_data
    
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
