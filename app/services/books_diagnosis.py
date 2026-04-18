"""
Books Brain — Diagnosis from disease knowledge graph and books only.

Uses the knowledge graph (Wikipedia, AIIMS/StatPearls, AIIMS syllabus) to
match symptoms to diseases and return diagnosis with treatments. No AI model.

Returns the same schema as MedGemma for API compatibility.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("books_diagnosis")

MODEL_VERSION = "books-brain-v1"

# Path to knowledge graph
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_GRAPH_PATH = _BACKEND_ROOT.parent / "disease_books" / "knowledge_graph.json"


def diagnose(
    symptoms: str,
    clinical_notes: str = "",
    medical_history: dict | None = None,
    top_k: int = 4,
) -> dict:
    """
    Diagnose from books/knowledge graph only. No AI.

    Returns the same schema as medgemma_diagnosis.diagnose() for compatibility.
    """
    try:
        from app.services.disease_knowledge_graph import get_graph_context
    except ImportError:
        logger.warning("disease_knowledge_graph not available")
        return _empty_result("Books brain unavailable")

    if not _GRAPH_PATH.exists():
        logger.warning("Knowledge graph not found at %s", _GRAPH_PATH)
        return _empty_result("Knowledge graph not built. Run: python scripts/build_knowledge_graph.py --merge-aiims")

    ctx = get_graph_context(
        symptoms,
        suspected_diagnoses=None,
        max_chars=3000,
        top_k_diseases=top_k,
        include_treatments=True,
    )

    if not ctx:
        return _empty_result("No matching diseases in knowledge base for given symptoms.")

    # Parse the context to extract primary diagnosis and differentials
    result = _parse_graph_context_to_result(ctx, symptoms)
    result["model_version"] = MODEL_VERSION
    result["medical_history_considered"] = bool(medical_history)

    # Enrich with app plans (dietary, routine, ayurvedic)
    result = _enrich_with_app_plans(result)

    return result


def _parse_graph_context_to_result(ctx: str, symptoms: str) -> dict:
    """Parse get_graph_context output into diagnosis result schema."""
    diseases = []
    current_disease = None
    current_symptoms = []
    current_treatments = []

    for line in ctx.split("\n"):
        line = line.strip()
        if not line or line.startswith("Knowledge Graph") or line.startswith("Use this"):
            continue
        if line == "---":
            if current_disease:
                diseases.append({
                    "name": current_disease,
                    "symptoms": current_symptoms,
                    "treatments": current_treatments,
                })
            current_disease = None
            current_symptoms = []
            current_treatments = []
            continue
        if line.startswith("**") and line.endswith("**"):
            if current_disease:
                diseases.append({
                    "name": current_disease,
                    "symptoms": current_symptoms,
                    "treatments": current_treatments,
                })
            current_disease = line.strip("*").strip()
            current_symptoms = []
            current_treatments = []
        elif line.startswith("Symptoms:") and current_disease:
            parts = line.replace("Symptoms:", "").strip().split(", ")
            current_symptoms = [p.strip() for p in parts if p.strip()]
        elif line.startswith("Treatments:") and current_disease:
            parts = line.replace("Treatments:", "").strip().split(", ")
            current_treatments = [p.strip() for p in parts if p.strip()]

    if current_disease:
        diseases.append({
            "name": current_disease,
            "symptoms": current_symptoms,
            "treatments": current_treatments,
        })

    if not diseases:
        return _empty_result("No matching diseases found.")

    primary = diseases[0]
    differentials = [
        {
            "diagnosis": d["name"],
            "confidence": max(0.1, 0.8 - (i * 0.2)),
            "reasoning": f"Matches symptoms: {', '.join(d['symptoms'][:3])}." if d["symptoms"] else "",
        }
        for i, d in enumerate(diseases[1:4])
    ]

    # Build medications from treatments (simple mapping)
    medications = []
    for t in primary.get("treatments", [])[:6]:
        medications.append({
            "name": t,
            "dosage": "",
            "frequency": "As prescribed",
            "when_to_take": "As directed by your doctor",
            "duration": "",
            "type": "tablet",
            "notes": "Consult doctor for dosage",
        })

    # Simple layman summary for books brain (no LLM)
    layman = (
        f"Based on your symptoms, the most likely condition is {primary['name']}. "
        f"This is a condition that can often be managed with proper care. "
        f"Consult a doctor to confirm the diagnosis and get personalized treatment."
    )

    return {
        "diagnosis": primary["name"],
        "layman_summary": layman,
        "differential_diagnoses": differentials,
        "reasoning": (
            f"Based on symptom match from medical reference books (Wikipedia, AIIMS/StatPearls). "
            f"Presenting symptoms suggest {primary['name']}. "
            f"Matching symptoms: {', '.join(primary['symptoms'][:5])}."
            if primary["symptoms"] else f"Diagnosis from knowledge graph based on: {symptoms[:100]}."
        ),
        "confidence": 0.75,
        "severity": "moderate",
        "urgency": "soon",
        "findings": [{"finding": s, "severity": "medium"} for s in primary.get("symptoms", [])[:5]],
        "medications": medications,
        "lifestyle_recommendations": ["Follow medical advice", "Maintain healthy lifestyle"],
        "precautions": ["Consult a healthcare professional for confirmation"],
        "recommended_tests": ["Clinical evaluation by physician"],
        "when_to_see_doctor": "See a doctor for proper evaluation and treatment plan.",
        "model_version": MODEL_VERSION,
        "medical_history_considered": False,
        "allergy_warnings": None,
    }


def _empty_result(reason: str) -> dict:
    """Return empty diagnosis result with reason."""
    return {
        "diagnosis": "Unable to diagnose",
        "differential_diagnoses": [],
        "reasoning": reason,
        "confidence": 0.0,
        "severity": "moderate",
        "urgency": "soon",
        "findings": [],
        "medications": [],
        "lifestyle_recommendations": [],
        "precautions": ["Consult a healthcare professional"],
        "recommended_tests": [],
        "when_to_see_doctor": "See a doctor for evaluation.",
        "model_version": MODEL_VERSION,
        "medical_history_considered": False,
        "allergy_warnings": None,
    }


def _enrich_with_app_plans(result: dict) -> dict:
    """Add dietary plan, routine plan, ayurvedic medicines."""
    try:
        from app.services.dietary_routine_plans import get_dietary_plan, get_routine_plan
        from app.services.ayurvedic_medicines import get_ayurvedic_medicines

        diagnosis_name = result.get("diagnosis", "")
        result["dietary_plan"] = get_dietary_plan(diagnosis_name)
        result["routine_plan"] = get_routine_plan(diagnosis_name)
        result["ayurvedic_medicines"] = get_ayurvedic_medicines(diagnosis_name)
    except ImportError:
        result["dietary_plan"] = []
        result["routine_plan"] = []
        result["ayurvedic_medicines"] = []
    return result
