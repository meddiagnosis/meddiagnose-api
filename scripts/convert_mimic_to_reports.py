#!/usr/bin/env python3
"""
Convert MIMIC-IV Demo lab data to report format for MedDiagnose.
Generates 150 real patient admission lab reports from de-identified EHR data.
Source: PhysioNet MIMIC-IV Clinical Database Demo (Open Access)
"""
import csv
import gzip
import json
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "real_patients_mimic"
HOSP_DIR = DATA_DIR / "hosp"
OUTPUT_DIR = DATA_DIR / "reports"
MAX_REPORTS = 150  # One report per admission (337 available)


def load_csv_gz(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading MIMIC-IV Demo data...")
    labitems = {int(r["itemid"]): r for r in load_csv_gz(HOSP_DIR / "d_labitems.csv.gz")}
    patients = {int(r["subject_id"]): r for r in load_csv_gz(HOSP_DIR / "patients.csv.gz")}
    labevents = load_csv_gz(HOSP_DIR / "labevents.csv.gz")
    diagnoses = load_csv_gz(HOSP_DIR / "diagnoses_icd.csv.gz")

    # Build diagnosis lookup by (subject_id, hadm_id)
    dx_by_admission: dict[tuple[int, int], list[str]] = defaultdict(list)
    for r in diagnoses:
        key = (int(r["subject_id"]), int(r["hadm_id"]))
        dx_by_admission[key].append(r["icd_code"])

    # Group lab events by (subject_id, hadm_id) - one report per admission
    labs_by_admission: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for r in labevents:
        sid = int(r["subject_id"])
        hadm = int(r["hadm_id"]) if r.get("hadm_id") else 0
        if hadm == 0:
            continue
        labs_by_admission[(sid, hadm)].append(r)

    # Sort admissions by (subject_id, hadm_id) for deterministic order, take first 150
    admissions = sorted(labs_by_admission.keys())[:MAX_REPORTS]
    manifest_patients = []

    for idx, (subject_id, hadm_id) in enumerate(admissions):
        pt = patients.get(subject_id, {})
        gender = pt.get("gender", "U")
        age = pt.get("anchor_age", "?")

        labs = labs_by_admission[(subject_id, hadm_id)]
        labs.sort(key=lambda x: x.get("charttime", ""))

        lines = [
            f"Laboratory Report - MIMIC-IV Demo (De-identified)",
            f"Patient ID: {subject_id} | Admission: {hadm_id} | Age: {age} | Gender: {gender}",
            f"Source: Beth Israel Deaconess Medical Center (de-identified)",
            "",
            "Laboratory Results",
            "-" * 50,
        ]

        seen_items: set[int] = set()
        for le in labs:
            itemid = int(le["itemid"])
            if itemid not in labitems or itemid in seen_items:
                continue
            seen_items.add(itemid)
            label = labitems[itemid]["label"]
            value = le.get("value", le.get("valuenum", ""))
            unit = le.get("valueuom", "")
            ref_lo = le.get("ref_range_lower", "")
            ref_hi = le.get("ref_range_upper", "")
            flag = le.get("flag", "")

            ref_str = f" (Ref: {ref_lo}-{ref_hi})" if ref_lo or ref_hi else ""
            flag_str = f" [{flag}]" if flag else ""
            lines.append(f"{label}: {value} {unit}{ref_str}{flag_str}".strip())

        dx_codes = dx_by_admission.get((subject_id, hadm_id), [])[:5]
        if dx_codes:
            lines.append("")
            lines.append("Discharge diagnoses (ICD): " + ", ".join(dx_codes))

        report_content = "\n".join(lines)
        report_path = OUTPUT_DIR / f"mimic_adm_{subject_id}_{hadm_id}.txt"
        report_path.write_text(report_content, encoding="utf-8")

        symptoms = f"Patient age {age}, {gender}. Lab results from hospitalization (admission {hadm_id})."
        clinical_notes = f"De-identified EHR data. ICD codes: {', '.join(dx_codes[:3])}" if dx_codes else ""

        manifest_patients.append({
            "user_email": f"mimic_{subject_id}_adm{hadm_id}@demo.meddiagnose",
            "lab_report": f"reports/mimic_adm_{subject_id}_{hadm_id}.txt",
            "symptoms": symptoms,
            "clinical_notes": clinical_notes,
            "expected_diagnosis": "",
            "source": "MIMIC-IV Demo (PhysioNet)",
        })
        if (idx + 1) % 25 == 0 or idx == 0:
            print(f"  Wrote {idx + 1}/{len(admissions)} reports...")

    manifest = {"patients": manifest_patients, "source": "MIMIC-IV Clinical Database Demo v2.2", "license": "ODbL 1.0"}
    manifest_path = DATA_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nWrote {len(manifest_patients)} reports and manifest to {DATA_DIR}")


if __name__ == "__main__":
    main()
