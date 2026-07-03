# MockMitra 🎯
### AI-Powered Exam Preparation Platform for Indian Competitive Exams

[![Live] (https://mockmitra.app)

MockMitra is a production-grade AI-powered CBT (Computer Based Test) platform
that helps students prepare for competitive exams like TS EAMCET through
intelligent mock tests, PYQ practice, and performance analytics.

---

## 🚀 Live Demo

**[https://mockmitra.app](https://mockmitra.app)**

| Metric | Count |
|---|---|
| Registered Users | 130+ |
| Total Visitors | 600+ |
| Test Responses Processed | 18,000+ |
| AI-Generated Questions | 4,700+ |

---

## ✨ Features

- **AI Test Generation** — Google Gemini 2.5 Flash generates exam-standard MCQs conditioned on subject, topic, and difficulty
- **PYQ Practice** — Attempt actual previous year question papers from TS EAMCET and other exams
- **Custom Tests** — Create personalized tests with subject-wise, topic-wise, and difficulty-based filtering
- **CBT Interface** — Realistic computer-based test simulation matching actual exam environments
- **Analytics Dashboard** — Track accuracy, average score, practice hours, and improvement over time
- **History & Review** — Revisit past tests, compare results, and identify weak areas

---

## 🏗️ System Architecture

```
React Frontend
      │
      ▼ POST /api/tests/generate
FastAPI Backend (Background Task)
      │
      ▼
QuestionSelector (Cache-First Logic)
      │
      ├── Pool has unseen questions? ──► Serve from MongoDB (compound index)
      │
      └── Pool deficit? ──► Fetch PYQ Blueprint (YAML)
                                  │
                                  ▼
                          AIQuestionGenerator
                          (Gemini 2.5 Flash)
                                  │
                                  ▼
                          QuestionValidator
                          (2-Pass Solver Consensus)
                                  │
                                  ▼
                          Deduplication Check
                          (SequenceMatcher ≥ 0.82)
                                  │
                                  ▼
                          Save to MongoDB Pool
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React.js, Tailwind CSS, Vite |
| Backend | FastAPI, Python |
| Database | MongoDB (compound indexed for sub-ms retrieval) |
| AI Model | Google Gemini 2.5 Flash |
| Validation | Gemini Thinking Model (2-pass consensus) |
| Deployment | Render |

---

## 🧠 How AI Generation Works

1. User selects exam, subject, topic, and difficulty from the frontend
2. System queries MongoDB pool for questions the user has **never seen**
3. If pool has enough unseen questions → serve directly (cache hit)
4. If pool deficit → fetch matching PYQ blueprint from YAML templates
5. Augment Gemini prompt with original PYQ as reference context
6. Gemini generates a new MCQ with 4 options + step-by-step solution in strict JSON
7. **2-pass solver validation** — Gemini thinking model solves the question twice; discards if solvers disagree
8. **SequenceMatcher deduplication** — rejects if similarity ratio ≥ 0.82 against existing pool
9. Validated, unique question saved to MongoDB pool and served to user

---

## 📁 Project Structure

```
mockmitra/
├── frontend/          # React + Vite frontend
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   ├── pages/         # Dashboard, Test, Analytics, History
│   │   └── App.jsx
│   └── package.json
│
└── backend/           # FastAPI Python backend
    ├── app/
    │   ├── api/           # Route handlers (tests, users, results)
    │   ├── services/      # QuestionSelector, AIGenerator, Validator
    │   ├── models/        # MongoDB schemas
    │   └── main.py
    ├── exam_configs/      # YAML exam configurations
    ├── pyq_papers/        # Previous Year Question templates
    └── requirements.txt
```

---

## ⚙️ Local Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # Add your Gemini API key and MongoDB URI
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env        # Add your backend API URL
npm run dev
```

### Environment Variables

**Backend `.env`**
```
GEMINI_API_KEY=your_gemini_api_key
MONGODB_URI=your_mongodb_connection_string
JWT_SECRET=your_jwt_secret
```

**Frontend `.env`**
```
VITE_API_URL=http://localhost:8000
```

---

## 📊 Platform Metrics

- **18,000+** test responses processed in production
- **4,700+** AI-generated questions stored in pool
- **130+** registered users organically
- **600+** total platform visitors
- Cache-first architecture reduces Gemini API calls by ~70% for returning users

---

## 🔑 Key Engineering Highlights

- **Cache-first architecture** — MongoDB compound index enables sub-millisecond question retrieval before falling back to AI generation
- **Prompt engineering** — Structured system + user prompts enforce JSON schema constraints (options, answer key, LaTeX math formatting)
- **AI quality control** — 2-pass solver consensus using Gemini thinking budget eliminates hallucinated or mathematically incorrect questions
- **Deduplication pipeline** — SequenceMatcher comparison against full pool prevents question repetition across user sessions
- **Background task processing** — FastAPI background workers handle AI generation asynchronously without blocking the API response

---

## 👨‍💻 Author

**Abhilash Ashadapu**

[GitHub] (https://github.com/Abhilash-226)
Live (https://mockmitra.app)

---

## 📄 License

This project is for educational and portfolio purposes.
