# Career Stat Card — Code Sample

> LLM workflow: PDF resume → structured Gemini prompt → parsed stat card with per-dimension rationales.

Live demo: https://unnamed-catalyst.github.io/Career-Stat-Card/  
API (Swagger): https://career-stat-cards.onrender.com/docs

---

## What this does

Takes an uploaded resume (PDF) and an optional job description, runs a single
Gemini Flash call, and returns a structured JSON card with six scored career
dimensions plus one-line rationales for each.

```
POST /analyze
  ├── PDF extraction      (PyMuPDF)
  ├── Prompt construction (experience-scaled scoring instructions)
  ├── Gemini call         (auto-selects latest flash model)
  ├── Regex parse         (deterministic markdown schema → dict)
  └── JSON response       (name, role, experience, 7 scores + explanations)
```

---

## Design decisions & trade-offs

### 1. Constrained markdown schema over JSON-mode output

Gemini's JSON-mode output was inconsistent across model versions during development —
field names drifted and nesting changed. Instead, the prompt enforces a strict
markdown contract (`**[Category] - [Score]**`) that a simple regex parser can
reliably extract regardless of which flash model is active.

**Trade-off:** regex parsing is brittle if the model deviates from the schema.
A v2 would replace this with Pydantic-validated structured output plus a retry
loop on validation failure.

### 2. Experience-scaling in the prompt, not post-hoc

Scoring multipliers (0.8× for 0–2 yrs → 1.0× for 10+ yrs) live inside the
prompt rather than being applied after the fact. This keeps the model's
reasoning grounded — it calibrates *during* generation rather than having
scores rescaled blindly afterward.

**Trade-off:** the model must infer YOE from the resume text, which can be
imprecise for non-linear careers. A future improvement would extract YOE as an
explicit structured field first, then pass it as a variable.

### 3. Role-fit vs domain-fit separation

A deliberate prompt instruction ensures an ML engineer from finance scores well
on a healthcare ML role. Most keyword-based tools penalise industry switches;
this approach scores transferable skill alignment instead.

### 4. Single-call architecture

No embeddings, no vector DB, no retrieval step — just one LLM call per
request. This keeps latency low (1–2 s warm) and cost near zero at hobby scale.

**Trade-off:** the model has no external grounding for what "good" looks like
in a given role. A v2 would add RAG over job description corpora to make
Domain Fit scores empirically grounded.

### 5. Auto model selection

`get_latest_flash_model()` enumerates the Gemini API at runtime and picks the
highest-sorted flash model name. This means the app transparently upgrades as
Google releases new versions without a code change.

**Trade-off:** non-deterministic model selection can cause subtle prompt
regressions. A production system would pin the model version and run an eval
suite before upgrading.

---

## File structure

```
backend/
├── main.py        # FastAPI app — single POST /analyze endpoint
├── utils.py       # PDF parse, Gemini call, response parser
├── Dockerfile
└── requirements.txt

frontend/
└── src/           # React + Vite — renders the stat card UI
```

---

## Running locally

```bash
# Backend
cd backend
docker build -t career-stat-api .
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key career-stat-api

# Frontend
cd frontend
npm install
npm run dev
```

---

## What v2 would add

- **Pydantic output validation + retry** — catch schema failures before they surface to the user
- **Eval harness** — fixture resumes with expected score ranges; assert bounds on every prompt change
- **RAG for Domain Fit** — retrieve role benchmarks to ground scores in real data
- **Async task queue (Celery/Redis)** — eliminate cold-start latency with a worker + polling pattern
- **Engagement instrumentation** — log score distributions and re-run rates to drive prompt improvements
