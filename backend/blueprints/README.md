# Question Blueprints

This directory contains question blueprints organized by exam type.

## Folder Structure

```
blueprints/
├── README.md
├── ts_eamcet/           # TS EAMCET Engineering
│   ├── mathematics.yaml
│   ├── physics.yaml
│   └── chemistry.yaml
├── ap_eamcet/           # AP EAMCET (future)
├── jee_main/            # JEE Main (future)
├── ssc_cgl/             # SSC CGL (future)
└── ...
```

## Adding a New Exam

1. Create a new folder with the exam code (lowercase, underscores):

   ```
   blueprints/jee_main/
   ```

2. Add subject YAML files following the blueprint schema:

   ```
   blueprints/jee_main/mathematics.yaml
   blueprints/jee_main/physics.yaml
   blueprints/jee_main/chemistry.yaml
   ```

3. Ensure each blueprint has the correct `exam` field:

   ```yaml
   - id: JEE_MATH_01
     exam: JEE_MAIN
     subject: Mathematics
     ...
   ```

4. The loader automatically discovers all `.yaml` and `.yml` files recursively.

## Blueprint Schema

Each blueprint should include:

```yaml
- id: UNIQUE_ID # Format: EXAM_SUBJECT_NUM (e.g., TS_MATH_01)
  exam: TS_EAMCET # Exam identifier
  subject: Mathematics # Subject name
  unit: Algebra # Unit/section (optional)
  chapter: Quadratics # Chapter name
  concept: Roots # Specific concept

  template_variants: # Question templates with {variables}
    - "Find the roots of {equation}."
    - "Solve: {equation}"

  variables: # Variable definitions
    a:
      type: integer
      range: [1, 5]

  constraints: # Generation constraints
    steps: 2
    expected_time_sec: 60

  formula: "x = (-b ± √(b²-4ac)) / 2a"
  answer_unit: ""
  difficulty_level: easy # easy, moderate, hard
  tags: [quadratics, roots]
```

## Supported Exams

| Folder      | Exam Name             | Status     |
| ----------- | --------------------- | ---------- |
| `ts_eamcet` | TS EAMCET Engineering | ✅ Active  |
| `ap_eamcet` | AP EAMCET Engineering | 🔜 Planned |
| `jee_main`  | JEE Main              | 🔜 Planned |
| `ssc_cgl`   | SSC CGL               | 🔜 Planned |
| `ibps_po`   | IBPS PO               | 🔜 Planned |
