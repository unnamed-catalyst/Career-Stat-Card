"""
eval.py — Offline evaluation harness for Career Stat Card.

Tests the core LLM workflow (analyze_resume + parse_response) against
fixture resumes to catch schema failures and score bound violations
before they surface in production.

Usage:
    GEMINI_API_KEY=your_key python eval.py
"""

import sys
from utils import analyze_resume, parse_response

# ── Constants ────────────────────────────────────────────────────────────────

REQUIRED_CATEGORIES = [
    "Technical Proficiency",
    "Problem Solving",
    "Communication",
    "Domain Fit",
    "Initiative & Impact",
    "Adaptability",
    "Overall Score",
]

SCORE_MIN = 45
SCORE_MAX = 99

# ── Fixture resumes ───────────────────────────────────────────────────────────

FIXTURES = [
    {
        "id": "senior_ml_engineer",
        "description": "Senior ML engineer, 8 years experience",
        "resume": """
            Jane Smith
            Senior Machine Learning Engineer — 8 years of experience

            Experience:
            - Led ML platform team at Acme Corp (2019–present): built real-time inference
              pipeline serving 50M predictions/day on AWS SageMaker; reduced p99 latency
              from 420ms to 85ms via model quantisation and batching.
            - ML Engineer at DataCo (2016–2019): shipped NLP classification models for
              customer support routing (92% accuracy); owned model retraining pipeline
              in Airflow.

            Skills: Python, PyTorch, TensorFlow, FastAPI, AWS (SageMaker, Lambda, S3),
            Docker, Kubernetes, SQL, Spark, MLflow, Airflow.

            Education: M.Sc. Computer Science (Machine Learning), Stanford University, 2016.
        """,
        "job_description": "Senior Machine Learning Engineer at a cloud-native AI startup",
        "expected_overall_min": 75,
    },
    {
        "id": "fresh_graduate",
        "description": "Fresh CS graduate, no industry experience",
        "resume": """
            Alex Johnson
            Computer Science Graduate — 0 years of industry experience

            Education: B.Sc. Computer Science, University of Toronto, 2024. GPA 3.7.

            Projects:
            - Built a sentiment analysis classifier using BERT fine-tuning (PyTorch) as
              a course project; achieved 89% accuracy on SST-2.
            - Developed a REST API in Flask for a to-do app; deployed on Heroku.

            Skills: Python, Java, PyTorch, Flask, Git, SQL (basic).
        """,
        "job_description": "Junior Software Engineer",
        "expected_overall_min": 45,
    },
    {
        "id": "career_changer",
        "description": "Finance professional transitioning into ML",
        "resume": """
            Michael Lee
            Quantitative Analyst — 6 years in finance, transitioning to ML engineering

            Experience:
            - Quant Analyst at Hedge Fund XYZ (2018–present): built statistical models
              in Python (pandas, numpy, scikit-learn) for equity signal generation;
              automated reporting pipelines that saved 12 hrs/week.
            - Analyst at Investment Bank ABC (2016–2018): financial modelling in Excel
              and Python; presented findings to senior stakeholders.

            Recent upskilling: Completed fast.ai deep learning course; built an image
            classifier deployed on a Flask API; studying MLOps on Coursera.

            Skills: Python, scikit-learn, pandas, numpy, SQL, Git, basic PyTorch.

            Education: B.Sc. Mathematics & Statistics, McGill University, 2016.
        """,
        "job_description": "Machine Learning Engineer at an automotive AI company",
        "expected_overall_min": 60,
    },
]

# ── Assertions ────────────────────────────────────────────────────────────────


def assert_schema(parsed: dict, fixture_id: str) -> list[str]:
    """Check all required fields are present and non-null."""
    failures = []

    for field in ("name", "target_role", "experience", "overall_score"):
        if not parsed.get(field):
            failures.append(f"[{fixture_id}] Missing required field: '{field}'")

    for category in REQUIRED_CATEGORIES:
        if category not in parsed.get("scores", {}):
            failures.append(f"[{fixture_id}] Missing score category: '{category}'")
        if category not in parsed.get("explanations", {}):
            failures.append(f"[{fixture_id}] Missing explanation for: '{category}'")

    return failures


def assert_score_bounds(parsed: dict, fixture_id: str) -> list[str]:
    """Check all scores fall within [SCORE_MIN, SCORE_MAX]."""
    failures = []
    for category, score in parsed.get("scores", {}).items():
        if not (SCORE_MIN <= score <= SCORE_MAX):
            failures.append(
                f"[{fixture_id}] '{category}' score {score} out of bounds "
                f"[{SCORE_MIN}, {SCORE_MAX}]"
            )
    return failures


def assert_overall_floor(parsed: dict, fixture: dict) -> list[str]:
    """Check overall score meets the fixture's expected minimum."""
    failures = []
    overall = parsed.get("overall_score")
    floor = fixture["expected_overall_min"]
    if overall is not None and overall < floor:
        failures.append(
            f"[{fixture['id']}] Overall score {overall} below expected "
            f"minimum {floor} for '{fixture['description']}'"
        )
    return failures


# ── Runner ────────────────────────────────────────────────────────────────────


def run_eval():
    total = len(FIXTURES)
    passed = 0
    all_failures = []

    print(f"\n{'─' * 55}")
    print(f"  Career Stat Card — Eval Harness ({total} fixtures)")
    print(f"{'─' * 55}\n")

    for fixture in FIXTURES:
        fid = fixture["id"]
        print(f"  Running: {fid} ({fixture['description']}) ...", end=" ", flush=True)

        try:
            raw = analyze_resume(fixture["resume"], fixture["job_description"])
            parsed = parse_response(raw)
            # print(f"    parsed: {parsed}")
        except Exception as e:
            msg = f"[{fid}] Exception during LLM call or parse: {e}"
            all_failures.append(msg)
            print("FAIL")
            continue

        failures = (
            assert_schema(parsed, fid)
            + assert_score_bounds(parsed, fid)
            + assert_overall_floor(parsed, fixture)
        )

        if failures:
            all_failures.extend(failures)
            print("FAIL")
        else:
            passed += 1
            overall = parsed.get("overall_score", "?")
            print(f"PASS  (overall: {overall})")

    print(f"\n{'─' * 55}")
    print(f"  Results: {passed}/{total} passed\n")

    if all_failures:
        print("  Failures:")
        for f in all_failures:
            print(f"    ✗ {f}")
        print()
        sys.exit(1)
    else:
        print("  All checks passed.")
        print(f"{'─' * 55}\n")
        sys.exit(0)


if __name__ == "__main__":
    run_eval()
