import json

import pytest

import analyzer
from conftest import RESUME_TEXT, assessment_dict
from model_selector import DAY, STATIC_FALLBACKS, ModelSelector, cooldown_for_error, rank_models

GEN = ["generateContent", "countTokens"]

# Snapshot of a real model listing (Nov 2026), trimmed.
LISTING = [
    ("models/gemini-2.5-flash", GEN),
    ("models/gemini-2.5-flash-preview-tts", GEN),
    ("models/gemini-flash-latest", GEN),
    ("models/gemini-flash-lite-latest", GEN),
    ("models/gemini-2.5-flash-lite", GEN),
    ("models/gemini-3-flash-preview", GEN),
    ("models/gemini-3.1-flash-image", GEN),
    ("models/gemini-3.5-flash", GEN),
    ("models/gemini-3.5-flash-lite", GEN),
    ("models/gemini-omni-flash-preview", GEN),  # the model that broke v1
    ("models/gemini-omni-1.2-flash", GEN),
    ("models/gemini-3.8-flash", GEN),
    ("models/gemini-3.8-flash-tts", GEN),
    ("models/gemini-3.10-flash", GEN),
    ("models/gemini-3.1-flash-live-preview", ["bidiGenerateContent"]),
    ("models/gemini-9-flash", ["bidiGenerateContent"]),
]


def test_rank_models_prefers_newest_stable_flash_by_version_number():
    ranked = rank_models(LISTING)
    # Newest first by version number, then the alias, then Flash-Lite.
    assert ranked == [
        "gemini-3.10-flash",
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash-lite",
        "gemini-flash-lite-latest",
    ]


def test_rank_models_excludes_preview_omni_tts_image_live():
    ranked = rank_models(LISTING)
    for bad in ("omni", "preview", "tts", "image", "live", "gemini-9-flash"):
        assert not any(bad in m for m in ranked)


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_selector_falls_back_to_static_list_when_listing_fails():
    def broken():
        raise RuntimeError("network down")

    assert ModelSelector(broken).candidates()[: len(STATIC_FALLBACKS)] == STATIC_FALLBACKS


def test_selector_pins_env_model_first():
    sel = ModelSelector(lambda: LISTING, pinned="models/gemini-2.5-flash")
    assert sel.candidates()[0] == "gemini-2.5-flash"


def test_selector_cooldown_skips_then_recovers():
    clock = FakeClock()
    sel = ModelSelector(lambda: LISTING, clock=clock)
    sel.mark_failed("gemini-3.10-flash", 60)
    assert sel.candidates()[0] == "gemini-3.8-flash"
    clock.t = 61
    assert sel.candidates()[0] == "gemini-3.10-flash"


def test_selector_never_returns_empty_list():
    sel = ModelSelector(lambda: [("models/gemini-2.5-flash", GEN)])
    for m in sel.candidates():
        sel.mark_failed(m, 999)
    assert sel.candidates()


# ── analyzer failover ───────────────────────────────────────────────────────


class FakeAPIError(Exception):
    def __init__(self, code):
        super().__init__(f"status {code}")
        self.code = code


def make_runtime(responses):
    """responses: model -> list of results (str JSON or Exception), consumed in order."""
    calls = []

    def generate(client, model, prompt, timeout_s=None):
        calls.append(model)
        queue = responses.get(model, [FakeAPIError(404)])
        result = queue.pop(0) if queue else FakeAPIError(404)
        if isinstance(result, Exception):
            raise result
        return result

    selector = ModelSelector(lambda: [("models/gemini-3.8-flash", GEN), ("models/gemini-2.5-flash", GEN)])
    return analyzer._Runtime(client=None, selector=selector), generate, calls


GOOD = json.dumps(assessment_dict())


def test_quota_error_fails_over_to_next_model(monkeypatch):
    runtime, generate, calls = make_runtime({"gemini-3.8-flash": [FakeAPIError(429)], "gemini-2.5-flash": [GOOD]})
    monkeypatch.setattr(analyzer, "_generate", generate)
    assessment, model, attempts = analyzer.assess(RESUME_TEXT, "", runtime)
    assert model == "gemini-2.5-flash"
    assert calls == ["gemini-3.8-flash", "gemini-2.5-flash"]
    # The failed model is skipped on the next request.
    assert runtime.selector.candidates()[0] == "gemini-2.5-flash"


def test_invalid_json_is_retried_on_same_model(monkeypatch):
    runtime, generate, calls = make_runtime({"gemini-3.8-flash": ["{not json", GOOD]})
    monkeypatch.setattr(analyzer, "_generate", generate)
    _, model, attempts = analyzer.assess(RESUME_TEXT, "", runtime)
    assert (model, attempts) == ("gemini-3.8-flash", 2)


def test_schema_violation_is_retried(monkeypatch):
    bad = json.dumps(assessment_dict(name="  "))
    runtime, generate, calls = make_runtime({"gemini-3.8-flash": [bad, bad], "gemini-2.5-flash": [GOOD]})
    monkeypatch.setattr(analyzer, "_generate", generate)
    _, model, attempts = analyzer.assess(RESUME_TEXT, "", runtime)
    assert (model, attempts) == ("gemini-2.5-flash", 3)


def test_auth_error_stops_immediately(monkeypatch):
    runtime, generate, calls = make_runtime({"gemini-3.8-flash": [FakeAPIError(403)]})
    monkeypatch.setattr(analyzer, "_generate", generate)
    with pytest.raises(analyzer.AnalysisError) as err:
        analyzer.assess(RESUME_TEXT, "", runtime)
    assert err.value.code == "misconfigured"
    assert calls == ["gemini-3.8-flash"]


def test_all_models_failing_gives_friendly_error(monkeypatch):
    runtime, generate, calls = make_runtime({})
    monkeypatch.setattr(analyzer, "_generate", generate)
    with pytest.raises(analyzer.AnalysisError) as err:
        analyzer.assess(RESUME_TEXT, "", runtime)
    assert err.value.code == "model_unavailable"
    assert len(calls) <= analyzer.MAX_MODELS_PER_REQUEST


def test_prompt_wraps_resume_and_handles_missing_job():
    prompt = analyzer.build_prompt("RESUME BODY", "")
    assert "<resume>\nRESUME BODY\n</resume>" in prompt
    assert "Infer the job title" in prompt
    assert "<job_description>" in analyzer.build_prompt("x", "Data Analyst")


def test_selector_prefers_last_working_model_until_refresh():
    clock = FakeClock()
    sel = ModelSelector(lambda: LISTING, clock=clock)
    sel.candidates()  # first request lists models
    sel.mark_ok("gemini-3.5-flash")
    assert sel.candidates()[0] == "gemini-3.5-flash"
    clock.t = 3601  # hourly refresh: try the newest again
    assert sel.candidates()[0] == "gemini-3.10-flash"


def test_slow_model_is_hedged_with_next_model(monkeypatch):
    import time as _time

    calls = []

    def generate(client, model, prompt, timeout_s=None):
        calls.append(model)
        if model == "gemini-3.8-flash":
            _time.sleep(0.6)  # overloaded: hangs, then fails
            raise FakeAPIError(503)
        return GOOD

    runtime, _, _ = make_runtime({})
    monkeypatch.setattr(analyzer, "_generate", generate)
    monkeypatch.setattr(analyzer, "HEDGE_AFTER_S", 0.05)
    started = _time.monotonic()
    _, model, attempts = analyzer.assess(RESUME_TEXT, "", runtime)
    assert model == "gemini-2.5-flash"
    assert calls == ["gemini-3.8-flash", "gemini-2.5-flash"]
    assert _time.monotonic() - started < 0.5  # did not wait for the slow model


def test_time_budget_is_enforced(monkeypatch):
    import time as _time

    def generate(client, model, prompt, timeout_s=None):
        _time.sleep(2)
        return GOOD

    runtime, _, _ = make_runtime({})
    monkeypatch.setattr(analyzer, "_generate", generate)
    monkeypatch.setattr(analyzer, "TOTAL_BUDGET_S", 0.3)
    monkeypatch.setattr(analyzer, "MIN_CALL_S", 0.01)
    monkeypatch.setattr(analyzer, "HEDGE_AFTER_S", 0.1)
    started = _time.monotonic()
    with pytest.raises(analyzer.AnalysisError):
        analyzer.assess(RESUME_TEXT, "", runtime)
    assert _time.monotonic() - started < 0.6


# ── adaptive cooldowns and probing ──────────────────────────────────────────

PAID_ONLY = "429 RESOURCE_EXHAUSTED. Quota exceeded for metric: free_tier_requests, limit: 0, model: gemini-x"
PER_MINUTE = "429 RESOURCE_EXHAUSTED. limit: 10 ... {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '41s'}"
DAILY = "429 RESOURCE_EXHAUSTED. limit: 250 ... 'retryDelay': '44610s'"


@pytest.mark.parametrize(
    "status, message, expected",
    [
        (429, PAID_ONLY, DAY),
        (429, PER_MINUTE, 41),
        (429, DAILY, 44610),
        (429, "429 slow down", 15 * 60),
        (429, "'retryDelay': '2s'", 30),  # floor
        (404, "no longer available to new users", DAY),
        (400, "model does not support", DAY),
        (503, "overloaded", 5 * 60),
        (None, "ReadTimeout", 5 * 60),
    ],
)
def test_cooldown_for_error(status, message, expected):
    assert cooldown_for_error(status, message) == expected


def test_probe_stops_at_first_usable_model(monkeypatch):
    pinged = []

    def ping(client, model):
        pinged.append(model)
        if model == "gemini-3.8-flash":
            raise FakeAPIError(429)

    runtime, _, _ = make_runtime({})
    monkeypatch.setattr(analyzer, "_ping", ping)
    assert analyzer.probe_models(runtime) == "gemini-2.5-flash"
    assert pinged == ["gemini-3.8-flash", "gemini-2.5-flash"]
    # Requests now start with the model the probe found.
    assert runtime.selector.candidates()[0] == "gemini-2.5-flash"
    assert runtime.selector.preferred == "gemini-2.5-flash"


def test_probe_returns_none_when_nothing_works(monkeypatch):
    def ping(client, model):
        raise FakeAPIError(503)

    runtime, _, _ = make_runtime({})
    monkeypatch.setattr(analyzer, "_ping", ping)
    assert analyzer.probe_models(runtime) is None
