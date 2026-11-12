"""
eval.py: live evaluation harness for Career Stat Card.

Runs fixture personas through the real Gemini pipeline (prompt, structured
output, validation, failover, deterministic scoring) and measures:

- Validity: every run returns a schema-valid card.
- Calibration: each persona's Overall lands in its expected band.
- Ordering: stronger candidates outrank weaker ones (e.g. senior > new grad).
- Consistency: standard deviation of the Overall across repeated runs.
- Grounding: share of evidence quotes found verbatim in the resume.
- Latency: p50 / p95 seconds per analysis, and which models served them.

Usage:
    GEMINI_API_KEY=... python eval.py                 # 2 runs per persona
    GEMINI_API_KEY=... python eval.py --runs 3 --model gemini-2.5-flash
    python eval.py --max-std 4                        # fail if a persona varies more

Writes eval_results/report-<timestamp>.json and eval_results/latest.md.
Exits 1 if any check fails, so it can gate CI.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import analyzer  # noqa: E402
from eval_fixtures import FIXTURES, ORDERING  # noqa: E402
from schemas import Meta  # noqa: E402
from scoring import build_card  # noqa: E402

RESULTS_DIR = Path(__file__).parent / "eval_results"


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct / 100
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def run_once(fixture: dict) -> dict:
    started = time.perf_counter()
    try:
        assessment, model, attempts = analyzer.assess(fixture["resume"], fixture["job_description"])
    except analyzer.AnalysisError as exc:
        return {"ok": False, "error": exc.code, "seconds": time.perf_counter() - started}
    seconds = time.perf_counter() - started
    meta = Meta(model=model, latency_ms=int(seconds * 1000), attempts=attempts, job_description_provided=True)
    card = build_card(assessment, fixture["resume"], meta)
    quotes = [s for s in assessment.model_dump().values() if isinstance(s, dict) and s.get("evidence")]
    return {
        "ok": True,
        "seconds": seconds,
        "model": model,
        "attempts": attempts,
        "overall": card.overall,
        "tier": card.tier,
        "years": card.years_of_experience,
        "scores": {s.code: s.score for s in card.stats},
        "evidence_given": len(quotes),
        "evidence_verified": sum(s.evidence_verified for s in card.stats),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=2, help="runs per persona (default 2)")
    parser.add_argument("--model", help="pin a model, e.g. gemini-2.5-flash")
    parser.add_argument("--max-std", type=float, default=5.0, help="max Overall std dev per persona")
    parser.add_argument("--sleep", type=float, default=2.0, help="seconds between calls (rate limits)")
    parser.add_argument("--only", nargs="*", help="persona ids to run")
    args = parser.parse_args()

    if args.model:
        os.environ["GEMINI_MODEL"] = args.model
    fixtures = [f for f in FIXTURES if not args.only or f["id"] in args.only]

    print(f"\nCareer Stat Card eval: {len(fixtures)} personas x {args.runs} runs\n")
    results: dict[str, list[dict]] = {}
    for fx in fixtures:
        results[fx["id"]] = []
        for i in range(args.runs):
            r = run_once(fx)
            results[fx["id"]].append(r)
            status = f"overall {r['overall']:>2} {r['tier']:<6} {r['seconds']:5.1f}s {r['model']}" if r["ok"] else f"ERROR {r['error']}"
            print(f"  {fx['id']:<20} run {i + 1}: {status}")
            time.sleep(args.sleep)

    failures: list[str] = []
    rows = []
    for fx in fixtures:
        runs = results[fx["id"]]
        ok_runs = [r for r in runs if r["ok"]]
        if len(ok_runs) < len(runs):
            failures.append(f"{fx['id']}: {len(runs) - len(ok_runs)} run(s) returned no card")
        if not ok_runs:
            rows.append({"id": fx["id"], "valid": f"0/{len(runs)}"})
            continue
        overalls = [r["overall"] for r in ok_runs]
        lo, hi = fx["expected_overall"]
        mean = statistics.mean(overalls)
        std = statistics.pstdev(overalls) if len(overalls) > 1 else 0.0
        in_band = all(lo <= o <= hi for o in overalls)
        if not in_band:
            failures.append(f"{fx['id']}: Overall {overalls} outside expected {lo}-{hi}")
        if std > args.max_std:
            failures.append(f"{fx['id']}: Overall std dev {std:.1f} > {args.max_std}")
        rows.append(
            {
                "id": fx["id"],
                "valid": f"{len(ok_runs)}/{len(runs)}",
                "overalls": overalls,
                "mean": round(mean, 1),
                "std": round(std, 2),
                "expected": f"{lo}-{hi}",
                "in_band": in_band,
            }
        )

    means = {r["id"]: r["mean"] for r in rows if "mean" in r}
    ordering = []
    for higher, lower in ORDERING:
        if higher in means and lower in means:
            passed = means[higher] > means[lower]
            ordering.append({"higher": higher, "lower": lower, "passed": passed})
            if not passed:
                failures.append(f"ordering: {higher} ({means[higher]}) should beat {lower} ({means[lower]})")

    all_ok = [r for runs in results.values() for r in runs if r["ok"]]
    total_runs = sum(len(v) for v in results.values())
    secs = [r["seconds"] for r in all_ok]
    given = sum(r["evidence_given"] for r in all_ok)
    verified = sum(r["evidence_verified"] for r in all_ok)
    models: dict[str, int] = {}
    for r in all_ok:
        models[r["model"]] = models.get(r["model"], 0) + 1

    summary = {
        "valid_cards": f"{len(all_ok)}/{total_runs}",
        "in_band": f"{sum(1 for r in rows if r.get('in_band'))}/{len(rows)}",
        "ordering": f"{sum(o['passed'] for o in ordering)}/{len(ordering)}",
        "max_std": max((r["std"] for r in rows if "std" in r), default=None),
        "latency_p50_s": round(percentile(secs, 50), 1) if secs else None,
        "latency_p95_s": round(percentile(secs, 95), 1) if secs else None,
        "evidence_verified": f"{verified}/{given}" if given else "0/0",
        "models": models,
        "passed": not failures,
    }

    print("\n  Persona               valid  overall(s)        mean   std  expected  band")
    for r in rows:
        if "mean" in r:
            print(f"  {r['id']:<20} {r['valid']:>5}  {str(r['overalls']):<16} {r['mean']:>5} {r['std']:>5}  {r['expected']:>8}  {'ok' if r['in_band'] else 'FAIL'}")
        else:
            print(f"  {r['id']:<20} {r['valid']:>5}  no cards")
    print("\n  " + "  ".join(f"{k}={v}" for k, v in summary.items() if k != "models"))
    print(f"  models used: {models}")

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {"timestamp": stamp, "runs_per_persona": args.runs, "summary": summary, "personas": rows, "ordering": ordering, "failures": failures, "raw": results}
    (RESULTS_DIR / f"report-{stamp}.json").write_text(json.dumps(report, indent=2))
    md = [
        f"# Eval report ({stamp})",
        "",
        f"{len(fixtures)} personas x {args.runs} runs. Passed: **{summary['passed']}**",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        *[f"| {k} | {v} |" for k, v in summary.items()],
        "",
        "| Persona | Valid | Overalls | Mean | Std | Expected | In band |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        *[f"| {r['id']} | {r['valid']} | {r.get('overalls', '')} | {r.get('mean', '')} | {r.get('std', '')} | {r.get('expected', '')} | {r.get('in_band', '')} |" for r in rows],
    ]
    if failures:
        md += ["", "## Failures", "", *[f"- {f}" for f in failures]]
    (RESULTS_DIR / "latest.md").write_text("\n".join(md) + "\n")

    if failures:
        print("\n  Failures:")
        for f in failures:
            print(f"    x {f}")
        return 1
    print("\n  All checks passed.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
