import pytest

from conftest import RESUME_TEXT
from schemas import Meta
from scoring import (
    OVERALL_WEIGHTS,
    build_card,
    card_tier,
    experience_band,
    experience_multiplier,
    overall_rating,
    sanitize_position,
    scale_rating,
    verify_evidence,
)

META = Meta(model="gemini-test", latency_ms=1, attempts=1, job_description_provided=True)


def test_weights_sum_to_one():
    assert sum(OVERALL_WEIGHTS.values()) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "years, expected",
    [(0, 0.80), (1, 0.825), (2, 0.85), (3.5, 0.875), (5, 0.90), (7.5, 0.95), (10, 1.0), (25, 1.0), (-3, 0.80)],
)
def test_multiplier_curve(years, expected):
    assert experience_multiplier(years) == pytest.approx(expected)


def test_multiplier_is_monotonic_and_has_no_cliffs():
    values = [experience_multiplier(y / 10) for y in range(0, 151)]
    assert values == sorted(values)
    assert max(b - a for a, b in zip(values, values[1:])) < 0.01


@pytest.mark.parametrize("years, band", [(0, "0-2 years"), (1.99, "0-2 years"), (2, "2-5 years"), (5, "5-10 years"), (12, "10+ years")])
def test_experience_band(years, band):
    assert experience_band(years) == band


def test_scale_rating_clamps_to_card_range():
    assert scale_rating(99, 1.0) == 99
    assert scale_rating(10, 0.8) == 45
    assert scale_rating(150, 1.0) == 99
    assert scale_rating(90, 0.8) == 72


def test_overall_is_weighted_average():
    scores = dict.fromkeys(OVERALL_WEIGHTS, 70)
    assert overall_rating(scores) == 70
    scores["technical_proficiency"] = 90
    assert overall_rating(scores) == 75  # 70 + 20 * 0.25


@pytest.mark.parametrize("overall, tier", [(45, "bronze"), (64, "bronze"), (65, "silver"), (74, "silver"), (75, "gold"), (99, "gold")])
def test_tiers(overall, tier):
    assert card_tier(overall) == tier


@pytest.mark.parametrize(
    "position, role, expected",
    [("mle", "ML Engineer", "MLE"), ("S.W.E.", "x", "SWE"), ("", "Data Analyst", "DA"), ("TOOLONGX", "Product Manager", "PM"), ("", "", "PRO")],
)
def test_sanitize_position(position, role, expected):
    assert sanitize_position(position, role) == expected


def test_verify_evidence_accepts_real_quotes_with_formatting_noise():
    assert verify_evidence("built a REST API in FastAPI serving 2M requests", RESUME_TEXT)
    assert verify_evidence('"Led migration of a monolith to   Docker containers…"', RESUME_TEXT)


def test_verify_evidence_rejects_invented_or_tiny_quotes():
    assert verify_evidence("Invented quote that is not in the resume", RESUME_TEXT) is None
    assert verify_evidence("Python", RESUME_TEXT) is None
    assert verify_evidence("", RESUME_TEXT) is None


def test_build_card(assessment):
    card = build_card(assessment, RESUME_TEXT, META)
    by_key = {s.key: s for s in card.stats}

    assert card.experience_multiplier == pytest.approx(0.867)
    assert by_key["technical_proficiency"].score == round(85 * 0.867)
    assert card.overall == overall_rating({s.key: s.score for s in card.stats})
    assert card.tier == card_tier(card.overall)
    assert card.experience_band == "2-5 years"

    # Evidence: real quotes kept, invented ones dropped.
    assert by_key["technical_proficiency"].evidence_verified
    assert not by_key["problem_solving"].evidence_verified
    assert by_key["problem_solving"].evidence is None

    # Lists are de-duplicated; rewrites of invented bullets are dropped.
    assert card.strengths == ["APIs", "Cloud"]
    assert len(card.bullet_rewrites) == 1


def test_build_card_same_input_same_numbers(assessment):
    a = build_card(assessment, RESUME_TEXT, META)
    b = build_card(assessment, RESUME_TEXT, META)
    assert a.model_dump() == b.model_dump()


def test_new_grad_cannot_reach_gold_on_raw_ratings_alone():
    from conftest import assessment_dict
    from schemas import LLMAssessment

    data = assessment_dict(years_of_experience=0)
    for key in OVERALL_WEIGHTS:
        data[key]["rating"] = 92
    card = build_card(LLMAssessment.model_validate(data), RESUME_TEXT, META)
    assert card.overall == 74  # 92 * 0.8 = 73.6
    assert card.tier == "silver"
