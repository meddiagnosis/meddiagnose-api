from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "MedDiagnose"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    LOG_FORMAT: str = "text"  # "json" for production (CloudWatch, Datadog, ELK)
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql+asyncpg://meddiagnose:meddiagnose@localhost:5432/meddiagnose"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://meddiagnose:meddiagnose@localhost:5432/meddiagnose"
    REDIS_URL: str = "redis://localhost:6379/0"
    # Force Redis for rate limiter even when DEBUG=true (set true in staging/production)
    USE_REDIS_FOR_LIMITER: bool = False

    SECRET_KEY: str = "CHANGE-THIS-TO-A-RANDOM-SECRET-KEY-IN-PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    STORAGE_BACKEND: str = "local"

    GCP_PROJECT_ID: Optional[str] = None
    GCS_BUCKET: Optional[str] = None
    VERTEX_AI_LOCATION: str = "us-central1"
    MEDGEMMA_ENDPOINT_4B: Optional[str] = None
    MEDGEMMA_ENDPOINT_27B: Optional[str] = None

    INFERENCE_WORKER_URL: str = "http://localhost:8001"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "alibayram/medgemma:4b"
    # Vision-capable model for image-based diagnosis (X-rays, skin, lab reports).
    # Use when images are uploaded; falls back to OLLAMA_MODEL for text-only.
    OLLAMA_MULTIMODAL_MODEL: str = "dcarrascosa/medgemma-1.5-4b-it"
    # 27B model for higher accuracy (requires more GPU/RAM)
    OLLAMA_MODEL_27B: str = "alibayram/medgemma:27b"
    # Ollama server-side: OLLAMA_MAX_QUEUE (default 512) limits pending requests.
    # For heavy concurrency, ensure Ollama is started with adequate queue: e.g.
    # OLLAMA_MAX_QUEUE=64 ollama serve

    AIRFLOW_API_URL: str = "http://localhost:8080/api/v1"
    AIRFLOW_USERNAME: str = "airflow"
    AIRFLOW_PASSWORD: str = "airflow"

    # Kafka for parallel bulk diagnosis processing
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_DIAGNOSIS_TOPIC: str = "meddiagnose-diagnosis-jobs"
    KAFKA_ENABLED: bool = False
    KAFKA_USE_VERTEX_AI: bool = False  # Use GCP Vertex AI instead of Ollama for bulk inference

    # Wearable integrations
    FITBIT_CLIENT_ID: Optional[str] = None
    FITBIT_CLIENT_SECRET: Optional[str] = None
    FITBIT_REDIRECT_URI: str = "http://localhost:8000/api/v1/wearables/callback/fitbit"

    GOOGLE_FIT_CLIENT_ID: Optional[str] = None
    GOOGLE_FIT_CLIENT_SECRET: Optional[str] = None
    GOOGLE_FIT_REDIRECT_URI: str = "http://localhost:8000/api/v1/wearables/callback/google_fit"

    CORS_ORIGINS: list[str] = [
    "http://localhost:3000", "http://localhost:4173", "http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:8081",
    "http://127.0.0.1:3000", "http://127.0.0.1:4173", "http://127.0.0.1:5173", "http://127.0.0.1:5174", "http://127.0.0.1:5175", "http://127.0.0.1:8081",
]

    # SSO (Google OAuth2)
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = None
    GOOGLE_OAUTH_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:5173"  # For SSO redirect after login

    # Keycloak OIDC (supports 3 clients: admin, doctor, patient)
    KEYCLOAK_URL: Optional[str] = None  # e.g. https://keycloak.example.com
    KEYCLOAK_REALM: Optional[str] = None  # e.g. meddiagnose
    KEYCLOAK_CLIENT_ID: Optional[str] = None  # default client (patient)
    KEYCLOAK_CLIENT_SECRET: Optional[str] = None
    KEYCLOAK_ADMIN_CLIENT_ID: str = "meddiagnose-admin"
    KEYCLOAK_ADMIN_CLIENT_SECRET: str = "meddiagnose-admin-secret"
    KEYCLOAK_DOCTOR_CLIENT_ID: str = "meddiagnose-doctor"
    KEYCLOAK_DOCTOR_CLIENT_SECRET: str = "meddiagnose-doctor-secret"
    KEYCLOAK_PATIENT_CLIENT_ID: str = "meddiagnose-patient"
    KEYCLOAK_PATIENT_CLIENT_SECRET: str = "meddiagnose-patient-secret"
    KEYCLOAK_REDIRECT_URI: str = "http://localhost:8001/api/v1/auth/keycloak/callback"

    # Diagnosis brain: "books" = knowledge graph only, "medgemma" = MedGemma AI only
    DIAGNOSIS_BRAIN: str = "medgemma"

    # Region for medication availability (India = prescribe drugs available in Indian pharmacies)
    REGION: str = "India"

    # Insurance integrations (ABDM/NHCX for government; insurer APIs for private)
    ABDM_CLIENT_ID: Optional[str] = None
    ABDM_CLIENT_SECRET: Optional[str] = None
    ABDM_BASE_URL: str = "https://sbxhcx.abdm.gov.in"  # Sandbox; prod: https://hcx.abdm.gov.in
    ABDM_AUTH_URL: Optional[str] = None  # Override if auth is at different URL (e.g. dev.abdm.gov.in/gateway/v0.5/sessions)
    # Callback URL for NHCX responses (must be public, set during NHCX registration)
    NHCX_CALLBACK_URL: Optional[str] = None  # e.g. https://yourdomain.com/api/v1/insurance/hcx/callback
    STAR_HEALTH_API_URL: Optional[str] = None
    STAR_HEALTH_API_KEY: Optional[str] = None
    HDFC_ERGO_API_URL: Optional[str] = None
    HDFC_ERGO_API_KEY: Optional[str] = None
    MAX_BUPA_API_URL: Optional[str] = None
    MAX_BUPA_API_KEY: Optional[str] = None
    AXIS_HEALTH_API_URL: Optional[str] = None
    AXIS_HEALTH_API_KEY: Optional[str] = None
    LIC_API_URL: Optional[str] = None
    LIC_API_KEY: Optional[str] = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
