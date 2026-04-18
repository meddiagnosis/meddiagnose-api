"""
MedDiagnose Accuracy Test
=========================
Downloads a public symptom-disease dataset and runs each case through the
MedDiagnose mock diagnosis engine, then produces a detailed accuracy report.

Usage:
    cd backend
    python -m tests.accuracy_test
"""

from __future__ import annotations

import csv
import io
import json
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.mock_diagnosis import diagnose, DISEASE_PROFILES

DATASET_URL = (
    "https://raw.githubusercontent.com/maharshsuryawala/"
    "predict-disease-from-symptoms/master/final_disease_symptom_data.csv"
)

MAPPING_PATH = Path(__file__).parent / "disease_name_mapping.json"

MEDDIAGNOSE_NAMES = {p.name for p in DISEASE_PROFILES}


def load_mapping() -> dict[str, str | None]:
    with open(MAPPING_PATH) as f:
        raw = json.load(f)
    raw.pop("_comment", None)
    return raw


def download_dataset() -> list[dict]:
    print("Downloading symptom-disease dataset from GitHub...")
    req = urllib.request.Request(DATASET_URL, headers={"User-Agent": "MedDiagnose-Test/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    print(f"  Downloaded {len(rows)} records.\n")
    return rows


def extract_symptoms(row: dict) -> list[str]:
    """Pull symptom names where the binary value is '1'."""
    import re
    skip = {"", "diseases"}
    symptoms = []
    for col, val in row.items():
        col_clean = re.sub(r"\s+", " ", col.strip())
        if col_clean in skip:
            continue
        try:
            if int(val) == 1:
                symptoms.append(col_clean.replace("_", " "))
        except (ValueError, TypeError):
            continue
    return symptoms


def normalise_disease_name(raw: str) -> str:
    """Lowercase, collapse multiple spaces, strip."""
    import re
    return re.sub(r"\s+", " ", raw.strip()).lower()


def run_accuracy_test():
    mapping = load_mapping()
    rows = download_dataset()

    dataset_diseases: set[str] = set()
    mapped_count = 0
    unmapped_diseases: set[str] = set()

    for row in rows:
        disease_raw = row.get("diseases", "").strip()
        dataset_diseases.add(disease_raw)
        norm = normalise_disease_name(disease_raw)
        target = mapping.get(norm) or mapping.get(disease_raw)
        if target:
            mapped_count += 1
        elif target is None and (norm in mapping or disease_raw in mapping):
            pass  # explicitly mapped to null (not covered)
        else:
            unmapped_diseases.add(disease_raw)

    mapped_disease_names = {
        normalise_disease_name(k): v
        for k, v in mapping.items()
        if v is not None
    }

    print("=" * 60)
    print("       MedDiagnose Accuracy Report")
    print("=" * 60)
    print(f"Dataset:           {len(rows)} test cases")
    print(f"Unique diseases:   {len(dataset_diseases)}")
    print(f"Mappable diseases: {len([v for v in mapping.values() if v is not None and v != '_comment'])}")
    print(f"Not in engine:     {len([v for v in mapping.values() if v is None])}")
    if unmapped_diseases:
        print(f"Unmapped (new):    {len(unmapped_diseases)}")
    print()

    # Run diagnoses
    exact_match = 0
    partial_match = 0
    total_testable = 0
    skipped = 0

    per_disease_correct: dict[str, int] = defaultdict(int)
    per_disease_total: dict[str, int] = defaultdict(int)
    misses: list[dict] = []

    for i, row in enumerate(rows):
        disease_raw = row.get("diseases", "").strip()
        norm = normalise_disease_name(disease_raw)

        expected_meddiagnose = mapped_disease_names.get(norm)
        if not expected_meddiagnose:
            skipped += 1
            continue

        symptoms = extract_symptoms(row)
        if not symptoms:
            skipped += 1
            continue

        total_testable += 1
        per_disease_total[expected_meddiagnose] += 1

        symptom_text = ", ".join(symptoms)
        result = diagnose(symptom_text)
        predicted = result.get("diagnosis", "")

        is_exact = predicted == expected_meddiagnose
        is_partial = (
            not is_exact
            and _disease_family(predicted) == _disease_family(expected_meddiagnose)
        )

        if is_exact:
            exact_match += 1
            per_disease_correct[expected_meddiagnose] += 1
        elif is_partial:
            partial_match += 1
            per_disease_correct[expected_meddiagnose] += 1
        else:
            misses.append({
                "expected": expected_meddiagnose,
                "predicted": predicted,
                "symptoms_sample": symptom_text[:120],
                "confidence": result.get("confidence", 0),
            })

    # Results
    exact_pct = (exact_match / total_testable * 100) if total_testable else 0
    partial_pct = ((exact_match + partial_match) / total_testable * 100) if total_testable else 0

    print("-" * 60)
    print(f"  Testable cases:    {total_testable}")
    print(f"  Skipped:           {skipped} (disease not in engine)")
    print(f"  Exact match:       {exact_match}/{total_testable} ({exact_pct:.1f}%)")
    print(f"  Partial match:     {exact_match + partial_match}/{total_testable} ({partial_pct:.1f}%)")
    print("-" * 60)
    print()

    # Per-disease breakdown
    print("Per-Disease Breakdown:")
    print(f"  {'Disease':<50} {'Correct':>8} {'Total':>6} {'Acc':>7}")
    print(f"  {'-'*50} {'-'*8} {'-'*6} {'-'*7}")

    for disease in sorted(per_disease_total.keys()):
        correct = per_disease_correct.get(disease, 0)
        total = per_disease_total[disease]
        acc = correct / total * 100 if total else 0
        marker = "✓" if acc >= 50 else "✗"
        print(f"  {marker} {disease:<48} {correct:>6} {total:>6} {acc:>6.1f}%")
    print()

    # Misses
    if misses:
        print(f"Misses ({len(misses)} cases):")
        shown = misses[:20]
        for m in shown:
            print(f"  Expected: {m['expected']}")
            print(f"  Got:      {m['predicted']} (conf: {m['confidence']})")
            print(f"  Symptoms: {m['symptoms_sample']}...")
            print()
        if len(misses) > 20:
            print(f"  ... and {len(misses) - 20} more misses.")
        print()

    # Not covered
    null_diseases = [k for k, v in mapping.items() if v is None and k != "_comment"]
    if null_diseases:
        print(f"Not Covered in MedDiagnose ({len(null_diseases)} diseases):")
        for d in sorted(null_diseases):
            print(f"  - {d}")
        print()

    if unmapped_diseases:
        print(f"New/Unmapped Diseases in Dataset ({len(unmapped_diseases)}):")
        for d in sorted(unmapped_diseases):
            print(f"  ? {d}")
        print()

    print("=" * 60)
    print(f"  OVERALL ACCURACY:  {exact_pct:.1f}%  (exact match)")
    print(f"  WITH PARTIAL:      {partial_pct:.1f}%")
    print("=" * 60)


def _disease_family(name: str) -> str:
    """Extract a rough 'family' for partial matching."""
    name_lower = name.lower()
    families = [
        ("respiratory", ["respiratory", "bronchitis", "pneumonia", "cold", "viral fever", "copd"]),
        ("diabetes", ["diabetes", "blood sugar", "hba1c"]),
        ("cardiac", ["heart", "hypertension", "blood pressure", "cardiac", "coronary"]),
        ("depression", ["depression", "depressive"]),
        ("anxiety", ["anxiety", "stress"]),
        ("arthritis", ["arthritis", "joint", "gout"]),
        ("kidney", ["kidney", "renal", "creatinine"]),
        ("liver", ["hepatitis", "liver", "cirrhosis"]),
        ("skin", ["skin", "dermatitis", "psoriasis", "eczema"]),
        ("thyroid", ["thyroid", "hypothyroid", "tsh"]),
        ("anemia", ["anemia", "iron", "hemoglobin"]),
        ("infection", ["infection", "bacterial"]),
        ("gi", ["gastritis", "gastro", "reflux", "gerd", "ulcer", "ibs"]),
        ("headache", ["headache", "migraine"]),
        ("back", ["back pain", "sciatica", "lumbar"]),
        ("eye", ["eye", "conjunctivitis", "dry eye"]),
        ("ear", ["ear", "otitis"]),
    ]
    for family, keywords in families:
        for kw in keywords:
            if kw in name_lower:
                return family
    return name_lower


if __name__ == "__main__":
    run_accuracy_test()
