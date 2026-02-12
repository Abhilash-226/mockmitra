# PYQ (Previous Year Questions) Extraction System

This folder contains:

- Source PDFs for various exam papers
- Extraction scripts using AI (Gemini Vision)
- Extracted YAML files ready for the backend API

## Folder Structure

```
PYQS/
├── exams/
│   ├── ts_eamcet/           # TS EAMCET exam
│   │   ├── pdfs/            # Source PDF files
│   │   └── extracted/       # Extracted YAML files
│   ├── jee_main/            # (Future) JEE Main
│   │   ├── pdfs/
│   │   └── extracted/
│   └── neet/                # (Future) NEET
│       ├── pdfs/
│       └── extracted/
└── scripts/
    ├── extract.py           # Main extraction script
    ├── requirements.txt     # Python dependencies
    └── pyq_extractor/       # Extraction module
        ├── __init__.py
        ├── config.py        # Exam configurations
        ├── gemini_extractor.py
        └── utils.py
```

## Setup

1. Install dependencies:

   ```bash
   cd PYQS/scripts
   pip install -r requirements.txt
   ```

2. Set your Gemini API key (optional - default key is configured):
   ```bash
   set GEMINI_API_KEY=your_api_key_here
   ```

## Usage

### List available PDFs

```bash
python extract.py ts_eamcet --list
```

### Extract a specific paper

```bash
python extract.py ts_eamcet 2020-1.pdf
```

### Extract all pending papers

```bash
python extract.py ts_eamcet --all
```

### List configured exams

```bash
python extract.py --exams
```

## Adding a New Exam

1. Create folder: `exams/{exam_code}/pdfs/`
2. Add PDFs to the pdfs folder
3. Add configuration in `scripts/pyq_extractor/config.py`:
   ```python
   "jee_main": ExamConfig(
       code="jee_main",
       name="JEE Main",
       sections=[
           {"code": "MAT", "name": "Mathematics"},
           {"code": "PHY", "name": "Physics"},
           {"code": "CHE", "name": "Chemistry"},
       ],
       section_questions={"MAT": 25, "PHY": 25, "CHE": 25},
       duration_minutes=180,
   )
   ```
4. Run extraction: `python extract.py jee_main --all`

## Output Format

Extracted YAML files follow this structure:

```yaml
id: ts_eamcet_2020_1
exam: TS EAMCET
year: 2020
shift: 1
metadata:
  total_questions: 160
  duration_minutes: 180
sections:
  - code: MAT
    name: Mathematics
    question_count: 80
questions:
  - number: 1
    section: MAT
    text: "Question with $LaTeX$ for math"
    options:
      A: "Option A"
      B: "Option B"
      C: "Option C"
      D: "Option D"
    correct: "A"
    topic: "Calculus"
```

## Extracted files location

After extraction, YAML files are saved to:

1. `exams/{exam_code}/extracted/` - Archive copy
2. `backend/pyq_papers/{exam_code}/` - Ready for API

The backend automatically reads from `backend/pyq_papers/{exam_code}/`.
