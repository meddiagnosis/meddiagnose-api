"""
Dedicated GPU inference service for MedGemma AI diagnosis.

Runs as a separate process/container with GPU access. The main API
dispatches inference requests here via Celery or direct HTTP.
"""

import os
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("inference_worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

_model = None
_tokenizer = None


def _load_model():
    """Load MedGemma model onto GPU. Falls back to mock if no GPU or model unavailable."""
    global _model, _tokenizer

    model_id = os.getenv("MEDGEMMA_MODEL_ID", "google/medgemma-4b-it")
    use_gpu = os.getenv("USE_GPU", "true").lower() == "true"

    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM

        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        logger.info(f"Loading model {model_id} on {device}...")

        _tokenizer = AutoTokenizer.from_pretrained(model_id)
        load_kwargs = {"torch_dtype": torch.float16, "device_map": "auto"}
        if device == "cuda":
            load_kwargs["load_in_4bit"] = True
        _model = AutoModelForCausalLM.from_pretrained(model_id, **load_kwargs)
        logger.info(f"Model loaded successfully on {device}")
    except Exception as e:
        logger.warning(f"Could not load GPU model: {e}. Using mock inference.")
        _model = None
        _tokenizer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_model()
    yield


app = FastAPI(title="MedDiagnose Inference Worker", lifespan=lifespan)


class InferenceRequest(BaseModel):
    symptoms: str
    clinical_notes: str = ""
    medical_history: dict | None = None
    patient_age: int | None = None
    patient_gender: str | None = None


class InferenceResponse(BaseModel):
    diagnosis: str
    reasoning: str
    confidence: float
    severity: str
    urgency: str
    medications: list[dict]
    findings: list[dict]
    lifestyle_recommendations: list[str]
    precautions: list[str]
    recommended_tests: list[str]
    when_to_see_doctor: str
    model_version: str
    inference_time_ms: float


@app.post("/infer", response_model=InferenceResponse)
async def infer(req: InferenceRequest):
    start = time.time()

    if _model is not None and _tokenizer is not None:
        result = _gpu_inference(req)
    else:
        result = _mock_inference(req)

    result["inference_time_ms"] = round((time.time() - start) * 1000, 2)
    return InferenceResponse(**result)


def _gpu_inference(req: InferenceRequest) -> dict:
    """Run actual MedGemma inference on GPU."""
    import torch

    prompt = _build_prompt(req)
    inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)

    with torch.no_grad():
        outputs = _model.generate(
            **inputs,
            max_new_tokens=2048,
            temperature=0.3,
            top_p=0.9,
            do_sample=True,
        )

    response_text = _tokenizer.decode(outputs[0], skip_special_tokens=True)
    return _parse_model_response(response_text, req)


def _build_prompt(req: InferenceRequest) -> str:
    history_str = ""
    if req.medical_history:
        parts = []
        for k, v in req.medical_history.items():
            if v and v not in ("Unknown", "None reported", "Not specified"):
                parts.append(f"{k}: {v}")
        if parts:
            history_str = f"\nMedical History: {', '.join(parts)}"

    return f"""You are MedGemma, a medical AI assistant. Analyze the following patient case and provide a structured diagnosis.

Patient Symptoms: {req.symptoms}
Clinical Notes: {req.clinical_notes or 'None'}
Patient Age: {req.patient_age or 'Unknown'}
Patient Gender: {req.patient_gender or 'Unknown'}{history_str}

Provide your response in the following structured format:
DIAGNOSIS: [primary diagnosis]
CONFIDENCE: [0.0-1.0]
SEVERITY: [mild/moderate/severe/critical]
URGENCY: [routine/soon/urgent/emergency]
REASONING: [detailed clinical reasoning]
FINDINGS: [key clinical findings, one per line]
MEDICATIONS: [recommended medications with dosage, one per line]
LIFESTYLE: [lifestyle recommendations, one per line]
PRECAUTIONS: [precautions and warnings, one per line]
TESTS: [recommended diagnostic tests, one per line]
WHEN_TO_SEE_DOCTOR: [guidance on when professional consultation is needed]"""


def _parse_model_response(text: str, req: InferenceRequest) -> dict:
    """Parse structured response from the model. Falls back gracefully."""
    lines = text.strip().split("\n")
    result = {
        "diagnosis": "Analysis pending",
        "reasoning": "",
        "confidence": 0.7,
        "severity": "moderate",
        "urgency": "soon",
        "medications": [],
        "findings": [],
        "lifestyle_recommendations": [],
        "precautions": [],
        "recommended_tests": [],
        "when_to_see_doctor": "Consult a healthcare professional for proper evaluation.",
        "model_version": "medgemma-4b-gpu-v1",
    }

    current_section = None
    for line in lines:
        line = line.strip()
        if line.startswith("DIAGNOSIS:"):
            result["diagnosis"] = line.split(":", 1)[1].strip()
        elif line.startswith("CONFIDENCE:"):
            try:
                result["confidence"] = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("SEVERITY:"):
            result["severity"] = line.split(":", 1)[1].strip().lower()
        elif line.startswith("URGENCY:"):
            result["urgency"] = line.split(":", 1)[1].strip().lower()
        elif line.startswith("REASONING:"):
            result["reasoning"] = line.split(":", 1)[1].strip()
            current_section = "reasoning"
        elif line.startswith("FINDINGS:"):
            current_section = "findings"
            content = line.split(":", 1)[1].strip()
            if content:
                result["findings"].append({"finding": content, "severity": "medium"})
        elif line.startswith("MEDICATIONS:"):
            current_section = "medications"
        elif line.startswith("LIFESTYLE:"):
            current_section = "lifestyle"
        elif line.startswith("PRECAUTIONS:"):
            current_section = "precautions"
        elif line.startswith("TESTS:"):
            current_section = "tests"
        elif line.startswith("WHEN_TO_SEE_DOCTOR:"):
            result["when_to_see_doctor"] = line.split(":", 1)[1].strip()
            current_section = None
        elif line and current_section:
            line_clean = line.lstrip("- •")
            if current_section == "reasoning":
                result["reasoning"] += " " + line_clean
            elif current_section == "findings":
                result["findings"].append({"finding": line_clean, "severity": "medium"})
            elif current_section == "medications":
                result["medications"].append({"name": line_clean, "dosage": "", "frequency": "", "duration": "", "type": "tablet", "notes": ""})
            elif current_section == "lifestyle":
                result["lifestyle_recommendations"].append(line_clean)
            elif current_section == "precautions":
                result["precautions"].append(line_clean)
            elif current_section == "tests":
                result["recommended_tests"].append(line_clean)

    return result


def _mock_inference(req: InferenceRequest) -> dict:
    """Fallback mock inference when GPU model is not available."""
    from app.services.mock_diagnosis import diagnose
    return diagnose(req.symptoms, req.clinical_notes, req.medical_history)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "gpu_loaded": _model is not None,
        "model": os.getenv("MEDGEMMA_MODEL_ID", "mock"),
    }
