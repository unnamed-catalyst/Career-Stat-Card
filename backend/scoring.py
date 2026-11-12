"""
Deterministic card logic.

v1 asked the model to apply experience multipliers and invent an Overall score
itself, which made results inconsistent (the same resume could get a different
Overall, and the Overall did not always follow from the six stats). v2 moves
all of that arithmetic here:

- The model rates each attribute on demonstrated ability alone (raw 1-99).
- Experience scaling is applied in code with a smooth curve, so 1.9 and 2.1
  years of experience no longer land in different steps.
- The Overall is a fixed weighted average of the six scaled stats.
- Card tier uses FIFA thresholds: gold 75+, silver 65-74, bronze below 65.
- Evidence quotes are kept only if they really appear in the resume text.
"""

from __future__ import annotations

import re

from schemas import (
    STAT_CODES,
    STAT_KEYS,
    STAT_LABELS,
    BulletRewrite,
    LLMAssessment,
    Meta,
    Stat,
    StatCard,
)

SCORE_MIN = 45
SCORE_MAX = 99

# (years, multiplier) anchors from the original v1 bands, now interpolated.
MULTIPLIER_CURVE = [(0.0, 0.80), (2.0, 0.85), (5.0, 0.90), (10.0, 1.00)]

# How much each stat contributes to the Overall rating. Sums to 1.
OVERALL_WEIGHTS = {
    "technical_proficiency": 0.25,
    "problem_solving": 0.20,
    "domain_fit": 0.20,
    "initiative_impact": 0.15,
    "communication": 0.10,
    "adaptability": 0.10,
}

MAX_LIST_ITEMS = 5
MAX_REWRITES = 3


def experience_multiplier(years: float) -> float:
    years = max(0.0, float(years))
    for (x0, y0), (x1, y1) in zip(MULTIPLIER_CURVE, MULTIPLIER_CURVE[1:]):
        if years <= x1:
            return round(y0 + (y1 - y0) * (years - x0) / (x1 - x0), 3)
    return MULTIPLIER_CURVE[-1][1]


def experience_band(years: float) -> str:
    years = max(0.0, float(years))
    if years < 2:
        return "0-2 years"
    if years < 5:
        return "2-5 years"
    if years < 10:
        return "5-10 years"
    return "10+ years"


def clamp(value: float) -> int:
    return int(min(SCORE_MAX, max(SCORE_MIN, round(value))))


def scale_rating(raw: int, multiplier: float) -> int:
    raw = min(99, max(1, int(raw)))
    return clamp(raw * multiplier)


def overall_rating(scores: dict[str, int]) -> int:
    return clamp(sum(scores[k] * w for k, w in OVERALL_WEIGHTS.items()))


def card_tier(overall: int) -> str:
    if overall >= 75:
        return "gold"
    if overall >= 65:
        return "silver"
    return "bronze"


def sanitize_position(position: str, target_role: str) -> str:
    letters = re.sub(r"[^A-Za-z]", "", position or "").upper()
    if 2 <= len(letters) <= 4:
        return letters
    initials = "".join(w[0] for w in re.findall(r"[A-Za-z]+", target_role or ""))
    return (initials.upper() or "PRO")[:4]


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[‐-―]", "-", text)  # unify dashes
    text = re.sub(r"[‘’]", "'", text)
    text = re.sub(r"[“”]", '"', text)
    text = re.sub(r"[•●▪◦·]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def verify_evidence(quote: str, resume_text: str) -> str | None:
    """Return the quote if it really appears in the resume, else None.

    Matching ignores case, whitespace, bullet glyphs and dash/quote styles,
    and tolerates a trailing ellipsis. This is the anti-hallucination check:
    an invented quote is dropped rather than shown to the user.
    """
    if not quote:
        return None
    cleaned = quote.strip().strip('"').strip()
    cleaned = re.sub(r"(\.\.\.|…)$", "", cleaned).strip()
    if len(cleaned) < 8:
        return None
    return cleaned if _normalize(cleaned) in _normalize(resume_text) else None


def _clean_list(items: list[str], limit: int) -> list[str]:
    out = []
    for item in items:
        item = (item or "").strip().lstrip("-•* ").strip()
        if item and item not in out:
            out.append(item)
    return out[:limit]


def build_card(
    assessment: LLMAssessment,
    resume_text: str,
    meta: Meta,
) -> StatCard:
    years = max(0.0, min(60.0, float(assessment.years_of_experience)))
    multiplier = experience_multiplier(years)

    stats: list[Stat] = []
    scores: dict[str, int] = {}
    for key in STAT_KEYS:
        llm_stat = getattr(assessment, key)
        score = scale_rating(llm_stat.rating, multiplier)
        scores[key] = score
        evidence = verify_evidence(llm_stat.evidence, resume_text)
        stats.append(
            Stat(
                key=key,
                label=STAT_LABELS[key],
                code=STAT_CODES[key],
                raw_rating=min(99, max(1, int(llm_stat.rating))),
                score=score,
                reason=llm_stat.reason.strip(),
                evidence=evidence,
                evidence_verified=evidence is not None,
            )
        )

    overall = overall_rating(scores)

    rewrites = [
        BulletRewrite(original=r.original.strip(), improved=r.improved.strip())
        for r in assessment.bullet_rewrites
        if r.improved.strip()
        and r.original.strip() != r.improved.strip()
        # Only rewrite bullets that really exist in the resume.
        and verify_evidence(r.original, resume_text)
    ][:MAX_REWRITES]

    return StatCard(
        name=assessment.name,
        target_role=assessment.target_role.strip(),
        position=sanitize_position(assessment.position, assessment.target_role),
        years_of_experience=round(years, 1),
        experience_band=experience_band(years),
        experience_multiplier=multiplier,
        overall=overall,
        tier=card_tier(overall),
        stats=stats,
        summary=assessment.summary,
        strengths=_clean_list(assessment.strengths, MAX_LIST_ITEMS),
        gaps=_clean_list(assessment.gaps, MAX_LIST_ITEMS),
        bullet_rewrites=rewrites,
        meta=meta,
    )
