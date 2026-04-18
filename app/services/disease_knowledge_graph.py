"""
Disease Knowledge Graph — Graph-based retrieval from AIIMS and Wikipedia books.

Builds a knowledge graph from disease texts with entities (diseases, symptoms,
treatments, causes) and relationships. Used for improved diagnosis and cure
retrieval when integrated with MedGemma.

Data loading priority: GCS bucket → local filesystem.
Index caching: Redis (survives cold starts) → build from scratch.
Scoring: feedback-weighted edges from diagnosis_feedback table.
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

# GCS paths for cloud-hosted graph data
_GCS_GRAPH_BLOB = "knowledge_graph/knowledge_graph.json"

# Redis keys
_REDIS_GRAPH_KEY = "meddiagnose:knowledge_graph"
_REDIS_INDEX_KEY = "meddiagnose:knowledge_graph_index"
_REDIS_WEIGHTS_KEY = "meddiagnose:feedback_weights"
_REDIS_TTL = 3600 * 6  # 6 hours

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
# Feedback weights: disease_name_normalised -> accuracy weight (0.0-2.0)
_FEEDBACK_WEIGHTS: dict[str, float] | None = None


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


def _load_graph_from_gcs() -> dict | None:
    """Try loading graph JSON from GCS bucket. Returns None on failure."""
    try:
        from app.core.config import get_settings
        settings = get_settings()
        if not settings.GCS_BUCKET:
            return None
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(settings.GCS_BUCKET)
        blob = bucket.blob(_GCS_GRAPH_BLOB)
        if not blob.exists():
            logger.debug("Graph not found in GCS: gs://%s/%s", settings.GCS_BUCKET, _GCS_GRAPH_BLOB)
            return None
        data = json.loads(blob.download_as_text())
        n = len(data.get("nodes", {}))
        e = len(data.get("edges", []))
        logger.info("Loaded knowledge graph from GCS: %d nodes, %d edges", n, e)
        return data
    except Exception as e:
        logger.debug("GCS graph load failed (will try local): %s", e)
        return None


def _load_graph_from_redis() -> dict | None:
    """Try loading cached graph from Redis (sync, for startup)."""
    try:
        import redis
        from app.core.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        val = r.get(_REDIS_GRAPH_KEY)
        if val:
            data = json.loads(val)
            logger.info("Loaded knowledge graph from Redis cache")
            return data
    except Exception as e:
        logger.debug("Redis graph load failed: %s", e)
    return None


def _save_graph_to_redis(graph: dict) -> None:
    """Cache the graph JSON in Redis."""
    try:
        import redis
        from app.core.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.setex(_REDIS_GRAPH_KEY, _REDIS_TTL, json.dumps(graph))
        logger.debug("Cached knowledge graph in Redis")
    except Exception as e:
        logger.debug("Redis graph cache failed: %s", e)


def _load_graph() -> dict:
    """Load the knowledge graph. Priority: Redis cache → GCS → local file."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    # 1. Try Redis (fastest, survives cold starts)
    data = _load_graph_from_redis()
    if data and data.get("nodes"):
        _CACHE = data
        return _CACHE

    # 2. Try GCS (cloud-hosted, updateable without redeploy)
    data = _load_graph_from_gcs()
    if data and data.get("nodes"):
        _CACHE = data
        _save_graph_to_redis(data)
        return _CACHE

    # 3. Fall back to local file
    if not _GRAPH_PATH.exists():
        logger.warning("Knowledge graph not found at %s. Run build_knowledge_graph.py first.", _GRAPH_PATH)
        return {"nodes": {}, "edges": []}
    try:
        with open(_GRAPH_PATH) as f:
            _CACHE = json.load(f)
        n = len(_CACHE.get("nodes", {}))
        e = len(_CACHE.get("edges", []))
        logger.info("Loaded knowledge graph from local file: %d nodes, %d edges", n, e)
        _save_graph_to_redis(_CACHE)
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


def _serialize_index(idx: dict) -> str:
    """Serialize index (with sets) to JSON string."""
    serializable = {
        "symptom_to_diseases": {k: list(v) for k, v in idx["symptom_to_diseases"].items()},
        "disease_to_symptoms": {k: list(v) for k, v in idx["disease_to_symptoms"].items()},
        "disease_to_treatments": {k: list(v) for k, v in idx["disease_to_treatments"].items()},
        "word_to_diseases": {k: list(v) for k, v in idx["word_to_diseases"].items()},
    }
    return json.dumps(serializable)


def _deserialize_index(data: str, nodes: dict) -> dict:
    """Deserialize JSON string back to index with sets."""
    raw = json.loads(data)
    return {
        "nodes": nodes,
        "symptom_to_diseases": {k: set(v) for k, v in raw["symptom_to_diseases"].items()},
        "disease_to_symptoms": {k: set(v) for k, v in raw["disease_to_symptoms"].items()},
        "disease_to_treatments": {k: set(v) for k, v in raw["disease_to_treatments"].items()},
        "word_to_diseases": {k: set(v) for k, v in raw["word_to_diseases"].items()},
    }


def _load_index_from_redis(nodes: dict) -> dict | None:
    """Try loading the pre-built index from Redis."""
    try:
        import redis
        from app.core.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        val = r.get(_REDIS_INDEX_KEY)
        if val:
            idx = _deserialize_index(val, nodes)
            logger.info("Loaded graph index from Redis cache")
            return idx
    except Exception as e:
        logger.debug("Redis index load failed: %s", e)
    return None


def _save_index_to_redis(idx: dict) -> None:
    """Cache the built index in Redis (without nodes — they're in the graph)."""
    try:
        import redis
        from app.core.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.setex(_REDIS_INDEX_KEY, _REDIS_TTL, _serialize_index(idx))
        logger.debug("Cached graph index in Redis")
    except Exception as e:
        logger.debug("Redis index cache failed: %s", e)


def _get_index(include_treatments: bool = True) -> dict | None:
    """Get pre-built index. Priority: in-memory → Redis → build from scratch."""
    global _INDEX
    graph = _load_graph()
    if not graph.get("nodes") or not graph.get("edges"):
        return None
    if _INDEX is not None:
        return _INDEX

    nodes = graph.get("nodes", {})

    # Try Redis first (fast cold start)
    idx = _load_index_from_redis(nodes)
    if idx:
        _INDEX = idx
        return _INDEX

    # Build from scratch and cache
    _INDEX = _build_index(graph, include_treatments=True)
    logger.info(
        "Built graph index: %d symptom->disease, %d word->disease",
        len(_INDEX["symptom_to_diseases"]),
        len(_INDEX["word_to_diseases"]),
    )
    _save_index_to_redis(_INDEX)
    return _INDEX


def _normalise_for_match(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    return re.sub(r"\s+", " ", t)


def _load_feedback_weights() -> dict[str, float]:
    """Load feedback-based accuracy weights from Redis. Returns disease_name_norm -> weight."""
    global _FEEDBACK_WEIGHTS
    if _FEEDBACK_WEIGHTS is not None:
        return _FEEDBACK_WEIGHTS
    try:
        import redis
        from app.core.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        val = r.get(_REDIS_WEIGHTS_KEY)
        if val:
            _FEEDBACK_WEIGHTS = json.loads(val)
            logger.debug("Loaded %d feedback weights from Redis", len(_FEEDBACK_WEIGHTS))
            return _FEEDBACK_WEIGHTS
    except Exception as e:
        logger.debug("Feedback weights load failed: %s", e)
    _FEEDBACK_WEIGHTS = {}
    return _FEEDBACK_WEIGHTS


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
    Applies feedback-based accuracy weights to boost diseases the AI diagnoses well.

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

    # Load feedback weights (cached in-memory after first call)
    feedback_weights = _load_feedback_weights()

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
        dname = dnode.get("name", did)
        dnorm = _normalise_for_match(dname)

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

        # Apply feedback weight: diseases the AI gets right more often rank higher
        if feedback_weights and dnorm in feedback_weights:
            score *= feedback_weights[dnorm]

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
    """Eager-load graph, index, and feedback weights at startup."""
    _get_index(include_treatments=True)
    _load_feedback_weights()


def invalidate_cache() -> None:
    """Clear in-memory caches. Forces reload from Redis/GCS/local on next access."""
    global _CACHE, _INDEX, _FEEDBACK_WEIGHTS
    _CACHE = None
    _INDEX = None
    _FEEDBACK_WEIGHTS = None
