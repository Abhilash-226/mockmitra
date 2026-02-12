# PYQ Papers Directory

This folder contains structured question data extracted from PDF papers.

## Structure

Each paper has its own YAML file:

```
ts_eamcet_2024_1.yaml   # 2024 Shift 1
ts_eamcet_2024_2.yaml   # 2024 Shift 2
...
```

## Paper YAML Schema

```yaml
exam: TS_EAMCET
year: 2024
shift: 1
date: "2024-05-09"
session: Morning/Afternoon
source_pdf: "2024-1.pdf"

metadata:
  total_questions: 160
  duration_minutes: 180
  total_marks: 160
  negative_marking: false
  cutoff_general: 85 # if known

sections:
  - code: MAT
    name: Mathematics
    question_count: 80
  - code: PHY
    name: Physics
    question_count: 40
  - code: CHE
    name: Chemistry
    question_count: 40

questions:
  - number: 1
    section: MAT
    text: "If f(x) = x² + 2x, then f(3) = ?"
    options:
      a: "9"
      b: "12"
      c: "15"
      d: "18"
    correct: c
    topic: Functions

  - number: 2
    section: MAT
    text: "..."
    # ... etc
```

## Extraction Status

| Year | Shifts | Extracted | Verified |
| ---- | ------ | --------- | -------- |
| 2024 | 5      | ⬜        | ⬜       |
| 2023 | 6      | ⬜        | ⬜       |
| 2022 | 6      | ⬜        | ⬜       |
| 2021 | 6      | ⬜        | ⬜       |
| 2020 | 7      | ⬜        | ⬜       |
| 2019 | 5      | ⬜        | ⬜       |
| 2018 | 5      | ⬜        | ⬜       |
| 2017 | 1      | ⬜        | ⬜       |
| 2016 | 1      | ⬜        | ⬜       |

Total: 42 papers
