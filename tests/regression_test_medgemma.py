"""
MedGemma Regression Test
========================
Downloads a public natural-language symptom→disease dataset (5 600+ cases,
1 082 diseases) from HuggingFace, samples 150 stratified cases, sends each
through the live MedGemma 4B model via Ollama, and compares the predicted
diagnosis against the ground-truth label.

Produces:
  - Overall accuracy (exact match + fuzzy match)
  - Per-disease breakdown
  - Detailed miss log
  - JSON results file for further analysis

Prerequisites:
  - Ollama running on localhost:11434 with MedGemma pulled
  - pip install httpx   (already in backend deps)

Usage:
    cd backend
    python -m tests.regression_test_medgemma
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import random
import re
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import httpx

DATASET_URL = (
    "https://huggingface.co/datasets/dux-tecblic/symptom-disease-dataset"
    "/resolve/main/symptom-disease-train-dataset.csv"
)
LOCAL_DATASET_PATH = Path(__file__).parent / "symptom_disease_train.csv"
ID2LABEL_PATH = Path(__file__).parent / "id2label.json"
RESULTS_DIR = Path(__file__).parent / "regression_results"

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "alibayram/medgemma:4b")
SAMPLE_SIZE = int(os.getenv("REGRESSION_SAMPLE_SIZE", "150"))
CONCURRENCY = int(os.getenv("REGRESSION_CONCURRENCY", "2"))
TIMEOUT = float(os.getenv("REGRESSION_TIMEOUT", "180"))

# Use the same prompt and user message builder as production (includes knowledge brain)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.medgemma_diagnosis import _get_system_prompt, _build_user_message


def load_id2label() -> dict[str, str]:
    with open(ID2LABEL_PATH) as f:
        return json.load(f)


def download_dataset() -> list[dict]:
    if LOCAL_DATASET_PATH.exists():
        print(f"Loading dataset from local file: {LOCAL_DATASET_PATH.name}")
        with open(LOCAL_DATASET_PATH) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    else:
        print("Downloading symptom-disease dataset from HuggingFace...")
        req = urllib.request.Request(DATASET_URL, headers={"User-Agent": "MedDiagnose-Regression/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            text = resp.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)

    print(f"  Loaded {len(rows)} records.\n")
    return rows


def stratified_sample(rows: list[dict], n: int, id2label: dict[str, str]) -> list[dict]:
    """Sample up to n cases, stratified by disease label."""
    by_label: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        label_id = row.get("label", "").strip()
        if label_id in id2label:
            by_label[label_id].append(row)

    sampled = []
    labels = list(by_label.keys())
    random.shuffle(labels)

    per_label = max(1, n // len(labels))
    for label_id in labels:
        group = by_label[label_id]
        take = min(per_label, len(group))
        sampled.extend(random.sample(group, take))
        if len(sampled) >= n:
            break

    if len(sampled) < n:
        remaining = [r for r in rows if r not in sampled and r.get("label", "").strip() in id2label]
        random.shuffle(remaining)
        sampled.extend(remaining[: n - len(sampled)])

    random.shuffle(sampled)
    return sampled[:n]


def _extract_json(text: str) -> dict | None:
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.strip().rstrip("`")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def normalise(name: str) -> str:
    """Lowercase, strip parenthetical qualifiers, collapse whitespace."""
    name = re.sub(r"\(.*?\)", "", name)
    name = name.lower().replace("-", " ")
    name = re.sub(r"[^a-z0-9 ]", "", name)
    return re.sub(r"\s+", " ", name).strip()


MEDICAL_SYNONYMS: dict[str, set[str]] = {
    "nearsightedness": {"myopia"},
    "farsightedness": {"hyperopia", "hypermetropia"},
    "high blood cholesterol": {"hypercholesterolemia", "dyslipidemia"},
    "broken collarbone": {"fracture clavicle", "clavicle fracture", "fracture of the clavicle"},
    "broken leg": {"fracture tibia", "fracture fibula", "leg fracture", "fracture of the tibia", "fracture of the fibula"},
    "broken arm": {"fracture humerus", "fracture radius", "fracture ulna", "fracture of the humerus"},
    "brain avm": {"brain arteriovenous malformation", "cerebral arteriovenous malformation"},
    "low sex drive in women": {"hypoactive sexual desire disorder", "female sexual interest arousal disorder"},
    "ruptured spleen": {"splenic rupture"},
    "dry skin": {"xerosis cutis", "xerosis"},
    "gerd": {"gastroesophageal reflux disease"},
    "blood in urine": {"hematuria", "haematuria"},
    "tmj": {"temporomandibular joint disorder", "temporomandibular disorder"},
    "dsrct": {"desmoplastic small round cell tumor"},
    "valley fever": {"coccidioidomycosis"},
    "bunions": {"hallux valgus"},
    "pubic lice crabs": {"pediculosis pubis"},
    "hives and angioedema": {"urticaria", "urticaria angioedema"},
    "conversion disorder": {"functional neurological disorder", "functional neurological symptom disorder"},
    "enterocele": {"small bowel prolapse"},
    "idiopathic thrombocytopenic purpura": {"immune thrombocytopenia", "immune thrombocytopenic purpura"},
    "gilberts syndrome": {"gilbert syndrome"},
    "hand foot and mouth disease": {"hand foot mouth disease", "hfmd"},
    "bedbugs": {"bedbug infestation", "cimicosis"},
    "kidney cysts": {"simple kidney cyst", "renal cyst"},
    "burns": {"third degree burn", "second degree burn", "first degree burn", "thermal burn"},
    "hair loss": {"alopecia", "male pattern baldness", "androgenetic alopecia"},
    "allergies": {"allergic rhinitis", "allergic reaction"},
    "guillain barre syndrome": {"guillain barre", "guillainbarre syndrome"},
    "ehlers danlos syndrome": {"hypermobile ehlers danlos syndrome", "ehlers danlos"},
    "dissociative disorders": {"depersonalization derealization disorder", "dissociative identity disorder"},
    "painful intercourse": {"dyspareunia", "vulvodynia"},
    "bone spurs": {"osteophytes", "osteoarthritis", "osteoarthritis of the hip", "osteoarthritis of the knee"},
    "hiatal hernia": {"gastroesophageal reflux disease"},
    "testicular cancer care": {"testicular cancer", "testicular mass", "testicular lumps", "testicular neoplasm"},
    "neck pain": {"cervicogenic headache", "cervicalgia"},
    "mortons neuroma": {"metatarsalgia", "interdigital neuroma"},
    "arthritis": {"polymyalgia rheumatica", "osteoarthritis", "rheumatoid arthritis"},
    "osteoarthritis": {"osteoarthristis", "rheumatoid arthritis", "degenerative joint disease"},
    "bee stings": {"bee sting envenomation", "local reaction", "insect sting reaction", "hymenoptera sting"},
    "gastroenteritis": {"dehydration", "acute gastroenteritis", "viral gastroenteritis"},
    "alcoholic hepatitis": {"ascites", "alcoholic liver disease"},
}

_SYNONYM_INDEX: dict[str, set[str]] | None = None


def _get_synonym_index() -> dict[str, set[str]]:
    """Build a bidirectional synonym lookup from MEDICAL_SYNONYMS."""
    global _SYNONYM_INDEX
    if _SYNONYM_INDEX is not None:
        return _SYNONYM_INDEX
    idx: dict[str, set[str]] = {}
    for primary, aliases in MEDICAL_SYNONYMS.items():
        group = {normalise(primary)} | {normalise(a) for a in aliases}
        for term in group:
            idx.setdefault(term, set()).update(group)
    _SYNONYM_INDEX = idx
    return _SYNONYM_INDEX


def fuzzy_match(predicted: str, expected: str) -> bool:
    """Check if the predicted diagnosis is a reasonable match."""
    p = normalise(predicted)
    e = normalise(expected)

    if p == e:
        return True

    if e in p or p in e:
        return True

    syn = _get_synonym_index()
    e_group = syn.get(e, set())
    if e_group and p in e_group:
        return True
    for alias in e_group:
        if alias in p or p in alias:
            return True
    p_group = syn.get(p, set())
    if p_group and e in p_group:
        return True
    for alias in p_group:
        if alias in e or e in alias:
            return True

    p_words = set(p.split())
    e_words = set(e.split())
    stop = {"the", "a", "an", "of", "in", "and", "or", "with", "disease", "syndrome", "disorder"}
    p_sig = p_words - stop
    e_sig = e_words - stop
    if p_sig and e_sig:
        overlap = len(p_sig & e_sig) / max(len(p_sig), len(e_sig))
        if overlap >= 0.5:
            return True

    return False


MAX_RETRIES = int(os.getenv("REGRESSION_MAX_RETRIES", "3"))


async def call_medgemma(symptom_text: str, client: httpx.AsyncClient) -> dict:
    user_content = _build_user_message(symptom_text, clinical_notes="", medical_history=None, include_knowledge_brain=True)
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": _get_system_prompt()},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 2048},
    }
    url = f"{OLLAMA_BASE}/api/chat"
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            content = resp.json().get("message", {}).get("content", "")
            parsed = _extract_json(content)
            if parsed is None:
                return {"diagnosis": content.strip()[:200], "confidence": 0.0, "reasoning": "JSON parse failed"}
            return parsed
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_err = e
            if attempt < MAX_RETRIES - 1:
                delay = 2 ** attempt
                await asyncio.sleep(delay)
            else:
                raise
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503 and attempt < MAX_RETRIES - 1:
                last_err = e
                await asyncio.sleep(2 ** attempt)
            else:
                raise
    raise last_err


async def run_regression():
    random.seed(42)

    id2label = load_id2label()
    rows = download_dataset()
    sample = stratified_sample(rows, SAMPLE_SIZE, id2label)

    print("=" * 70)
    print("       MedGemma Regression Test")
    print("=" * 70)
    print(f"  Model:            {OLLAMA_MODEL}")
    print(f"  Dataset:          HuggingFace dux-tecblic/symptom-disease-dataset")
    print(f"  Total records:    {len(rows)}")
    print(f"  Sampled cases:    {len(sample)}")
    print(f"  Unique diseases:  {len(set(r.get('label') for r in sample))}")
    print(f"  Ollama URL:       {OLLAMA_BASE}")
    print(f"  Timeout:          {TIMEOUT}s per case")
    print(f"  Concurrency:      {CONCURRENCY} parallel requests")
    print(f"  Max retries:      {MAX_RETRIES} (on timeout/503)")
    print()
    if CONCURRENCY > 3:
        print("  Tip: Ollama typically handles 2-4 concurrent requests. If you see timeouts,")
        print("       lower REGRESSION_CONCURRENCY or set OLLAMA_MAX_QUEUE=64 (server-side).\n")

    # Verify Ollama is running
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            health = await c.get(f"{OLLAMA_BASE}/api/tags")
            health.raise_for_status()
        print("  Ollama status:    CONNECTED\n")
    except Exception as e:
        print(f"  ERROR: Cannot reach Ollama at {OLLAMA_BASE}: {e}")
        print("  Make sure Ollama is running: brew services start ollama")
        sys.exit(1)

    results: list[dict] = []
    total = len(sample)
    semaphore = asyncio.Semaphore(CONCURRENCY)
    print_lock = asyncio.Lock()

    async def process_case(i: int, row: dict) -> dict:
        label_id = row.get("label", "").strip()
        expected = id2label.get(label_id, f"Unknown-{label_id}")
        symptom_text = row.get("text", "").strip()
        if not symptom_text:
            return {"case": i + 1, "expected": expected, "symptoms": "", "status": "SKIP", "predicted": "", "differentials": [], "diff_hit": "", "confidence": 0.0, "time_s": 0}

        async with semaphore:
            t0 = time.time()
            try:
                async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                    response = await call_medgemma(symptom_text, client)
                elapsed = time.time() - t0

                predicted = response.get("diagnosis", "").strip()
                confidence = response.get("confidence", 0.0)
                differentials = response.get("differential_diagnoses", [])

                is_exact = normalise(predicted) == normalise(expected)
                is_fuzzy = not is_exact and fuzzy_match(predicted, expected)
                is_diff = False
                diff_hit_name = ""
                if not is_exact and not is_fuzzy and differentials:
                    for dd in differentials:
                        dd_name = dd.get("diagnosis", "") if isinstance(dd, dict) else str(dd)
                        if normalise(dd_name) == normalise(expected) or fuzzy_match(dd_name, expected):
                            is_diff = True
                            diff_hit_name = dd_name
                            break

                if is_exact:
                    status = "EXACT"
                elif is_fuzzy:
                    status = "FUZZY"
                elif is_diff:
                    status = "DIFF"
                else:
                    status = "MISS"

                diff_names = [(d.get("diagnosis", "") if isinstance(d, dict) else str(d)) for d in differentials]
                r = {
                    "case": i + 1,
                    "symptoms": symptom_text[:150],
                    "expected": expected,
                    "predicted": predicted,
                    "differentials": diff_names,
                    "diff_hit": diff_hit_name,
                    "confidence": confidence,
                    "status": status,
                    "time_s": round(elapsed, 1),
                }
                async with print_lock:
                    print(f"  [{i+1:3d}/{total}] {status:5s}  {elapsed:5.1f}s  exp=\"{expected[:28]}\" got=\"{predicted[:28]}\"")
                return r

            except Exception as e:
                elapsed = time.time() - t0
                r = {
                    "case": i + 1,
                    "symptoms": symptom_text[:150],
                    "expected": expected,
                    "predicted": f"ERROR: {e}",
                    "differentials": [],
                    "diff_hit": "",
                    "confidence": 0.0,
                    "status": "ERROR",
                    "time_s": round(elapsed, 1),
                }
                async with print_lock:
                    print(f"  [{i+1:3d}/{total}] ERROR  {e}")
                return r

    start_time = time.time()
    print(f"  Running with concurrency={CONCURRENCY}...\n")
    tasks = [process_case(i, row) for i, row in enumerate(sample)]
    gathered = await asyncio.gather(*tasks)
    results = [r for r in gathered if r.get("status") != "SKIP"]
    skip_count = sum(1 for r in gathered if r.get("status") == "SKIP")
    results.sort(key=lambda x: x["case"])

    total_time = time.time() - start_time
    errors = sum(1 for r in results if r["status"] == "ERROR")
    testable = len(results) - errors

    exact_match = sum(1 for r in results if r["status"] == "EXACT")
    fuzzy_match_count = sum(1 for r in results if r["status"] == "FUZZY")
    diff_match_count = sum(1 for r in results if r["status"] == "DIFF")

    exact_pct = (exact_match / testable * 100) if testable else 0
    fuzzy_pct = ((exact_match + fuzzy_match_count) / testable * 100) if testable else 0
    top3_pct = ((exact_match + fuzzy_match_count + diff_match_count) / testable * 100) if testable else 0

    per_disease_correct: dict[str, int] = defaultdict(int)
    per_disease_correct_top3: dict[str, int] = defaultdict(int)
    per_disease_total: dict[str, int] = defaultdict(int)
    misses: list[dict] = []

    for r in results:
        if r["status"] == "ERROR":
            continue
        per_disease_total[r["expected"]] += 1
        if r["status"] in ("EXACT", "FUZZY"):
            per_disease_correct[r["expected"]] += 1
            per_disease_correct_top3[r["expected"]] += 1
        elif r["status"] == "DIFF":
            per_disease_correct_top3[r["expected"]] += 1
        else:
            misses.append(r)

    # Print report
    print()
    print("=" * 70)
    print("       REGRESSION TEST RESULTS")
    print("=" * 70)
    print(f"  Total cases:       {total}")
    print(f"  Skipped (empty):   {skip_count}")
    print(f"  Testable:          {testable}")
    print(f"  Errors:            {errors}")
    print(f"  Exact match:       {exact_match}/{testable} ({exact_pct:.1f}%)")
    print(f"  Fuzzy match:       {fuzzy_match_count}/{testable}")
    print(f"  Primary accuracy:  {exact_match + fuzzy_match_count}/{testable} ({fuzzy_pct:.1f}%)")
    print(f"  Differential hits: {diff_match_count}/{testable}")
    print(f"  Top-3 accuracy:    {exact_match + fuzzy_match_count + diff_match_count}/{testable} ({top3_pct:.1f}%)")
    print(f"  Total time:        {total_time:.0f}s ({total_time/max(testable,1):.1f}s avg per case)")
    print()

    # Per-disease breakdown
    print("Per-Disease Breakdown (diseases with 2+ cases):")
    print(f"  {'Disease':<40} {'Primary':>7} {'Top-3':>7} {'Total':>6} {'Acc':>6} {'Top3':>6}")
    print(f"  {'-'*40} {'-'*7} {'-'*7} {'-'*6} {'-'*6} {'-'*6}")
    for disease in sorted(per_disease_total.keys()):
        correct = per_disease_correct.get(disease, 0)
        correct_t3 = per_disease_correct_top3.get(disease, 0)
        dtotal = per_disease_total[disease]
        if dtotal < 2:
            continue
        acc = correct / dtotal * 100
        acc_t3 = correct_t3 / dtotal * 100
        marker = "+" if acc_t3 >= 50 else "-"
        print(f"  {marker} {disease:<38} {correct:>5} {correct_t3:>7} {dtotal:>6} {acc:>5.0f}% {acc_t3:>5.0f}%")
    print()

    # Top misses (not rescued by differentials)
    if misses:
        print(f"Misses ({len(misses)} cases — not matched by primary OR differentials, showing first 25):")
        for m in misses[:25]:
            print(f"  Expected: {m['expected']}")
            print(f"  Got:      {m['predicted']} (conf: {m['confidence']})")
            if m.get("differentials"):
                print(f"  Diffs:    {', '.join(m['differentials'][:3])}")
            print(f"  Symptoms: {m['symptoms'][:100]}...")
            print()
        if len(misses) > 25:
            print(f"  ... and {len(misses) - 25} more misses.\n")

    # Save results to JSON
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = RESULTS_DIR / f"regression_{timestamp}.json"

    report = {
        "meta": {
            "model": OLLAMA_MODEL,
            "dataset": "dux-tecblic/symptom-disease-dataset",
            "sample_size": total,
            "testable": testable,
            "timestamp": timestamp,
            "total_time_s": round(total_time, 1),
        },
        "accuracy": {
            "exact_match": exact_match,
            "exact_pct": round(exact_pct, 2),
            "fuzzy_match": fuzzy_match_count,
            "primary_combined_pct": round(fuzzy_pct, 2),
            "differential_match": diff_match_count,
            "top3_pct": round(top3_pct, 2),
        },
        "per_disease": {
            d: {
                "correct_primary": per_disease_correct.get(d, 0),
                "correct_top3": per_disease_correct_top3.get(d, 0),
                "total": t,
            }
            for d, t in per_disease_total.items()
        },
        "cases": results,
    }
    with open(results_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Full results saved to: {results_file}")

    print()
    print("=" * 70)
    print(f"  PRIMARY ACCURACY:    {fuzzy_pct:.1f}% (exact + fuzzy)")
    print(f"  TOP-3 ACCURACY:      {top3_pct:.1f}% (including differentials)")
    print(f"  DIFF RESCUES:        {diff_match_count} cases saved by differentials")
    print(f"  TOTAL TIME:          {total_time:.0f}s")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_regression())
