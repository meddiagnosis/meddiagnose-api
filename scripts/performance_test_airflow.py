#!/usr/bin/env python3
"""
Performance test for Airflow batch diagnosis pipeline.

Uploads one or more batches, triggers the DAG, and measures throughput.
Requires: backend running, Airflow running, auth token.

Usage:
    cd backend
    python scripts/performance_test_airflow.py [--batches N] [--patients-per-batch M] [--api-url URL]

Example:
    python scripts/performance_test_airflow.py --batches 2 --patients-per-batch 5
"""

import argparse
import csv
import io
import json
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SAMPLE_SYMPTOMS = [
    "fever, sore throat, swollen lymph nodes",
    "burning sensation in chest after meals, acid taste in mouth",
    "dry itchy skin on arms and legs, worse in winter",
    "headache, nausea, sensitivity to light",
    "cough, shortness of breath, wheezing",
]


def create_test_csv(num_patients: int) -> bytes:
    """Create a CSV with test patient data."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["first_name", "last_name", "symptoms", "clinical_notes"])
    for i in range(num_patients):
        symptoms = SAMPLE_SYMPTOMS[i % len(SAMPLE_SYMPTOMS)]
        w.writerow([f"Test{i}", f"Patient{i}", symptoms, f"Clinical notes for patient {i}"])
    return out.getvalue().encode("utf-8")


def login(api_url: str, email: str = "perftest@example.com", password: str = "perftest123") -> str | None:
    """Login and return access token. Registers user if not exists."""
    try:
        import httpx
        # Try login first
        r = httpx.post(
            f"{api_url}/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=10.0,
        )
        if r.status_code == 200:
            return r.json().get("access_token")
        # Try register
        r2 = httpx.post(
            f"{api_url}/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "Perf Test User", "role": "doctor"},
            timeout=10.0,
        )
        if r2.status_code in (200, 201):
            return r2.json().get("access_token")
        # Retry login after register (user may have existed)
        r3 = httpx.post(
            f"{api_url}/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=10.0,
        )
        if r3.status_code == 200:
            return r3.json().get("access_token")
        return None
    except Exception:
        return None


def upload_batch(api_url: str, token: str, csv_bytes: bytes, batch_name: str) -> dict | None:
    """Upload batch and return batch response."""
    try:
        import httpx
        r = httpx.post(
            f"{api_url}/api/v1/batches/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test_batch.csv", csv_bytes, "text/csv")},
            params={"batch_name": batch_name},
            timeout=60.0,
        )
        if r.status_code not in (200, 201):
            print(f"  Upload response: {r.status_code} {r.text[:200]}")
            return None
        return r.json()
    except Exception:
        return None


def get_batch_status(api_url: str, token: str, batch_id: int) -> dict | None:
    """Get batch status."""
    try:
        import httpx
        r = httpx.get(
            f"{api_url}/api/v1/batches/{batch_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def run_test(
    api_url: str,
    num_batches: int,
    patients_per_batch: int,
    poll_interval: float = 5.0,
    timeout_sec: float = 600.0,
) -> dict:
    """Run performance test and return metrics."""
    token = login(api_url)
    if not token:
        return {"error": "Login failed. Ensure backend is running and user exists."}

    batch_ids = []
    upload_start = time.perf_counter()

    for b in range(num_batches):
        csv_bytes = create_test_csv(patients_per_batch)
        batch = upload_batch(api_url, token, csv_bytes, f"perf_test_batch_{b+1}")
        if not batch:
            return {"error": f"Upload failed for batch {b+1}"}
        batch_ids.append(batch["id"])
        print(f"  Uploaded batch {batch['id']}: {batch['total_patients']} patients, status={batch['status']}")

    upload_elapsed = time.perf_counter() - upload_start
    total_patients = num_batches * patients_per_batch
    print(f"  Upload complete: {total_patients} patients in {upload_elapsed:.1f}s")

    # Poll until all batches complete
    poll_start = time.perf_counter()
    completed = set()
    while len(completed) < num_batches and (time.perf_counter() - poll_start) < timeout_sec:
        time.sleep(poll_interval)
        for bid in batch_ids:
            if bid in completed:
                continue
            status = get_batch_status(api_url, token, bid)
            if status:
                s = status.get("status", "")
                p = status.get("processed_count", 0)
                f = status.get("failed_count", 0)
                if s in ("completed", "partially_completed", "failed"):
                    completed.add(bid)
                    print(f"  Batch {bid} done: status={s}, processed={p}, failed={f}")
        if len(completed) < num_batches:
            print(f"  Waiting... {len(completed)}/{num_batches} batches complete")

    total_elapsed = time.perf_counter() - upload_start
    processing_elapsed = time.perf_counter() - poll_start

    return {
        "num_batches": num_batches,
        "patients_per_batch": patients_per_batch,
        "total_patients": total_patients,
        "upload_time_sec": round(upload_elapsed, 2),
        "processing_time_sec": round(processing_elapsed, 2),
        "total_time_sec": round(total_elapsed, 2),
        "batches_completed": len(completed),
        "throughput_patients_per_min": round(total_patients / (total_elapsed / 60), 2) if total_elapsed > 0 else 0,
    }


def main():
    p = argparse.ArgumentParser(description="Airflow batch performance test")
    p.add_argument("--batches", type=int, default=2, help="Number of batches to upload")
    p.add_argument("--patients-per-batch", type=int, default=5, help="Patients per batch")
    p.add_argument("--api-url", default="http://localhost:8001", help="Backend API URL")
    p.add_argument("--poll-interval", type=float, default=5.0, help="Status poll interval (sec)")
    args = p.parse_args()

    print("Airflow batch performance test")
    print(f"  API: {args.api_url}")
    print(f"  Batches: {args.batches}, Patients/batch: {args.patients_per_batch}")
    print()

    result = run_test(
        args.api_url,
        args.batches,
        args.patients_per_batch,
        args.poll_interval,
    )

    if "error" in result:
        print(f"ERROR: {result['error']}")
        sys.exit(1)

    print()
    print("Results:")
    print(f"  Total patients:     {result['total_patients']}")
    print(f"  Batches completed:  {result['batches_completed']}/{result['num_batches']}")
    print(f"  Upload time:        {result['upload_time_sec']}s")
    print(f"  Processing time:    {result['processing_time_sec']}s")
    print(f"  Total time:        {result['total_time_sec']}s")
    print(f"  Throughput:         {result['throughput_patients_per_min']} patients/min")
    print()

    # Save JSON
    out_path = Path(__file__).parent.parent / "performance_results.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    main()
