"""
Data contracts.

`LLMAssessment` is the JSON schema Gemini must return (structured output).
It deliberately contains only *judgements*: raw skill ratings, reasons,
evidence quotes and fit analysis. Everything numeric that should be consistent
(experience scaling, the Overall score, the card tier) is computed in
`scoring.py`, not by the model.

`StatCard` is what the API returns to the frontend.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

STAT_KEYS = (
    "technical_proficiency",
    "problem_solving",
    "communication",
    "domain_fit",
    "initiative_impact",
    "adaptability",
)

STAT_LABELS = {
    "technical_proficiency": "Technical Proficiency",
    "problem_solving": "Problem Solving",
    "communication": "Communication",
    "domain_fit": "Domain Fit",
    "initiative_impact": "Initiative & Impact",
    "adaptability": "Adaptability",
}

# FIFA-style three-letter codes shown on the card face.
STAT_CODES = {
    "technical_proficiency": "TEC",
    "problem_solving": "PRB",
    "communication": "COM",
    "domain_fit": "FIT",
    "initiative_impact": "IMP",
    "adaptability": "ADP",
}


# ── What the model returns ──────────────────────────────────────────────────


class LLMStat(BaseModel):
    rating: int = Field(description="Raw 1-99 rating of demonstrated ability, ignoring years of experience")
    reason: str = Field(description="One sentence explaining the rating")
    evidence: str = Field(description="A short verbatim quote from the resume supporting the rating, or empty")


class LLMBulletRewrite(BaseModel):
    original: str = Field(description="A bullet copied verbatim from the resume")
    improved: str = Field(description="The same bullet rewritten to be stronger for the target role, without inventing facts")


class LLMAssessment(BaseModel):
    name: str
    target_role: str
    position: str = Field(description="2-4 letter uppercase abbreviation of the target role, like a football position")
    years_of_experience: float = Field(description="Total years of relevant professional experience, 0 if none")
    technical_proficiency: LLMStat
    problem_solving: LLMStat
    communication: LLMStat
    domain_fit: LLMStat
    initiative_impact: LLMStat
    adaptability: LLMStat
    summary: str = Field(description="One or two sentence scouting report")
    strengths: list[str]
    gaps: list[str]
    bullet_rewrites: list[LLMBulletRewrite]

    @field_validator("name", "target_role", "summary")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


# ── What the API returns ────────────────────────────────────────────────────


class Stat(BaseModel):
    key: str
    label: str
    code: str
    raw_rating: int
    score: int
    reason: str
    evidence: str | None
    evidence_verified: bool


class BulletRewrite(BaseModel):
    original: str
    improved: str


class Meta(BaseModel):
    model: str
    latency_ms: int
    attempts: int
    job_description_provided: bool


class StatCard(BaseModel):
    name: str
    target_role: str
    position: str
    years_of_experience: float
    experience_band: str
    experience_multiplier: float
    overall: int
    tier: Literal["bronze", "silver", "gold"]
    stats: list[Stat]
    summary: str
    strengths: list[str]
    gaps: list[str]
    bullet_rewrites: list[BulletRewrite]
    meta: Meta
