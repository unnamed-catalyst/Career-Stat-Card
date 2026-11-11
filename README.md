# Career Stat Card

> Upload a resume and the job you want. Get a FIFA-style player card: six career stats scored against the role, the resume evidence behind each one, the gaps to close, and stronger rewrites of your own bullets.

Live demo: https://unnamed-catalyst.github.io/Career-Stat-Card/ (add `?example` to see a sample card)
API (Swagger): https://career-stat-cards.onrender.com/docs

---

## What it does

```
POST /analyze  (PDF + optional job description)
  ├── Validate upload       PDF only, ≤ 5 MB, read in memory (never written to disk)
  ├── Extract text          PyMuPDF
  ├── Assess                Gemini Flash, structured JSON output (Pydantic schema)
  │     ├── validate + retry once on malformed output
  │     └── fail over to the next model on quota / outage / retired model
  ├── Score deterministically
  │     ├── experience scaling   smooth curve ×0.80 (0 yrs) → ×1.00 (10+ yrs)
  │     ├── Overall              fixed weighted average of the six stats
  │     ├── tier                 gold 75+, silver 65–74, bronze < 65
  │     └── evidence check       quotes kept only if found verbatim in the resume
  └── JSON card               stats, reasons, evidence, strengths, gaps, rewrites, meta
```

The frontend (React + Vite, GitHub Pages) renders the card, a stats / job-fit / improve breakdown, and exports the card as a PNG.

## v2: what changed and why

v1 (June 2025) was a single prompt plus a regex parser. It broke in November 2026 when the
"pick the latest Flash model" code sorted model names alphabetically and chose a preview
model with no free-tier quota. v2 rebuilds the pipeline around that lesson.

### 1. Model selection that can't take the app down
`model_selector.py` lists models at runtime and keeps only **stable text Flash models**
(`gemini-X.Y-flash`), skipping preview, experimental, TTS, image, audio, live and other
variants. It sorts by **parsed version number** (3.10 > 3.9), not alphabetically.

Failover order: newest version first → `gemini-flash-latest` → Flash-Lite models. A model that fails is put on a cooldown (Google's retry delay
for quota errors, 1 day for paid-only or retired models, 5 min for outages) and the last working model is tried first until the hourly
refresh. If a call hasn't answered within 12 s, the next model is started in parallel
(hedged requests, up to 3 at once) and the first valid answer wins, so one overloaded
model can't stall a request. The whole request is capped at 60 s.
**It adapts to whatever the API key can use for free.** On startup (and hourly) the
server pings the ranked models with a tiny prompt and settles on the first that answers;
the page's `/health` wake-up ping triggers this, so a working model is usually known
before the user clicks Generate. Quota errors are read, not just counted: a model whose
free-tier limit is 0 (paid only) is skipped for a day, and a rate-limited model is skipped
for exactly the retry delay Google reports. `/health` shows the model in use.
`GEMINI_MODEL` pins a model when you need reproducibility.

### 2. Structured output instead of regex parsing
v1 parsed a markdown format with regex because JSON mode drifted between model versions.
v2 passes a Pydantic schema as Gemini's `response_schema`, validates the reply, retries
once on a malformed answer and then fails over, so the frontend always gets one shape.

### 3. Card logic moved out of the prompt
In v1 the model applied experience multipliers and made up the Overall itself, so the
Overall didn't always follow from the six stats, and 1.9 vs 2.1 years fell into different
steps. Now the model only rates demonstrated ability; `scoring.py` applies the experience
curve, the weighted Overall (25% TEC, 20% PRB, 20% FIT, 15% IMP, 10% COM, 10% ADP), the
45–99 clamp and the tier. The same assessment always produces the same card.

### 4. Grounded feedback
Every stat comes with a quote from the resume. The server keeps a quote only if it
appears in the resume text (ignoring case, whitespace and dash styles); invented quotes
are dropped. Bullet rewrites are only offered for bullets that really exist, and the
prompt forbids adding facts. The resume is wrapped as untrusted data in the prompt.

### 5. Production hygiene
Uploads are processed in memory (no filename-based temp files), PDF type and size are
checked, CORS is limited to the site's origins, upstream errors are never leaked to the
client, there is a per-IP rate limit, dependencies are pinned, and the Docker image runs
as a non-root user with `.env` excluded.

## Testing and evaluation

**Unit tests** (`backend/tests`, 70 tests, no API key needed): scoring maths, the evidence
check, model ranking and cooldowns, failover and retry behaviour with a fake client, the
time budget, and API validation (non-PDF, oversize, empty PDF, path-traversal filename,
rate limiting, CORS, error hygiene).

**Live eval** (`backend/eval.py`): 6 fictional personas (senior ML engineer, new graduate,
career changer, staff backend engineer, data analyst, and a graphic designer applying for
a backend role) run through the real pipeline. It checks that each Overall lands in a
hand-set expected band, that stronger candidates outrank weaker ones, run-to-run
consistency (std dev), evidence grounding, and p50/p95 latency. It writes
`eval_results/latest.md` and exits 1 on failure.

Latest live run (11 Nov 2026, free-tier key, 6 personas x 2 runs):

| Check | Result |
| --- | --- |
| Valid cards | 12/12 |
| Overall within expected band | 6/6 personas |
| Ordering (stronger outranks weaker) | 3/3 pairs |
| Evidence quotes verified in resume | 68/68 |
| Run-to-run Overall std dev | 0 to 4.5 points (max on the new-graduate persona) |
| Latency | p50 11.5 s, p95 39.2 s |

That day the newest Flash models were rate-limited (429) or overloaded (503) on the free
tier, so failover served the cards from `gemini-3.6-flash`, `gemini-3.5-flash` and Flash-Lite
models. The spread and the p95 reflect that mix of models. An earlier run on the same day,
before hedged failover, produced 11/12 cards with p50 3.0 s.

**CI** (`.github/workflows`): unit tests, lint and build on every push; the live eval on
pull requests and weekly (needs the `GEMINI_API_KEY` repository secret), so a new Gemini
release that breaks scoring is caught within a week.

## Running locally

```bash
# Backend
cd backend
pip install -r requirements-dev.txt
export GEMINI_API_KEY=your_key
uvicorn main:app --reload            # http://localhost:8000/docs
python -m pytest -q tests            # unit tests
python eval.py --runs 2              # live eval

# or with Docker
docker build -t career-stat-api . && docker run -p 8000:8000 -e GEMINI_API_KEY=your_key career-stat-api

# Frontend
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

Environment variables: `GEMINI_API_KEY` (required), `GEMINI_MODEL` (optional pin),
`ALLOWED_ORIGINS` (comma-separated), `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_S`.

## File structure

```
backend/
├── main.py             FastAPI app: /analyze, /health, validation, rate limit, CORS
├── analyzer.py         PDF text, prompt, Gemini call with retry + failover
├── model_selector.py   model ranking, cooldowns, sticky preference
├── scoring.py          deterministic card logic + evidence verification
├── schemas.py          Pydantic contracts (LLM output and API response)
├── eval.py             live eval harness; fixtures in eval_fixtures.py
└── tests/              pytest unit tests
frontend/src/
├── App.jsx             page flow: upload → loading → card + breakdown
├── api.js              fetch with timeouts, server warm-up ping
└── components/         UploadForm, LoadingCard, PlayerCard, ResultPanel, CardActions
```

## Limitations

- Ratings are an AI estimate for fun and self-reflection, not a hiring assessment. The eval
  bands are the author's sanity checks, not labelled ground truth.
- The free Render tier sleeps; the first request after idle can take up to a minute (the
  page pings `/health` on load to start waking it early).
- The rate limiter is in memory, which is fine for one instance.
