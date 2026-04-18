"""
Disease Knowledge Graph — Graph-based retrieval from AIIMS and Wikipedia books.

Builds a knowledge graph from disease texts with entities (diseases, symptoms,
treatments, causes) and relationships. Used for improved diagnosis and cure
retrieval when integrated with MedGemma.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("disease_knowledge_graph")

# backend/app/services -> backend -> project root (meddiagnose)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_PROJECT_ROOT = _BACKEND_ROOT.parent
_KNOWLEDGE_INDEX_PATH = _PROJECT_ROOT / "disease_books" / "knowledge_index.json"
_GRAPH_PATH = _PROJECT_ROOT / "disease_books" / "knowledge_graph.json"
_GRAPH_AIIMS_PATH = _PROJECT_ROOT / "disease_books" / "knowledge_index_aiims.json"

# Entity types in the graph
NODE_DISEASE = "disease"
NODE_SYMPTOM = "symptom"
NODE_TREATMENT = "treatment"
NODE_CAUSE = "cause"
NODE_MEDICATION = "medication"

REL_HAS_SYMPTOM = "has_symptom"
REL_TREATABLE_BY = "treatable_by"
REL_CAUSED_BY = "caused_by"
REL_MENTIONED_IN = "mentioned_in"

_CACHE: dict | None = None
# Pre-built index: adjacency + word lookup. Built once at load.
_INDEX: dict | None = None


def _slug(s: str) -> str:
    """Create a stable ID from text."""
    t = re.sub(r"[^\w\s-]", "", s.lower().strip())
    return re.sub(r"\s+", "_", t)[:80] if t else "unknown"


def _extract_section(text: str, header: str) -> str:
    """Extract content under a Wikipedia-style section header."""
    pattern = rf"==\s*{re.escape(header)}\s*==\s*\n(.*?)(?=\n==|\Z)"
    m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _extract_list_items(text: str) -> list[str]:
    """Extract bullet/list items from text."""
    items = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or len(line) < 3:
            continue
        # Bullet points: -, *, •
        m = re.match(r"^[-*•]\s*(.+)$", line)
        if m:
            items.append(m.group(1).strip())
            continue
        # Numbered: 1. 2. etc
        m = re.match(r"^\d+[.)]\s*(.+)$", line)
        if m:
            items.append(m.group(1).strip())
            continue
    return items


def _extract_phrases_after(text: str, patterns: list[str]) -> list[str]:
    """Extract phrases following patterns like 'Symptoms include X, Y, and Z'."""
    found = []
    text_lower = text.lower()
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            phrase = m.group(1).strip()
            # Split on common delimiters
            parts = re.split(r"[,;]\s*|\s+and\s+|\s+or\s+", phrase)
            for p in parts:
                p = p.strip()
                if len(p) > 4 and len(p) < 120:
                    found.append(p)
    return found


def _extract_symptoms(content: str, disease_name: str) -> list[str]:
    """Extract symptom entities from disease content."""
    symptoms = set()

    # Section-based
    sym_section = _extract_section(content, "Signs and symptoms")
    if not sym_section:
        sym_section = _extract_section(content, "Symptoms")
    if sym_section:
        for item in _extract_list_items(sym_section):
            if len(item) > 5:
                symptoms.add(item[:150])
        for phrase in _extract_phrases_after(
            sym_section,
            [
                r"symptoms?\s+include[s]?\s+(.+?)(?:\.|$)",
                r"signs?\s+include[s]?\s+(.+?)(?:\.|$)",
                r"characterized\s+by\s+(.+?)(?:\.|$)",
                r"typically\s+include[s]?\s+(.+?)(?:\.|$)",
                r"may\s+include\s+(.+?)(?:\.|$)",
            ],
        ):
            symptoms.add(phrase)

    # Inline patterns in full content
    for m in re.finditer(
        r"(?:symptoms?|signs?)\s+(?:include|are|may\s+be)\s+([^.]{10,200})",
        content,
        re.IGNORECASE,
    ):
        phrase = m.group(1).strip()
        if len(phrase) > 10:
            symptoms.add(phrase[:150])

    # Common symptom phrases
    symptom_keywords = [
        "pain", "fever", "fatigue", "weakness", "nausea", "vomiting", "headache",
        "cough", "shortness of breath", "chest pain", "abdominal pain", "jaundice",
        "swelling", "rash", "itching", "dizziness", "weight loss", "bleeding",
        "diarrhea", "constipation", "confusion", "seizure", "numbness",
    ]
    content_lower = content.lower()
    for kw in symptom_keywords:
        if kw in content_lower:
            symptoms.add(kw)

    return list(symptoms)[:30]  # Cap per disease


def _extract_treatments(content: str) -> list[str]:
    """Extract treatment/cure entities."""
    treatments = set()

    treat_section = _extract_section(content, "Treatment")
    if not treat_section:
        treat_section = _extract_section(content, "Management")
    if not treat_section:
        treat_section = _extract_section(content, "Therapy")
    src = treat_section or content

    for item in _extract_list_items(src):
        if len(item) > 5 and any(
            w in item.lower()
            for w in ["surgery", "medication", "therapy", "drug", "antibiotic", "injection"]
        ):
            treatments.add(item[:150])

    for phrase in _extract_phrases_after(
        src,
        [
            r"treatment\s+(?:may\s+)?(?:consist\s+of|include[s]?|is)\s+(.+?)(?:\.|$)",
            r"treated\s+with\s+(.+?)(?:\.|$)",
            r"managed\s+with\s+(.+?)(?:\.|$)",
            r"first-line\s+treatment\s+(?:is\s+)?(.+?)(?:\.|$)",
            r"primary\s+treatment\s+(?:is\s+)?(.+?)(?:\.|$)",
            r"surgery\s+is\s+(.+?)(?:\.|$)",
        ],
    ):
        treatments.add(phrase)

    # Medication names (common patterns)
    for m in re.finditer(
        r"\b(ibuprofen|paracetamol|acetaminophen|aspirin|omeprazole|"
        r"amoxicillin|metformin|insulin|prednisone|antibiotics?|"
        r"chemotherapy|radiation|surgery|stent|transplant)\b",
        src,
        re.IGNORECASE,
    ):
        treatments.add(m.group(1))

    return list(treatments)[:20]


def _extract_causes(content: str) -> list[str]:
    """Extract cause/risk factor entities."""
    causes = set()

    cause_section = _extract_section(content, "Causes")
    if not cause_section:
        cause_section = _extract_section(content, "Risk factors")
    src = cause_section or content

    for item in _extract_list_items(src):
        if len(item) > 5:
            causes.add(item[:120])

    for phrase in _extract_phrases_after(
        src,
        [
            r"caused\s+by\s+(.+?)(?:\.|$)",
            r"risk\s+factors?\s+include[s]?\s+(.+?)(?:\.|$)",
            r"associated\s+with\s+(.+?)(?:\.|$)",
            r"due\s+to\s+(.+?)(?:\.|$)",
        ],
    ):
        causes.add(phrase)

    return list(causes)[:15]


def build_graph_from_index(index: dict[str, str], source: str = "wikipedia") -> dict:
    """
    Build a knowledge graph from a disease->content index.

    Returns a JSON-serializable dict with nodes and edges.
    """
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []

    for disease_name, content in index.items():
        if not content or len(content) < 50:
            continue

        d_id = _slug(disease_name)
        nodes[d_id] = {"id": d_id, "type": NODE_DISEASE, "name": disease_name, "source": source}

        for sym in _extract_symptoms(content, disease_name):
            s_id = _slug(sym)
            if s_id and s_id != d_id:
                nodes[s_id] = {"id": s_id, "type": NODE_SYMPTOM, "name": sym}
                edges.append({"from": d_id, "to": s_id, "relation": REL_HAS_SYMPTOM})

        for tr in _extract_treatments(content):
            t_id = _slug(tr)
            if t_id and t_id != d_id:
                nodes[t_id] = {"id": t_id, "type": NODE_TREATMENT, "name": tr}
                edges.append({"from": d_id, "to": t_id, "relation": REL_TREATABLE_BY})

        for c in _extract_causes(content):
            c_id = _slug(c)
            if c_id and c_id != d_id:
                nodes[c_id] = {"id": c_id, "type": NODE_CAUSE, "name": c}
                edges.append({"from": d_id, "to": c_id, "relation": REL_CAUSED_BY})

    return {"nodes": nodes, "edges": edges, "sources": [source]}


def _load_graph() -> dict:
    """Load the persisted knowledge graph. Cached."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not _GRAPH_PATH.exists():
        logger.warning("Knowledge graph not found at %s. Run build_knowledge_graph.py first.", _GRAPH_PATH)
        return {"nodes": {}, "edges": []}
    try:
        with open(_GRAPH_PATH) as f:
            _CACHE = json.load(f)
        n = len(_CACHE.get("nodes", {}))
        e = len(_CACHE.get("edges", []))
        logger.info("Loaded knowledge graph: %d nodes, %d edges", n, e)
        return _CACHE
    except Exception as e:
        logger.warning("Failed to load knowledge graph: %s", e)
        return {"nodes": {}, "edges": []}


def _build_index(graph: dict, include_treatments: bool = True) -> dict:
    """
    Pre-build adjacency maps and symptom-word index. Excludes syllabus/cause-only nodes.
    """
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", [])

    # Exclude diseases that are syllabus topics (not diagnosis-relevant)
    def _is_diagnosis_disease(nid: str) -> bool:
        n = nodes.get(nid, {})
        if n.get("type") != NODE_DISEASE:
            return True
        src = n.get("source", "") or ""
        return "aiims_syllabus" not in src.lower()

    symptom_to_diseases: dict[str, set[str]] = {}
    disease_to_treatments: dict[str, set[str]] = {}
    disease_to_symptoms: dict[str, set[str]] = {}
    # word -> set of disease_ids (for fast lookup)
    word_to_diseases: dict[str, set[str]] = {}

    for e in edges:
        fr, to, rel = e["from"], e["to"], e["relation"]
        if rel == REL_HAS_SYMPTOM:
            if _is_diagnosis_disease(fr):
                disease_to_symptoms.setdefault(fr, set()).add(to)
                symptom_to_diseases.setdefault(to, set()).add(fr)
        elif rel == REL_TREATABLE_BY and include_treatments:
            disease_to_treatments.setdefault(fr, set()).add(to)

    # Build word index: for each symptom name, add its words -> disease_ids
    for sid, disease_ids in symptom_to_diseases.items():
        snode = nodes.get(sid, {})
        sname = snode.get("name", sid)
        for w in _normalise_for_match(sname).split():
            if len(w) > 2:
                word_to_diseases.setdefault(w, set()).update(disease_ids)

    return {
        "nodes": nodes,
        "symptom_to_diseases": symptom_to_diseases,
        "disease_to_symptoms": disease_to_symptoms,
        "disease_to_treatments": disease_to_treatments,
        "word_to_diseases": word_to_diseases,
    }


def _get_index(include_treatments: bool = True) -> dict | None:
    """Get pre-built index. Builds on first call and caches."""
    global _INDEX
    graph = _load_graph()
    if not graph.get("nodes") or not graph.get("edges"):
        return None
    if _INDEX is None:
        _INDEX = _build_index(graph, include_treatments=True)
        logger.info(
            "Built graph index: %d symptom->disease, %d word->disease",
            len(_INDEX["symptom_to_diseases"]),
            len(_INDEX["word_to_diseases"]),
        )
    return _INDEX


def _normalise_for_match(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    return re.sub(r"\s+", " ", t)


def get_graph_context(
    symptoms: str,
    suspected_diagnoses: list[str] | None = None,
    max_chars: int = 2500,
    top_k_diseases: int = 4,
    include_treatments: bool = True,
) -> str:
    """
    Retrieve relevant disease and cure context from the knowledge graph.

    Uses pre-built index for fast lookup. Traverses symptom -> disease -> treatment
    paths to provide structured context for MedGemma diagnosis and cure recommendations.

    Returns:
        Formatted context string for the prompt.
    """
    idx = _get_index(include_treatments)
    if not idx:
        return ""

    nodes = idx["nodes"]
    symptom_to_diseases = idx["symptom_to_diseases"]
    disease_to_symptoms = idx["disease_to_symptoms"]
    disease_to_treatments = idx["disease_to_treatments"]
    word_to_diseases = idx["word_to_diseases"]

    sym_words = set(w for w in _normalise_for_match(symptoms).split() if len(w) > 2)
    if not sym_words:
        return ""

    # Fast path: get candidate diseases from word index (only diseases matching symptom words)
    candidate_diseases: set[str] = set()
    for w in sym_words:
        candidate_diseases.update(word_to_diseases.get(w, set()))

    if not candidate_diseases:
        return ""

    # Score only candidate diseases (O(candidates * symptoms_per_disease))
    disease_scores: dict[str, float] = {}
    sym_words_joined = " ".join(sym_words)

    for did in candidate_diseases:
        dnode = nodes.get(did, {})
        dnorm = _normalise_for_match(dnode.get("name", did))

        bonus = 0.0
        if suspected_diagnoses:
            for sd in suspected_diagnoses:
                sd_norm = _normalise_for_match(sd)
                if sd_norm in dnorm or dnorm in sd_norm:
                    bonus = 2.0
                    break

        score = bonus
        for osid in disease_to_symptoms.get(did, set()):
            oname_norm = _normalise_for_match(nodes.get(osid, {}).get("name", ""))
            if any(w in oname_norm or oname_norm in sym_words_joined for w in sym_words):
                score += 1

        disease_scores[did] = disease_scores.get(did, 0) + score

    ranked = sorted(disease_scores.items(), key=lambda x: -x[1])[:top_k_diseases]
    if not ranked:
        return ""

    parts = []
    total = 0
    for did, _ in ranked:
        dnode = nodes.get(did, {})
        dname = dnode.get("name", did)
        block = f"**{dname}**\n"

        syms = disease_to_symptoms.get(did, set())
        if syms:
            sym_names = [nodes.get(s, {}).get("name", s) for s in list(syms)[:8]]
            block += f"  Symptoms: {', '.join(sym_names)}\n"

        if include_treatments:
            treat_ids = disease_to_treatments.get(did, set())
            if treat_ids:
                treat_names = [nodes.get(t, {}).get("name", t) for t in list(treat_ids)[:6]]
                block += f"  Treatments: {', '.join(treat_names)}\n"

        block += "\n"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)

    if not parts:
        return ""

    return (
        "\n\nKnowledge Graph Reference (disease–symptom–treatment):\n"
        + "Use this to inform your diagnosis and treatment recommendations.\n"
        + "---\n"
        + "".join(parts)
    )


def warm_cache() -> None:
    """Eager-load graph and index at startup. Call from FastAPI lifespan."""
    _get_index(include_treatments=True)
