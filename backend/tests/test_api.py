import pytest
from fastapi.testclient import TestClient

import analyzer
import main
from conftest import make_pdf


@pytest.fixture
def client(monkeypatch, assessment):
    def fake_assess(resume_text, job_description, runtime=None):
        assert "Alex Johnson" in resume_text
        return assessment, "gemini-test", 1

    monkeypatch.setattr(analyzer, "assess", fake_assess)
    monkeypatch.setattr(main, "limiter", main.RateLimiter(3, 600))
    return TestClient(main.app)


def post(client, data: bytes, name="resume.pdf", ctype="application/pdf", job=""):
    return client.post("/analyze", files={"file": (name, data, ctype)}, data={"job_description": job})


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert "model" in body


def test_analyze_happy_path(client):
    res = post(client, make_pdf(), job="Backend Engineer")
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Alex Johnson"
    assert len(body["stats"]) == 6
    assert 45 <= body["overall"] <= 99
    assert body["tier"] in ("bronze", "silver", "gold")
    assert body["meta"]["model"] == "gemini-test"
    assert body["meta"]["job_description_provided"] is True


def test_rejects_non_pdf(client):
    res = post(client, b"hello", name="resume.txt", ctype="text/plain")
    assert res.status_code == 400
    assert res.json()["code"] == "not_pdf"


def test_rejects_fake_pdf(client):
    res = post(client, b"not really a pdf")
    assert res.status_code == 400


def test_rejects_large_upload(client):
    res = post(client, b"%PDF" + b"0" * (main.MAX_UPLOAD_BYTES + 10))
    assert res.status_code == 413


def test_empty_pdf_gives_helpful_error(client):
    res = post(client, make_pdf(" "))
    assert res.status_code == 422
    assert "scanned" in res.json()["error"]


def test_path_traversal_filename_is_harmless(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    res = post(client, make_pdf(), name="../../evil.pdf")
    assert res.status_code == 200
    assert list(tmp_path.iterdir()) == []  # nothing written to disk


def test_rate_limit(client):
    pdf = make_pdf()
    codes = [post(client, pdf).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]


def test_model_errors_are_not_leaked(client, monkeypatch):
    def boom(*a, **k):
        raise analyzer.AnalysisError("The AI service is busy right now.", 503, "model_unavailable")

    monkeypatch.setattr(analyzer, "assess", boom)
    res = post(client, make_pdf())
    assert res.status_code == 503
    assert res.json() == {"error": "The AI service is busy right now.", "code": "model_unavailable"}


def test_cors_allows_pages_origin_only(client):
    ok = client.options("/analyze", headers={"Origin": "https://unnamed-catalyst.github.io", "Access-Control-Request-Method": "POST"})
    bad = client.options("/analyze", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "https://unnamed-catalyst.github.io"
    assert "access-control-allow-origin" not in bad.headers

