# MockMitra 🎯

MockMitra is a state-of-the-art, cache-first mock exam generation and assessment platform. It is engineered to generate highly accurate, conceptually grounded, and syllabus-aligned multiple-choice questions (MCQs) for competitive exams like the **TS EAMCET**. It leverages Google's Gemini models for structured question drafting and 2-pass solver consensus validation.

---

## 🏗️ Architecture & High-Level Workflow

MockMitra utilizes a hybrid decoupled client-server architecture consisting of:
*   **Frontend:** React Web application providing interactive mock test creation, live test-taking interfaces with LaTeX support, and performance review screens.
*   **Backend:** FastAPI application running on Python, utilizing MongoDB (via Beanie ODM) for fast data persistence and the Google GenAI SDK for LLM operations.

### High-Level Data Flow

```
                       ┌─────────────────────────┐
                       │   React Web Frontend    │
                       └────────────┬────────────┘
                                    │ (POST /api/tests/generate)
                                    ▼
                       ┌─────────────────────────┐
                       │  FastAPI Backend Router │
                       │    (app/api/tests.py)   │
                       └────────────┬────────────┘
                                    │ (Spawns background task)
                                    ▼
                       ┌─────────────────────────┐
                       │process_test_generation  │
                       └────────────┬────────────┘
                                    │ (Invokes)
                                    ▼
                       ┌─────────────────────────┐
                       │    QuestionSelector     │
                       └──────┬─────────────┬────┘
                              │             │
       (If Unseen DB pool     │             │ (If DB pool has
        has < target count)   │             │  >= target count)
                              ▼             ▼
                 ┌───────────────────┐ ┌───────────────────┐
                 │    AI Fallback    │ │   Serve from DB   │
                 │(_generate_store)  │ │   (compound idx)  │
                 └────────┬──────────┘ └─────────┬─────────┘
                          │                      │
                          ▼                      │
             ┌─────────────────────────┐         │
             │   QuestionGeneratorV2   │         │
             └────────────┬────────────┘         │
                          │                      │
                          ▼                      │
             ┌─────────────────────────┐         │
             │  AIQuestionGenerator    │         │
             │   (Gemini 2.5 Flash)    │         │
             └────────────┬────────────┘         │
                          │ (Generates question) │
                          ▼                      │
             ┌─────────────────────────┐         │
             │    QuestionValidator    │         │
             │  (2-Pass Consensus via  │         │
             │    Thinking Budget)     │         │
             └────────────┬────────────┘         │
                          │ (Validation Passes)  │
                          ▼                      │
             ┌─────────────────────────┐         │
             │      Deduplication      │         │
             │ (SequenceMatcher ratio) │         │
             └────────────┬────────────┘         │
                          │                      │
                          ▼                      │
             ┌─────────────────────────┐         │
             │   Save to MongoDB Pool  │         │
             └─────────────────────────┘         │
                          │                      │
                          ▼                      ▼
                       ┌─────────────────────────┐
                       │  Populate Test & Start  │
                       └─────────────────────────┘
```

---

## ⚡ Core Systems & Pipelines

### 1. The Cache-First Question Selector
To minimize API token costs and eliminate latency, the platform serves mock tests using a **cache-first retrieval pattern** implemented in [question_selector.py](backend/app/services/question_selector.py):
*   **Seen Question Filter:** Queries previous test attempts for the current user to extract all seen question IDs.
*   **Fast Pool Query:** Performs a compound-indexed NoSQL search on the MongoDB `questions` collection based on `(exam_code, section, topic, difficulty)` excluding all seen IDs.
*   **AI Fallback:** If the database contains fewer questions than requested, it calculates the exact deficit and invokes the LLM fallback pipeline to generate and cache the remaining questions on the fly.

### 2. Context-Grounded Question Generation
When generating questions, the platform grounds the LLM (Gemini 2.5 Flash) by supplying context derived from original previous year exam papers (PYQs) stored in YAML files:
*   **Virtual Blueprints:** Original questions from past papers are loaded into memory as template sources.
*   **Concept-Based Phrasing:** The original PYQ question text is injected into the LLM prompt as a reference. The LLM is strictly instructed to generate a new, original question based on the core concept of the PYQ (altering variables, scenarios, or compounds) rather than repeating the reference question.
*   **LaTeX Formatting:** Enforces standard LaTeX formatting for all variables, chemical equations, and formulas (`$` for inline math, `$$` for block equations).

### 3. Two-Pass AI Solver Consensus Validation
To prevent arithmetic hallucinations and invalid options, generated questions pass through a rigorous quality gate in [question_validator.py](backend/app/services/question_validator.py):
*   **Structural Gate:** Validates the presence of exactly 4 unique options, correct answer string matching, non-empty questions, and lack of placeholder tags.
*   **Pass 1 (Independent Solving):** A separate instance of the Gemini model with a thinking budget solves the question from scratch, re-verifies arithmetic, and outputs a validated answer key. It can modify the answer key in-place if an error is caught.
*   **Pass 2 (Consensus Check):** If Pass 1 accepts, a second independent solver pass runs. Both passes must agree on the identical correct answer value to validate and approve the question.
*   **Deduplication:** A similarity check using `SequenceMatcher` verifies the new question text against existing pool questions (rejecting if similarity is $\ge 82\%$).

---

## 📂 Project Directory Structure

```
MockMitra/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI Endpoint Controllers
│   │   │   └── tests.py     # Test Attempt / Generation APIs
│   │   ├── core/            # Config settings and security
│   │   ├── models/          # Beanie ODM MongoDB Schema Models
│   │   │   └── question.py  # Compound-indexed Question schema
│   │   └── services/        # Pipeline logic services
│   │       ├── ai_question_generator.py  # Gemini Prompter
│   │       ├── question_generator_v2.py  # Generation Router
│   │       ├── question_selector.py       # Unseen-first cache router
│   │       └── question_validator.py      # 2-Pass Solver validator
│   ├── exam_configs/        # Exam structures (Syllabi & Weightage)
│   ├── pyq_papers/          # Previous Year Papers (YAML formatted)
│   └── scripts/             # Seeding & pool replenishment scripts
│       └── seed_question_pool.py  # Bulk question replenishment seeder
└── frontend/
    ├── src/                 # React UI Components
    └── public/              # Static files
```

---

## 🚀 Getting Started

### Backend Setup

1.  **Navigate to backend and configure environment:**
    ```bash
    cd backend
    cp .env.example .env
    ```
    Set your `MONGODB_URL`, `GEMINI_API_KEY` (or Google Cloud Vertex parameters), and auth secret keys.

2.  **Activate virtual environment and install dependencies:**
    ```bash
    venv\Scripts\activate   # Windows
    pip install -r requirements.txt
    ```

3.  **Run the seeder to pre-populate your question pool:**
    ```bash
    python -m scripts.seed_question_pool --exam ts_eamcet --target 10 --resume
    ```

4.  **Launch the development API server:**
    ```bash
    python run.py
    ```

### Frontend Setup

1.  **Navigate to frontend and install packages:**
    ```bash
    cd ../frontend
    npm install
    ```

2.  **Start the React development server:**
    ```bash
    npm run dev
    ```

---

## 🛡️ License

Created for educational exam preparation. All reference papers belong to their respective boards.
