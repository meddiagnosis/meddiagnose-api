#!/usr/bin/env python3
"""
Comparative analysis of Books Brain vs MedGemma Brain.

Runs both diagnosis engines on the same test cases and produces a report.

Usage:
  python scripts/compare_brains.py              # Full run (10 cases)
  python scripts/compare_brains.py --quick      # Quick run (4 cases)
  python scripts/compare_brains.py --parallel 2 # Run 2 MedGemma calls at a time (GPU)
  python scripts/compare_brains.py --books-only  # Books only (instant)
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Test cases: (symptoms, expected_diagnosis_hint for reference - not used for scoring)
ALL_TEST_CASES = [
    {
        "id": "cardiac_1",
        "symptoms": "chest pain, pressure, shortness of breath, palpitations",
        "notes": "55yo male, smoker",
        "category": "Cardiovascular",
    },
    {
        "id": "neuro_1",
        "symptoms": "vertigo, dizziness, spinning sensation when moving head",
        "notes": "",
        "category": "Neurology/ENT",
    },
    {
        "id": "gi_1",
        "symptoms": "heartburn, acid reflux after meals, regurgitation",
        "notes": "worse when lying down",
        "category": "Gastrointestinal",
    },
    {
        "id": "resp_1",
        "symptoms": "cough, wheezing, shortness of breath, chest tightness",
        "notes": "triggers: exercise, cold air",
        "category": "Respiratory",
    },
    {
        "id": "infectious_1",
        "symptoms": "fever, sore throat, swollen lymph nodes, fatigue",
        "notes": "teenager",
        "category": "Infectious",
    },
    {
        "id": "renal_1",
        "symptoms": "flank pain, fever, painful urination, frequency",
        "notes": "",
        "category": "Renal/Urinary",
    },
    {
        "id": "derm_1",
        "symptoms": "itchy red rash, scaly patches, silvery scales on elbows",
        "notes": "",
        "category": "Dermatology",
    },
    {
        "id": "endo_1",
        "symptoms": "excessive thirst, frequent urination, weight loss, fatigue",
        "notes": "",
        "category": "Endocrine",
    },
    {
        "id": "ortho_1",
        "symptoms": "joint pain, morning stiffness, swelling in hands",
        "notes": "worse after rest",
        "category": "Musculoskeletal",
    },
    {
        "id": "psych_1",
        "symptoms": "low mood, anhedonia, sleep disturbance, fatigue for weeks",
        "notes": "",
        "category": "Psychiatry",
    },
]

# Quick subset for faster runs
QUICK_CASES = ["cardiac_1", "gi_1", "neuro_1", "resp_1"]


def run_books_brain(symptoms: str, clinical_notes: str = "") -> tuple[dict, float]:
    """Run books brain and return (result, latency_seconds)."""
    from app.services.books_diagnosis import diagnose as books_diagnose

    t0 = time.perf_counter()
    result = books_diagnose(symptoms, clinical_notes)
    latency = time.perf_counter() - t0
    return result, latency


async def run_medgemma_brain(symptoms: str, clinical_notes: str = "") -> tuple[dict, float]:
    """Run MedGemma brain and return (result, latency_seconds)."""
    from app.services.medgemma_diagnosis import diagnose as medgemma_diagnose

    t0 = time.perf_counter()
    result = await medgemma_diagnose(symptoms, clinical_notes)
    latency = time.perf_counter() - t0
    return result, latency


def run_mock_brain(symptoms: str, clinical_notes: str = "") -> tuple[dict, float]:
    """Run mock brain (fallback when MedGemma unavailable) and return (result, latency)."""
    from app.services.mock_diagnosis import diagnose as mock_diagnose

    t0 = time.perf_counter()
    result = mock_diagnose(symptoms, clinical_notes)
    latency = time.perf_counter() - t0
    return result, latency


def summarise_result(r: dict) -> dict:
    """Extract key fields for comparison."""
    return {
        "diagnosis": r.get("diagnosis", "N/A"),
        "confidence": r.get("confidence", 0),
        "model_version": r.get("model_version", "unknown"),
        "differentials_count": len(r.get("differential_diagnoses", [])),
        "medications_count": len(r.get("medications", [])),
        "reasoning_len": len(r.get("reasoning", "")),
        "findings_count": len(r.get("findings", [])),
        "severity": r.get("severity", "N/A"),
        "urgency": r.get("urgency", "N/A"),
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Run only 4 test cases")
    parser.add_argument("--books-only", action="store_true", help="Run only books brain (fast)")
    parser.add_argument("--parallel", type=int, default=1, help="Run N MedGemma calls concurrently (default 1)")
    args = parser.parse_args()

    if args.quick:
        TEST_CASES = [tc for tc in ALL_TEST_CASES if tc["id"] in QUICK_CASES]
    else:
        TEST_CASES = ALL_TEST_CASES

    print("=" * 80)
    print("COMPARATIVE ANALYSIS: Books Brain vs MedGemma Brain")
    print("=" * 80)
    mode = []
    if args.quick:
        mode.append("quick")
    if args.parallel > 1:
        mode.append(f"parallel={args.parallel}")
    print(f"Running {len(TEST_CASES)} test cases" + (f" ({', '.join(mode)})" if mode else "") + "\n")

    # Books brain (fast, run all first)
    print("Running Books Brain...")
    books_results = []
    for tc in TEST_CASES:
        r, lat = run_books_brain(tc["symptoms"], tc["notes"])
        books_results.append((tc, r, lat))

    # MedGemma brain (slow, run in batches if parallel)
    all_results = []
    medgemma_available = True
    parallel = max(1, args.parallel) if not args.books_only else 1

    if args.books_only:
        for tc, books_result, books_latency in books_results:
            all_results.append({
                "test": tc,
                "books": {"result": books_result, "latency": books_latency, "summary": summarise_result(books_result)},
                "medgemma": {"result": {"diagnosis": "N/A (skipped)", "confidence": 0, "model_version": "skipped"}, "latency": 0, "summary": {"diagnosis": "N/A (skipped)", "confidence": 0, "model_version": "skipped"}},
            })
    else:
        print("\nRunning MedGemma Brain (GPU)...")
        async def run_one_medgemma(tc, books_result, books_latency):
            try:
                medgemma_result, medgemma_latency = await run_medgemma_brain(tc["symptoms"], tc["notes"])
                return tc, books_result, books_latency, medgemma_result, medgemma_latency, True
            except Exception as e:
                medgemma_result, medgemma_latency = run_mock_brain(tc["symptoms"], tc["notes"])
                return tc, books_result, books_latency, medgemma_result, medgemma_latency, False

        tasks = [run_one_medgemma(tc, br, bl) for tc, br, bl in books_results]
        for i in range(0, len(tasks), parallel):
            batch = tasks[i : i + parallel]
            batch_results = await asyncio.gather(*batch)
            for res in batch_results:
                tc, books_result, books_latency, medgemma_result, medgemma_latency, ok = res
                if not ok:
                    medgemma_available = False
                if medgemma_result.get("model_version", "").startswith("mock"):
                    medgemma_available = False
                all_results.append({
                    "test": tc,
                    "books": {"result": books_result, "latency": books_latency, "summary": summarise_result(books_result)},
                    "medgemma": {"result": medgemma_result, "latency": medgemma_latency, "summary": summarise_result(medgemma_result)},
                })
                status = "[FALLBACK]" if medgemma_result.get("model_version", "").startswith("mock") else ""
                print(f"  {tc['id']:12} | Books: {books_result.get('diagnosis', '')[:30]:30} | MedGemma: {medgemma_result.get('diagnosis', '')[:30]:30} {status} [{medgemma_latency:.1f}s]")

    # Sort by test id to match original order
    id_order = {tc["id"]: i for i, tc in enumerate(TEST_CASES)}
    all_results.sort(key=lambda r: id_order.get(r["test"]["id"], 0))

    # Aggregate stats
    books_latencies = [r["books"]["latency"] for r in all_results]
    medgemma_latencies = [r["medgemma"]["latency"] for r in all_results if r["medgemma"]["latency"] > 0]
    books_diagnoses = [r["books"]["summary"]["diagnosis"] for r in all_results]
    medgemma_diagnoses = [r["medgemma"]["summary"]["diagnosis"] for r in all_results]

    # Agreement (only when both ran)
    if not args.books_only and medgemma_latencies:
        agreement = sum(1 for b, m in zip(books_diagnoses, medgemma_diagnoses) if b == m and m != "N/A (skipped)")
        agreement_pct = 100 * agreement / len(TEST_CASES) if TEST_CASES else 0
    else:
        agreement = 0
        agreement_pct = 0

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    medgemma_avg = sum(medgemma_latencies) / len(medgemma_latencies) if medgemma_latencies else 0
    medgemma_min = min(medgemma_latencies) if medgemma_latencies else 0
    medgemma_max = max(medgemma_latencies) if medgemma_latencies else 0

    print(f"""
| Metric                    | Books Brain           | MedGemma Brain        |
|---------------------------|----------------------|------------------------|
| Avg latency               | {sum(books_latencies)/len(books_latencies):.2f}s              | {medgemma_avg:.2f}s              |
| Min latency               | {min(books_latencies):.2f}s              | {medgemma_min:.2f}s              |
| Max latency               | {max(books_latencies):.2f}s              | {medgemma_max:.2f}s              |
| Primary diagnosis agreement | —                    | {agreement}/{len(TEST_CASES)} ({agreement_pct:.0f}%)          |
| MedGemma available        | —                    | {'Yes' if medgemma_available else 'No (mock fallback)'}  |
""")

    print("\n--- Per-case comparison ---")
    for r in all_results:
        t = r["test"]
        b = r["books"]["summary"]
        m = r["medgemma"]["summary"]
        match = "✓" if b["diagnosis"] == m["diagnosis"] else "✗"
        print(f"  {t['id']:12} | Books: {b['diagnosis'][:35]:35} | MedGemma: {m['diagnosis'][:35]:35} | {match}")

    # Detailed table
    print("\n" + "=" * 80)
    print("DETAILED RESULTS (JSON)")
    print("=" * 80)

    report = {
        "summary": {
            "books_avg_latency_s": sum(books_latencies) / len(books_latencies),
            "medgemma_avg_latency_s": sum(medgemma_latencies) / len(medgemma_latencies) if medgemma_latencies else 0,
            "primary_diagnosis_agreement": agreement,
            "total_tests": len(TEST_CASES),
            "medgemma_available": medgemma_available,
        },
        "cases": [
            {
                "id": r["test"]["id"],
                "category": r["test"]["category"],
                "symptoms": r["test"]["symptoms"],
                "books": r["books"]["summary"] | {"latency_s": r["books"]["latency"]},
                "medgemma": r["medgemma"]["summary"] | {"latency_s": r["medgemma"]["latency"]},
                "agreement": r["books"]["summary"]["diagnosis"] == r["medgemma"]["summary"]["diagnosis"],
            }
            for r in all_results
        ],
    }

    out_path = Path(__file__).resolve().parent.parent.parent / "brain_comparison_report.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to: {out_path}")

    # Qualitative comparison
    print("\n" + "=" * 80)
    print("QUALITATIVE COMPARISON")
    print("=" * 80)
    print("""
Books Brain:
  • Source: Knowledge graph (Wikipedia, AIIMS/StatPearls, AIIMS syllabus)
  • Method: Symptom→disease matching, no LLM
  • Pros: Fast, deterministic, no GPU, explainable (symptom match)
  • Cons: Limited to graph coverage, fixed confidence (0.75), generic treatments

MedGemma Brain:
  • Source: MedGemma 4B via Ollama (pure AI, no books)
  • Method: LLM inference with clinical reasoning
  • Pros: Nuanced reasoning, considers context, richer differentials
  • Cons: Slower, requires GPU/Ollama, non-deterministic, may hallucinate

Recommendation:
  • Use Books Brain for: quick triage, low-resource environments, auditability
  • Use MedGemma Brain for: complex cases, when clinical reasoning matters
  • Consider ensemble: run both and compare when confidence differs
""")


if __name__ == "__main__":
    asyncio.run(main())
