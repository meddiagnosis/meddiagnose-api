"""
MedGemma diagnosis service via Ollama.

Sends patient symptoms to the locally-running MedGemma 4B model through
Ollama's chat API and parses the structured JSON response.  Falls back
to the keyword-based mock engine when Ollama is unreachable.

Handles Ollama queue/load limits: retries on timeout or 503 with backoff.
"""

import asyncio
import json
import logging
import re

import httpx

from app.core.config import get_settings

logger = logging.getLogger("medgemma_diagnosis")

MODEL_VERSION = "medgemma-4b-ollama-v3"


def _get_image_analysis_block(
    file_hints: list[tuple[str, str]] | None,
    has_images: bool,
) -> str:
    """Return modality-specific instructions and lab extraction schema when images are present."""
    if not has_images:
        return ""

    file_hints = file_hints or []
    modalities = {h[0] for h in file_hints}
    hints_text = ", ".join(f"{t}: {fn}" for t, fn in file_hints) if file_hints else "attached images"

    blocks = [
        "IMAGE_ANALYSIS — When attached images are present:",
        f"Uploaded files: {hints_text}",
    ]

    if "radiology" in modalities:
        blocks.append(
            "- RADIOLOGY (X-ray, CT, MRI, DICOM): Describe findings, anatomical location, "
            "abnormalities. Suggest differential diagnoses based on imaging."
        )
    if "document" in modalities:
        blocks.append(
            "- LAB REPORTS / DOCUMENTS: Extract structured data. Include extracted_lab_values "
            "array: [{\"test\": \"<name>\", \"value\": \"<value>\", \"unit\": \"<unit>\", "
            "\"reference\": \"<ref range>\", \"status\": \"normal|high|low|abnormal\"}]. "
            "Incorporate abnormal values into diagnosis and reasoning."
        )
    if "image" in modalities or not modalities:
        blocks.append(
            "- DERMATOLOGY / GENERAL IMAGES: Describe lesions, distribution, morphology. "
            "Suggest dermatological or relevant differentials."
        )

    blocks.append("")
    blocks.append(
        "extracted_lab_values schema (include when lab reports are present, else empty array): "
        "[{\"test\": \"<test name>\", \"value\": \"<value>\", \"unit\": \"<unit>\", "
        "\"reference\": \"<reference range>\", \"status\": \"normal|high|low|abnormal\"}]"
    )
    return "\n".join(blocks)


def _get_system_prompt(
    file_hints: list[tuple[str, str]] | None = None,
    has_images: bool = False,
) -> str:
    settings = get_settings()
    region = (settings.REGION or "India").strip()
    region_block = ""
    if region.lower() == "india":
        region_block = """
REGION — INDIA: Prescribe ONLY medications commonly available in Indian pharmacies.
- Use generic/INN names (e.g. Paracetamol, Cetirizine, Omeprazole, Amoxicillin, Metformin).
- Prefer Paracetamol over Acetaminophen; Diclofenac, Ibuprofen are common.
- Avoid drugs not routinely stocked in India (e.g. some US-only brands).
- Dosages should follow Indian standard practice (e.g. Paracetamol 500mg, Cetirizine 10mg).
"""

    image_block = _get_image_analysis_block(file_hints, has_images)

    return (
        "You are MedGemma, a clinical decision-support AI.\n"
        + region_block
        + "\n"
        "When analysing a patient case, follow this process:\n"
        "1. Identify the key symptoms and clinical signs presented.\n"
        "2. If vital signs are provided (BP, SpO2, heart rate, temperature, respiratory rate, blood sugar, weight, pain level, ECG), incorporate them into your reasoning — abnormal values (e.g. hypertension, hypoxia, fever, tachypnea, hyperglycemia) can support or refute differentials and affect severity/urgency.\n"
        "3. Consider the top differential diagnoses that fit these findings.\n"
        "4. Select the most likely primary diagnosis and rank alternatives.\n"
        "\n"
        "Respond with ONLY a JSON object — no markdown fences, no commentary.\n"
        "\n"
        "IMPORTANT naming rules:\n"
        '- Use the standard medical / clinical name for every diagnosis '
        '(e.g. "Gastroesophageal Reflux Disease" not "GERD", '
        '"Hematuria" not "Blood In Urine", "Myopia" not "Nearsightedness").\n'
        "- Use the commonly accepted disease name, not a symptom description.\n"
        "\n"
        "Required JSON schema:\n"
        '{\n'
        '  "diagnosis": "<primary diagnosis — standard medical name>",\n'
        '  "layman_summary": "<2-4 sentences in plain language for the patient: what this condition means, what to expect, and what they should do. Avoid jargon.>",\n'
        '  "differential_diagnoses": [\n'
        '    {"diagnosis": "<alternative diagnosis>", "confidence": <0.0-1.0>, "reasoning": "<why this is considered>"}\n'
        '  ],\n'
        '  "reasoning": "<detailed clinical reasoning for primary diagnosis, 3-6 sentences>",\n'
        '  "confidence": <float 0.0-1.0>,\n'
        '  "severity": "<mild | moderate | severe | critical>",\n'
        '  "urgency": "<routine | soon | urgent | emergency>",\n'
        '  "findings": [\n'
        '    {"finding": "<clinical finding text>", "severity": "<low | medium | high>"}\n'
        '  ],\n'
        '  "medications": [\n'
        '    {\n'
        '      "name": "<drug name>",\n'
        '      "dosage": "<e.g. 500 mg>",\n'
        '      "frequency": "<e.g. twice daily>",\n'
        '      "when_to_take": "<patient-friendly timing>",\n'
        '      "duration": "<e.g. 7 days>",\n'
        '      "type": "<tablet | capsule | syrup | injection | inhaler | cream | drops | other>",\n'
        '      "notes": "<optional notes>"\n'
        '    }\n'
        '  ],\n'
        '  "lifestyle_recommendations": ["<recommendation>"],\n'
        '  "precautions": ["<precaution>"],\n'
        '  "recommended_tests": ["<test name>"],\n'
        '  "when_to_see_doctor": "<guidance text>"\n'
        '}\n'
        "\n"
        + image_block
        + "\n"
        "Diagnostic rules:\n"
        '- Always diagnose the PRIMARY UNDERLYING DISEASE, never a secondary '
        'complication, symptom, or sign. For example: diagnose "Gastroenteritis" '
        'not "Dehydration"; "Alcoholic Hepatitis" not "Ascites"; '
        '"Brain Tumor" not "Headache".\n'
        "- When the symptom text explicitly names or describes a known condition "
        '(e.g. "bee stings", "brain tumor", "hiatal hernia"), that condition '
        "must be your primary diagnosis or appear prominently in your differentials.\n"
        "- Prefer a specific, recognised disease entity over a generic reaction "
        'type or symptom category (e.g. "Bee Sting Envenomation" not "Local Reaction"; '
        '"Morton\'s Neuroma" not "Metatarsalgia" when a neuroma-specific finding '
        'such as a "pebble in shoe" sensation is described).\n'
        "- When symptoms are ambiguous between common and rare conditions, favour "
        'the more common/prevalent diagnosis (e.g. "Osteoarthritis" is far more '
        'common than "Rheumatoid Arthritis" for non-inflammatory joint pain).\n'
        "\n"
        "Output rules:\n"
        "- differential_diagnoses must contain 2-3 alternative diagnoses ranked "
        "by confidence (the primary diagnosis should NOT appear in this list)\n"
        "- confidence values must be between 0.0 and 1.0\n"
        "- severity must be one of: mild, moderate, severe, critical\n"
        "- urgency must be one of: routine, soon, urgent, emergency\n"
        "- findings, medications, lifestyle_recommendations, precautions, "
        "recommended_tests must be non-empty arrays\n"
        "- Provide evidence-based, clinically accurate information\n"
        "- If symptoms are vague, still provide your best differential and "
        "state uncertainty in the reasoning field\n"
        "\n"
        'Example 1 — "Patient has fever, sore throat, and swollen lymph nodes":\n'
        '{\n'
        '  "diagnosis": "Acute Pharyngitis",\n'
        '  "differential_diagnoses": [\n'
        '    {"diagnosis": "Infectious Mononucleosis", "confidence": 0.25, "reasoning": "Fever with lymphadenopathy can indicate EBV infection"},\n'
        '    {"diagnosis": "Peritonsillar Abscess", "confidence": 0.10, "reasoning": "Severe sore throat with swelling warrants exclusion"}\n'
        '  ],\n'
        '  "reasoning": "The combination of fever, sore throat, and cervical lymphadenopathy is most consistent with acute pharyngitis...",\n'
        '  "confidence": 0.85,\n'
        '  "severity": "mild",\n'
        '  "urgency": "soon",\n'
        '  "findings": [{"finding": "Pharyngeal erythema", "severity": "medium"}],\n'
        '  "medications": [{"name": "Paracetamol", "dosage": "500 mg", "frequency": "every 6 hours", "when_to_take": "Every 6 hours (e.g. 8am, 2pm, 8pm) after food", "duration": "5 days", "type": "tablet", "notes": "For fever and pain. Available as Crocin, Dolo."}],\n'
        '  "lifestyle_recommendations": ["Rest and adequate hydration"],\n'
        '  "precautions": ["Seek care if difficulty breathing develops"],\n'
        '  "recommended_tests": ["Rapid strep test"],\n'
        '  "when_to_see_doctor": "If symptoms worsen after 48 hours or difficulty swallowing develops"\n'
        '}\n'
        "\n"
        'Example 2 — "Patient reports burning sensation in chest after meals, acid taste in mouth, worsens when lying down":\n'
        '{\n'
        '  "diagnosis": "Gastroesophageal Reflux Disease",\n'
        '  "differential_diagnoses": [\n'
        '    {"diagnosis": "Hiatal Hernia", "confidence": 0.20, "reasoning": "Hiatal hernia is a common anatomical cause of reflux symptoms"},\n'
        '    {"diagnosis": "Peptic Ulcer Disease", "confidence": 0.15, "reasoning": "Epigastric burning can overlap with ulcer presentation"}\n'
        '  ],\n'
        '  "reasoning": "Post-prandial retrosternal burning with acid regurgitation and positional worsening is classic for GERD. No alarm features such as dysphagia or weight loss are reported.",\n'
        '  "confidence": 0.88,\n'
        '  "severity": "moderate",\n'
        '  "urgency": "soon",\n'
        '  "findings": [{"finding": "Retrosternal burning aggravated by recumbency", "severity": "medium"}],\n'
        '  "medications": [{"name": "Pantoprazole", "dosage": "40 mg", "frequency": "once daily", "when_to_take": "Every morning 30 minutes before breakfast", "duration": "4 weeks", "type": "tablet", "notes": "Reduces stomach acid. Available as Pantocid, Pan."}],\n'
        '  "lifestyle_recommendations": ["Elevate head of bed", "Avoid eating within 3 hours of bedtime"],\n'
        '  "precautions": ["Seek immediate care if chest pain is crushing or radiates to the arm/jaw"],\n'
        '  "recommended_tests": ["Upper GI endoscopy if symptoms persist beyond 8 weeks"],\n'
        '  "when_to_see_doctor": "If difficulty swallowing, unintentional weight loss, or vomiting blood occurs"\n'
        '}\n'
        "\n"
        'Example 3 — "Patient has dry, flaky, itchy skin on arms and legs, worse in winter, no rash or redness":\n'
        '{\n'
        '  "diagnosis": "Xerosis Cutis",\n'
        '  "differential_diagnoses": [\n'
        '    {"diagnosis": "Atopic Dermatitis", "confidence": 0.20, "reasoning": "Chronic pruritus with dry skin can indicate eczema"},\n'
        '    {"diagnosis": "Psoriasis", "confidence": 0.10, "reasoning": "Scaling skin on extremities warrants exclusion of psoriasis"}\n'
        '  ],\n'
        '  "reasoning": "Bilateral dry, flaky, pruritic skin on the extremities with seasonal worsening in winter and absence of erythema or distinct rash points to simple xerosis (dry skin) rather than an inflammatory dermatosis.",\n'
        '  "confidence": 0.82,\n'
        '  "severity": "mild",\n'
        '  "urgency": "routine",\n'
        '  "findings": [{"finding": "Diffuse xerosis on bilateral extremities", "severity": "low"}],\n'
        '  "medications": [{"name": "Urea 10% cream", "dosage": "Apply thin layer", "frequency": "twice daily", "when_to_take": "After morning bath and before bed", "duration": "ongoing", "type": "cream", "notes": "Emollient for dry skin. Available as Moisturex, Xerina."}],\n'
        '  "lifestyle_recommendations": ["Use lukewarm water for bathing", "Apply moisturiser within 3 minutes of bathing"],\n'
        '  "precautions": ["Avoid harsh soaps and hot showers"],\n'
        '  "recommended_tests": ["Thyroid function tests if dryness is refractory"],\n'
        '  "when_to_see_doctor": "If skin develops cracks, bleeding, or signs of infection"\n'
        '}'
    )


def _build_user_message(
    symptoms: str,
    clinical_notes: str = "",
    medical_history: dict | None = None,
    include_knowledge_brain: bool = True,
) -> str:
    parts = [f"Patient Symptoms: {symptoms}"]

    if clinical_notes:
        parts.append(f"Clinical Notes: {clinical_notes}")

    if medical_history:
        gender = medical_history.get("gender", "Not specified")
        dob = medical_history.get("date_of_birth", "Unknown")
        blood = medical_history.get("blood_group", "Unknown")
        allergies = medical_history.get("allergies", "None reported")

        if gender and gender != "Not specified":
            parts.append(f"Gender: {gender}")
        if dob and dob != "Unknown":
            parts.append(f"Date of Birth: {dob}")
        if blood and blood != "Unknown":
            parts.append(f"Blood Group: {blood}")
        if allergies and allergies != "None reported":
            parts.append(f"Known Allergies: {allergies}")

        # Vitals from BP machine, oximeter, thermometer, glucometer, ECG, etc.
        vitals = medical_history.get("vitals") or {}
        if vitals:
            vitals_parts = []
            if vitals.get("systolic_bp") is not None and vitals.get("diastolic_bp") is not None:
                vitals_parts.append(f"BP: {vitals['systolic_bp']}/{vitals['diastolic_bp']} mmHg")
            elif vitals.get("systolic_bp") is not None:
                vitals_parts.append(f"Systolic BP: {vitals['systolic_bp']} mmHg")
            elif vitals.get("diastolic_bp") is not None:
                vitals_parts.append(f"Diastolic BP: {vitals['diastolic_bp']} mmHg")
            if vitals.get("spo2") is not None:
                vitals_parts.append(f"SpO2: {vitals['spo2']}%")
            if vitals.get("heart_rate") is not None:
                vitals_parts.append(f"Heart rate: {vitals['heart_rate']} bpm")
            if vitals.get("temperature_f") is not None:
                vitals_parts.append(f"Temperature: {vitals['temperature_f']}°F")
            if vitals.get("respiratory_rate") is not None:
                vitals_parts.append(f"Respiratory rate: {vitals['respiratory_rate']}/min")
            if vitals.get("blood_sugar_mg_dl") is not None:
                vitals_parts.append(f"Blood sugar: {vitals['blood_sugar_mg_dl']} mg/dL")
            if vitals.get("weight_kg") is not None:
                vitals_parts.append(f"Weight: {vitals['weight_kg']} kg")
            if vitals.get("pain_level") is not None:
                vitals_parts.append(f"Pain level: {vitals['pain_level']}/10")
            if vitals.get("ecg_notes"):
                vitals_parts.append(f"ECG interpretation: {vitals['ecg_notes']}")
            if vitals_parts:
                parts.append("Vital signs (from patient's devices): " + "; ".join(vitals_parts))

        # Prior context: previous diagnoses, fitness vitals, symptom history
        prior = medical_history.get("prior_context")
        if prior and isinstance(prior, str):
            parts.append(prior)

    # MedGemma brain uses AI only; books brain is separate (disease_knowledge_brain)
    if include_knowledge_brain:
        try:
            from app.services.disease_knowledge_brain import get_relevant_context
            context = get_relevant_context(symptoms, max_chars=1800, top_k=3)
            if context:
                parts.append(context)
        except Exception as exc:
            logger.debug("Knowledge brain skipped: %s", exc)

    return "\n".join(parts)


def _extract_json(text: str) -> dict | None:
    """Try to pull a JSON object from the model's response text."""
    # Strip markdown fences if the model wrapped its answer
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.strip().rstrip("`")

    # First attempt: direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Second attempt: find the first { ... } block
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def _normalise_extracted_lab_values(raw: list | None) -> list:
    """Normalise extracted lab values from model output."""
    if not raw or not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if isinstance(item, dict):
            out.append({
                "test": str(item.get("test", "")),
                "value": str(item.get("value", "")),
                "unit": str(item.get("unit", "")),
                "reference": str(item.get("reference", "")),
                "status": str(item.get("status", "normal")).lower(),
            })
    return out


def _clamp_confidence(val) -> float:
    try:
        f = float(val)
        return max(0.0, min(1.0, f))
    except (TypeError, ValueError):
        return 0.7


_VALID_SEVERITIES = {"mild", "moderate", "severe", "critical"}
_VALID_URGENCIES = {"routine", "soon", "urgent", "emergency"}


def _normalise_result(raw: dict) -> dict:
    """Ensure every expected key exists and has the right type."""
    severity = str(raw.get("severity", "moderate")).lower()
    if severity not in _VALID_SEVERITIES:
        severity = "moderate"

    urgency = str(raw.get("urgency", "soon")).lower()
    if urgency not in _VALID_URGENCIES:
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
            medications.append({
                "name": m, "dosage": "", "frequency": "", "when_to_take": "",
                "duration": "", "type": "tablet", "notes": "",
            })

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
            differential_diagnoses.append({
                "diagnosis": d, "confidence": 0.0, "reasoning": "",
            })

    return {
        "diagnosis": str(raw.get("diagnosis", "Analysis pending")),
        "layman_summary": str(raw.get("layman_summary", "")),
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
        "model_version": MODEL_VERSION,
        "medical_history_considered": True,
        "allergy_warnings": None,
        "extracted_lab_values": _normalise_extracted_lab_values(raw.get("extracted_lab_values")),
    }


def _enrich_with_app_plans(result: dict) -> dict:
    """Add dietary plan, routine plan and ayurvedic medicines from
    the app's built-in lookup tables (MedGemma doesn't know about these)."""
    from app.services.dietary_routine_plans import get_dietary_plan, get_routine_plan
    from app.services.ayurvedic_medicines import get_ayurvedic_medicines

    diagnosis_name = result.get("diagnosis", "")
    result["dietary_plan"] = get_dietary_plan(diagnosis_name)
    result["routine_plan"] = get_routine_plan(diagnosis_name)
    result["ayurvedic_medicines"] = get_ayurvedic_medicines(diagnosis_name)
    return result


OLLAMA_MAX_RETRIES = 3


async def _call_ollama(
    symptoms: str,
    clinical_notes: str,
    medical_history: dict | None,
    image_data_urls: list[str] | None = None,
    file_hints: list[tuple[str, str]] | None = None,
    use_27b: bool = False,
    timeout: float = 180.0,
) -> dict:
    """Call Ollama chat endpoint and return normalised result dict.
    Retries on timeout, connection error, or 503 (queue full) with exponential backoff.
    When image_data_urls is provided, uses the multimodal model and attaches images.
    """
    settings = get_settings()
    has_images = bool(image_data_urls)

    # Model selection: 27B for text-only (higher accuracy); multimodal for images
    if has_images:
        model = settings.OLLAMA_MULTIMODAL_MODEL
    elif use_27b:
        model = settings.OLLAMA_MODEL_27B
    else:
        model = settings.OLLAMA_MODEL

    user_msg = _build_user_message(symptoms, clinical_notes, medical_history, include_knowledge_brain=False)

    content = user_msg
    if has_images:
        modality_instruction = (
            f"The user has attached {len(image_data_urls)} image(s). "
            "Analyze them per the IMAGE_ANALYSIS instructions in the system prompt. "
            "Incorporate radiology findings, extracted lab values, or dermatology observations "
            "into your diagnosis, reasoning, and findings."
        )
        content = f"{user_msg}\n\n[{modality_instruction}]"

    user_message: dict = {"role": "user", "content": content}
    if image_data_urls:
        user_message["images"] = image_data_urls

    system_prompt = _get_system_prompt(file_hints=file_hints, has_images=has_images)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            user_message,
        ],
        "stream": False,
        "options": {"temperature": 0.1, "top_p": 0.9, "num_predict": 2048},
    }
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    last_err = None

    for attempt in range(OLLAMA_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            body = resp.json()
            content = body.get("message", {}).get("content", "")
            parsed = _extract_json(content)
            if parsed is None:
                logger.warning("MedGemma returned non-JSON response, raw=%s", content[:500])
                raise ValueError("Model did not return valid JSON")
            return _normalise_result(parsed)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_err = e
            if attempt < OLLAMA_MAX_RETRIES - 1:
                delay = 2 ** attempt
                logger.debug("Ollama timeout/connect error, retry in %ds: %s", delay, e)
                await asyncio.sleep(delay)
            else:
                raise
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503 and attempt < OLLAMA_MAX_RETRIES - 1:
                last_err = e
                delay = 2 ** attempt
                logger.debug("Ollama 503 (queue full), retry in %ds", delay)
                await asyncio.sleep(delay)
            else:
                raise
    raise last_err


async def diagnose(
    symptoms: str,
    clinical_notes: str = "",
    medical_history: dict | None = None,
    image_data_urls: list[str] | None = None,
    file_hints: list[tuple[str, str]] | None = None,
    use_27b: bool = False,
) -> dict:
    """Primary diagnosis entry point.

    Tries MedGemma via Ollama; falls back to the mock engine on failure.
    When image_data_urls is provided, uses the vision-capable model to analyze
    lab reports, X-rays, skin photos, etc. use_27b selects the 27B model for
    higher accuracy (text-only).
    """
    try:
        result = await _call_ollama(
            symptoms,
            clinical_notes,
            medical_history,
            image_data_urls=image_data_urls,
            file_hints=file_hints,
            use_27b=use_27b,
        )
        result["medical_history_considered"] = bool(medical_history)
        logger.info("MedGemma diagnosis: %s (confidence %.2f)", result["diagnosis"], result["confidence"])

    except Exception as exc:
        logger.warning("MedGemma unavailable (%s), falling back to mock engine", exc)
        from app.services.mock_diagnosis import diagnose as mock_diagnose
        result = mock_diagnose(symptoms, clinical_notes, medical_history)
        return result

    return _enrich_with_app_plans(result)
