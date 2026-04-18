# Real Patient Lab Data (MIMIC-IV Demo)

**Source:** [MIMIC-IV Clinical Database Demo v2.2](https://physionet.org/content/mimic-iv-demo/2.2/)  
**License:** Open Data Commons Open Database License v1.0  
**Records:** 150 admission-level lab reports from 100 de-identified ICU patients (Beth Israel Deaconess Medical Center)

## Contents

- `hosp/*.csv.gz` – Raw MIMIC data (labevents, patients, diagnoses)
- `reports/*.txt` – Lab reports converted to text format
- `manifest.json` – Patient metadata for the diagnosis API

## Regenerating Reports

```bash
cd backend
python scripts/convert_mimic_to_reports.py
```

## Record Count

150 admission-level reports (one per hospitalization). MIMIC-IV Demo has 337 total admissions; we use the first 150.
