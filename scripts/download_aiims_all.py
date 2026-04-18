#!/usr/bin/env python3
"""
Download AIIMS/StatPearls study material for ALL diseases (MBBS/MD level).

Fetches from NCBI Bookshelf. Run from your terminal — requires internet.

Usage:
    cd backend
    python scripts/download_aiims_all.py

    # Limit to first N diseases (faster for testing):
    python scripts/download_aiims_all.py -n 100

    # Then rebuild the knowledge graph:
    python scripts/build_knowledge_graph.py --merge-aiims
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
ID2LABEL = BACKEND / "tests" / "id2label.json"


def main():
    with open(ID2LABEL) as f:
        n_total = len(set(json.load(f).values()))

    n = n_total
    if "-n" in sys.argv:
        idx = sys.argv.index("-n")
        if idx + 1 < len(sys.argv):
            n = int(sys.argv[idx + 1])

    print(f"Downloading AIIMS/StatPearls for {n} diseases...")
    print("(Requires internet. Run from terminal if using Cursor.)\n")

    result = subprocess.run(
        [
            sys.executable,
            str(BACKEND / "scripts" / "download_disease_books.py"),
            "--source", "aiims",
            "-n", str(n),
            "-w", "8",
        ],
        cwd=str(BACKEND),
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
