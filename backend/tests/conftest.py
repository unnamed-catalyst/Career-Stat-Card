import os
import sys
from pathlib import Path

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DISABLE_MODEL_PROBE"] = "1"  # no background API calls in tests

from schemas import LLMAssessment  # noqa: E402

RESUME_TEXT = """Alex Johnson
Software Engineer, 3 years of experience
- Built a REST API in FastAPI serving 2M requests per day with p99 latency under 80ms.
- Led migration of a monolith to Docker containers on AWS ECS.
- Mentored two junior engineers and ran weekly code reviews.
Skills: Python, FastAPI, PostgreSQL, Docker, AWS, React
"""


def make_pdf(text: str = RESUME_TEXT) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(40, 40, 560, 800), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


def assessment_dict(**overrides) -> dict:
    stat = lambda rating, evidence="": {"rating": rating, "reason": "Because.", "evidence": evidence}  # noqa: E731
    data = {
        "name": "Alex Johnson",
        "target_role": "Backend Engineer",
        "position": "BE",
        "years_of_experience": 3,
        "technical_proficiency": stat(85, "Built a REST API in FastAPI serving 2M requests per day"),
        "problem_solving": stat(80, "Invented quote that is not in the resume at all"),
        "communication": stat(70, "Mentored two junior engineers"),
        "domain_fit": stat(82),
        "initiative_impact": stat(78, "Led migration of a monolith to Docker containers"),
        "adaptability": stat(72),
        "summary": "Solid backend engineer.",
        "strengths": ["APIs", "Cloud", "APIs"],
        "gaps": ["Kubernetes"],
        "bullet_rewrites": [
            {
                "original": "Mentored two junior engineers and ran weekly code reviews.",
                "improved": "Mentored 2 junior engineers through weekly code reviews.",
            },
            {"original": "Made up bullet that does not exist", "improved": "Something better"},
        ],
    }
    data.update(overrides)
    return data


@pytest.fixture
def assessment() -> LLMAssessment:
    return LLMAssessment.model_validate(assessment_dict())
