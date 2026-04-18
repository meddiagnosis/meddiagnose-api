"""
Vertex AI MedGemma diagnosis for bulk/Kafka processing.

Uses GCP Vertex AI endpoint (same as Airflow DAG) when configured.
Returns the same format as medgemma_diagnosis.diagnose() for compatibility.
"""

import json
import logging
import re
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger("vertex_ai_diagnosis")

def _get_vertex_prompt() -> str:
    from app.core.config import get_settings
    region = (get_settings().REGION or "India").strip()
    region_note = ""
    if region.lower() == "india":
        region_note = """
REGION — INDIA: Prescribe ONLY medications commonly available in Indian pharmacies.
Use generic/INN names (Paracetamol, Cetirizine, Omeprazole, Pantoprazole, Amoxicillin, Metformin, Diclofenac, Ibuprofen).
Prefer Paracetamol over Acetaminophen. Avoid US-only drugs not stocked in India.
"""
    return f"""You are an AI medical assistant helping patients understand their health.
{region_note}
Analyze the following patient data and provide a clear diagnosis with treatment recommendations.

IMPORTANT: This is a preliminary AI assessment. Always consult a qualified physician before starting any medication.

=== PATIENT DATA ===

Clinical Notes / Report Summary:
{clinical_notes}

Reported Symptoms:
{symptoms}

Medical History & Allergies:
{medical_history}

=== INSTRUCTIONS ===

Provide your assessment in the following JSON format:
{{
    "diagnosis": "Primary suspected condition/disease",
    "reasoning": "Clear explanation in simple language why this diagnosis is suspected",
    "severity": "mild|moderate|severe|critical",
    "differential_diagnoses": [
        {{"diagnosis": "Alternative possibility 1", "confidence": 0.0-1.0, "reasoning": "brief reason"}},
        {{"diagnosis": "Alternative possibility 2", "confidence": 0.0-1.0, "reasoning": "brief reason"}}
    ],
    "findings": [
        {{"finding": "Key finding from the reports", "severity": "low|medium|high|critical"}}
    ],
    "medications": [
        {{
            "name": "Generic/INN name (e.g. Paracetamol, Pantoprazole)",
            "dosage": "Recommended dosage (e.g., 500mg)",
            "frequency": "How often (e.g., twice daily)",
            "when_to_take": "When to take (e.g. Morning after breakfast, At bedtime)",
            "duration": "For how long (e.g., 7 days)",
            "type": "tablet|capsule|syrup|injection|topical|inhaler",
            "notes": "Take after meals / any special instructions"
        }}
    ],
    "lifestyle_recommendations": ["Recommendation 1", "Recommendation 2"],
    "recommended_tests": ["Any additional tests needed"],
    "when_to_see_doctor": "Describe warning signs that need immediate medical attention",
    "confidence": 0.0 to 1.0,
    "urgency": "routine|soon|urgent|emergency",
    "precautions": ["Precaution 1", "Precaution 2"]
}}

Respond ONLY with valid JSON. Do not include any text outside the JSON object.
"""


def _clamp_confidence(val: Any) -> float:
    try:
        f = float(val)
        return max(0.0, min(1.0, f))
    except (TypeError, ValueError):
        return 0.7


def _normalise_vertex_result(raw: dict) -> dict:
    """Normalise Vertex AI response to match consumer's expected format."""
    severity = str(raw.get("severity", "moderate")).lower()
    if severity not in {"mild", "moderate", "severe", "critical"}:
        severity = "moderate"

    urgency = str(raw.get("urgency", "soon")).lower()
    if urgency not in {"routine", "soon", "urgent", "emergency"}:
        urgency = "soon"

    findings_raw = raw.get("findings") or []
    findings = []
    for f in findings_raw:
        if isinstance(f, dict):
            findings.append({
                "finding": str(f.get("finding", "")),
                "severity": str(f.get("severity", "medium")),
            })
        elif isinstance(f, str):
            findings.append({"finding": f, "severity": "medium"})

    meds_raw = raw.get("medications") or []
    medications = []
    for m in meds_raw:
        if isinstance(m, dict):
            freq = str(m.get("frequency", ""))
            when = str(m.get("when_to_take", "")) or freq
            medications.append({
                "name": str(m.get("name", "")),
                "dosage": str(m.get("dosage", "")),
                "frequency": freq,
                "when_to_take": when,
                "duration": str(m.get("duration", "")),
                "type": str(m.get("type", "tablet")),
                "notes": str(m.get("notes", "")),
            })
        elif isinstance(m, str):
            medications.append({"name": m, "dosage": "", "frequency": "", "when_to_take": "", "duration": "", "type": "tablet", "notes": ""})

    def _str_list(key: str) -> list[str]:
        val = raw.get(key) or []
        if isinstance(val, list):
            return [str(v) for v in val]
        return [str(val)]

    diff_raw = raw.get("differential_diagnoses") or []
    differential_diagnoses = []
    for d in diff_raw:
        if isinstance(d, dict):
            differential_diagnoses.append({
                "diagnosis": str(d.get("diagnosis", "")),
                "confidence": _clamp_confidence(d.get("confidence", 0.0)),
                "reasoning": str(d.get("reasoning", "")),
            })
        elif isinstance(d, str):
            differential_diagnoses.append({"diagnosis": d, "confidence": 0.0, "reasoning": ""})

    return {
        "diagnosis": str(raw.get("diagnosis", "Analysis pending")),
        "differential_diagnoses": differential_diagnoses,
        "reasoning": str(raw.get("reasoning", "")),
        "confidence": _clamp_confidence(raw.get("confidence", 0.7)),
        "severity": severity,
        "urgency": urgency,
        "findings": findings,
        "medications": medications,
        "lifestyle_recommendations": _str_list("lifestyle_recommendations"),
        "precautions": _str_list("precautions"),
        "recommended_tests": _str_list("recommended_tests"),
        "when_to_see_doctor": str(
            raw.get("when_to_see_doctor", "Consult a healthcare professional for proper evaluation.")
        ),
        "model_version": "medgemma-4b-vertex",
    }


def _parse_vertex_response(raw: str) -> dict:
    """Parse JSON from Vertex AI model output."""
    try:
        if isinstance(raw, str) and raw.strip().startswith("{"):
            return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", str(raw or ""))
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {
        "diagnosis": str(raw)[:500] if raw else "No diagnosis generated",
        "reasoning": str(raw)[500:2000] if raw and len(str(raw)) > 500 else "",
        "findings": [],
    }


def diagnose_vertex(
    symptoms: str,
    clinical_notes: str = "",
    medical_history: dict | None = None,
    specialty: str = "general",
) -> dict:
    """
    Run MedGemma inference via GCP Vertex AI endpoint.
    Sync; run in executor for async contexts.
    """
    settings = get_settings()
    endpoint_id = settings.MEDGEMMA_ENDPOINT_4B or settings.MEDGEMMA_ENDPOINT_27B
    project_id = settings.GCP_PROJECT_ID
    location = settings.VERTEX_AI_LOCATION

    if not endpoint_id or not project_id:
        logger.warning("Vertex AI not configured (MEDGEMMA_ENDPOINT_4B, GCP_PROJECT_ID)")
        return _normalise_vertex_result({
            "diagnosis": "Vertex AI not configured",
            "reasoning": "Set MEDGEMMA_ENDPOINT_4B and GCP_PROJECT_ID, VERTEX_AI_LOCATION for real inference.",
            "confidence": 0.0,
        })

    try:
        from google.cloud import aiplatform
        aiplatform.init(project=project_id, location=location)
        endpoint = aiplatform.Endpoint(endpoint_id)

        clinical = clinical_notes or "None reported"
        symptoms_str = symptoms if isinstance(symptoms, str) else ", ".join(str(s) for s in (symptoms or []))
        history_str = json.dumps(medical_history or {}, indent=2)

        prompt = _get_vertex_prompt().format(
            clinical_notes=clinical,
            symptoms=symptoms_str or "None reported",
            medical_history=history_str,
        )

        instances = [{"prompt": prompt}]
        response = endpoint.predict(instances=instances)
        raw = response.predictions[0] if response.predictions else ""
        if isinstance(raw, dict):
            parsed = raw
        else:
            parsed = _parse_vertex_response(str(raw))
        return _normalise_vertex_result(parsed)

    except Exception as e:
        logger.exception("Vertex AI inference failed: %s", e)
        return _normalise_vertex_result({
            "diagnosis": "Error during inference",
            "reasoning": str(e),
            "confidence": 0.0,
        })
