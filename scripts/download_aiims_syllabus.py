"""
Download official AIIMS MD/MS syllabus and extract curriculum content.

AIIMS publishes official syllabi at:
  https://www.aiims.edu/aiims/academic/aiims-syllabus/

This script downloads the MD/MS/MDS/MHA syllabus PDF, extracts text, and creates
a knowledge index that can be merged with the disease knowledge graph.

Usage:
    cd backend
    python scripts/download_aiims_syllabus.py

Output:
    disease_books/aiims_syllabus/
      - Syllabus - md ms mds mha.pdf  (raw PDF)
      - syllabus_text.txt             (extracted text)
    disease_books/knowledge_index_aiims_syllabus.json  (structured curriculum)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

AIIMS_SYLLABUS_URL = "https://www.aiims.edu/aiims/academic/aiims-syllabus/Syllabus%20-%20md%20ms%20mds%20mha.pdf"
BOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "disease_books"
SYLLABUS_DIR = BOOKS_DIR / "aiims_syllabus"
OUTPUT_INDEX = BOOKS_DIR / "knowledge_index_aiims_syllabus.json"

# MD specialties from AIIMS syllabus (for section parsing)
MD_SPECIALTIES = [
    "Anaesthesiology", "Anatomy", "Biochemistry", "Biophysics", "Community Medicine",
    "Dermatology and Venereology", "Forensic Medicine and Toxicology", "Laboratory Medicine",
    "Medicine", "Microbiology", "Nuclear Medicine", "Obstetrics & Gynaecology",
    "Ophthalmology", "Pathology", "Pediatrics", "Pharmacology", "Physiology",
    "Physical Medicine & Rehabilitation", "PMR", "Psychiatry", "Radio-Diagnosis",
    "Radiotherapy", "Surgery", "Otorhinolaryngology", "ENT", "Orthopaedics",
]


def download_pdf() -> Path | None:
    """Download AIIMS syllabus PDF. Returns path or None."""
    import urllib.request

    SYLLABUS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SYLLABUS_DIR / "Syllabus - md ms mds mha.pdf"

    try:
        req = urllib.request.Request(
            AIIMS_SYLLABUS_URL,
            headers={"User-Agent": "MedDiagnose/1.0 (medical education; +https://github.com/meddiagnose)"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        out_path.write_bytes(data)
        return out_path
    except Exception as e:
        print(f"Download failed: {e}")
        return None


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF. Tries pypdf, PyPDF2, pdftotext, then pdfminer."""
    # 1. Try pypdf
    try:
        from pypdf import PdfReader
        text_parts = []
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
        return "\n\n".join(text_parts)
    except ImportError:
        pass

    # 2. Try PyPDF2
    try:
        from PyPDF2 import PdfReader
        text_parts = []
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
        return "\n\n".join(text_parts)
    except ImportError:
        pass

    # 3. Try pdftotext (poppler-utils)
    try:
        import subprocess
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    print("Install pypdf for PDF extraction: pip install pypdf")
    return ""


def parse_syllabus_sections(full_text: str) -> dict[str, str]:
    """Parse syllabus into specialty -> content sections."""
    index = {}
    # Use specialty names as section headers (they appear in the syllabus TOC)
    lines = full_text.split("\n")
    current_section = "AIIMS MD/MS Syllabus"
    current_content = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Check if this line starts a new MD/MS specialty section
        for spec in MD_SPECIALTIES:
            # Match "9. Medicine" or "Medicine — M D" style headers
            if re.match(rf"^\d+\.\s*{re.escape(spec)}\s", line_stripped, re.I):
                if current_content:
                    index[current_section] = "\n".join(current_content)[:8000]
                current_section = f"AIIMS MD {spec}"
                current_content = [line_stripped]
                break
            if re.match(rf"^{re.escape(spec)}\s*[—\-]", line_stripped, re.I):
                if current_content:
                    index[current_section] = "\n".join(current_content)[:8000]
                current_section = f"AIIMS MD {spec}"
                current_content = [line_stripped]
                break
        else:
            current_content.append(line_stripped)

    if current_content:
        index[current_section] = "\n".join(current_content)[:8000]

    return index


def main():
    SYLLABUS_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = SYLLABUS_DIR / "Syllabus - md ms mds mha.pdf"
    if not pdf_path.exists():
        print("Downloading AIIMS official MD/MS syllabus...")
        pdf_path = download_pdf()
        if not pdf_path:
            sys.exit(1)
    else:
        print(f"Using existing: {pdf_path}")

    print(f"Saved: {pdf_path}")

    print("Extracting text...")
    text = extract_text_from_pdf(pdf_path)
    if not text:
        sys.exit(1)

    # Save raw text
    text_path = SYLLABUS_DIR / "syllabus_text.txt"
    text_path.write_text(text, encoding="utf-8")
    print(f"Saved: {text_path} ({len(text)} chars)")

    # Parse into sections and build index
    print("Parsing syllabus sections...")
    sections = parse_syllabus_sections(text)

    # Also add full syllabus as single entry for RAG retrieval
    knowledge_index = {
        "AIIMS MD/MS Syllabus (Full)": f"[Official AIIMS Curriculum]\n\n{text[:15000]}",
    }
    for section, content in sections.items():
        if content and len(content) > 100:
            knowledge_index[section] = f"[Official AIIMS Curriculum]\n\n{content}"

    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_INDEX, "w") as f:
        json.dump(knowledge_index, f, indent=2)

    print(f"\nDone. Knowledge index: {OUTPUT_INDEX}")
    print(f"  Entries: {len(knowledge_index)}")


if __name__ == "__main__":
    main()
