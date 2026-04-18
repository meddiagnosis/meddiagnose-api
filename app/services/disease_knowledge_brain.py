"""
Disease Knowledge Brain — RAG-style retrieval from disease-specific books.

Loads indexed disease summaries (from downloaded PDFs/Wikipedia) and
retrieves relevant context for the MedGemma diagnosis prompt. Improves
accuracy by grounding the model in medical reference content.

When a knowledge graph is available (built by build_knowledge_graph.py),
prefers graph-based retrieval for structured disease–symptom–treatment
context. Falls back to text-based retrieval otherwise.
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

_MAX_SCORE_WORKERS = 8

logger = logging.getLogger("disease_knowledge_brain")

# Path to knowledge index (built by download_disease_books.py)
# backend/app/services -> backend -> project root (meddiagnose)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_PROJECT_ROOT = _BACKEND_ROOT.parent
_KNOWLEDGE_INDEX_PATH = _PROJECT_ROOT / "disease_books" / "knowledge_index.json"
_KNOWLEDGE_GRAPH_PATH = _PROJECT_ROOT / "disease_books" / "knowledge_graph.json"
_AIIMS_INDEX_PATH = _PROJECT_ROOT / "disease_books" / "knowledge_index_aiims.json"
_AIIMS_SYLLABUS_PATH = _PROJECT_ROOT / "disease_books" / "knowledge_index_aiims_syllabus.json"

_CACHE: dict[str, str] | None = None


def _load_index() -> dict[str, str]:
    """Load the disease knowledge index. Cached after first load.
    Merges Wikipedia, AIIMS/StatPearls, and official AIIMS syllabus when available."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    merged: dict[str, str] = {}
    try:
        if _KNOWLEDGE_INDEX_PATH.exists():
            with open(_KNOWLEDGE_INDEX_PATH) as f:
                merged.update(json.load(f))
        if _AIIMS_INDEX_PATH.exists():
            with open(_AIIMS_INDEX_PATH) as f:
                merged.update(json.load(f))
        if _AIIMS_SYLLABUS_PATH.exists():
            with open(_AIIMS_SYLLABUS_PATH) as f:
                merged.update(json.load(f))
        _CACHE = merged
        logger.info("Loaded disease knowledge for %d conditions (incl. AIIMS syllabus)", len(_CACHE))
        return _CACHE
    except Exception as e:
        logger.warning("Failed to load disease knowledge: %s", e)
        return {}


def _normalise_for_match(text: str) -> str:
    """Lowercase, collapse whitespace, remove punctuation for matching."""
    t = text.lower().strip()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    return re.sub(r"\s+", " ", t)


def _score_relevance(symptoms: str, disease_name: str, content: str) -> float:
    """
    Simple relevance score: symptom words appearing in disease content.
    Returns 0.0-1.0.
    """
    sym_norm = _normalise_for_match(symptoms)
    content_norm = _normalise_for_match(content)
    name_norm = _normalise_for_match(disease_name)

    words = set(w for w in sym_norm.split() if len(w) > 2)
    if not words:
        return 0.0

    hits = sum(1 for w in words if w in content_norm or w in name_norm)
    return min(1.0, hits / max(1, len(words)) * 1.5)


def get_relevant_context(
    symptoms: str,
    suspected_diagnoses: list[str] | None = None,
    max_chars: int = 2000,
    top_k: int = 3,
    use_knowledge_graph: bool = True,
) -> str:
    """
    Retrieve relevant disease knowledge for the given symptoms and optional
    suspected diagnoses. Returns a string to inject into the MedGemma prompt.

    When use_knowledge_graph=True (default), uses the graph for structured
    disease–symptom–treatment retrieval. Falls back to text-based retrieval
    if the graph is empty or unavailable.

    Args:
        symptoms: Patient symptom text
        suspected_diagnoses: Optional list of diagnoses to prioritise
        max_chars: Max total characters to return
        top_k: Max number of disease entries to include
        use_knowledge_graph: Prefer graph-based retrieval when available

    Returns:
        Formatted context string, or empty if no relevant content.
    """
    # Prefer knowledge graph when available (includes treatments/cures)
    if use_knowledge_graph and _KNOWLEDGE_GRAPH_PATH.exists():
        try:
            from app.services.disease_knowledge_graph import get_graph_context
            ctx = get_graph_context(
                symptoms,
                suspected_diagnoses=suspected_diagnoses,
                max_chars=max_chars,
                top_k_diseases=top_k,
                include_treatments=True,
            )
            if ctx:
                return ctx
        except Exception as e:
            logger.debug("Knowledge graph retrieval failed, falling back to text: %s", e)

    index = _load_index()
    if not index:
        return ""

    def score_one(name: str, content: str) -> tuple[float, str, str]:
        s = _score_relevance(symptoms, name, content)
        if suspected_diagnoses:
            name_norm = _normalise_for_match(name)
            for sd in suspected_diagnoses:
                sd_norm = _normalise_for_match(sd)
                if sd_norm in name_norm or name_norm in sd_norm:
                    s += 0.5
                    break
        return (s, name, content)

    workers = min(_MAX_SCORE_WORKERS, len(index))
    scored: list[tuple[float, str, str]] = []
    if workers >= 4 and len(index) >= 20:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(score_one, n, c): (n, c) for n, c in index.items()}
            for future in as_completed(futures):
                s, n, c = future.result()
                if s > 0:
                    scored.append((s, n, c))
    else:
        for name, content in index.items():
            s, n, c = score_one(name, content)
            if s > 0:
                scored.append((s, n, c))

    scored.sort(key=lambda x: -x[0])
    selected = scored[:top_k]

    if not selected:
        return ""

    parts = []
    total = 0
    for _score, name, content in selected:
        excerpt = content[:800].strip()
        if len(content) > 800:
            excerpt += "..."
        block = f"Reference — {name}:\n{excerpt}\n"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)

    if not parts:
        return ""

    return (
        "\n\nRelevant medical reference (use to inform your diagnosis and naming):\n"
        + "\n---\n".join(parts)
    )
