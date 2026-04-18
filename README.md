# meddiagnose-api

FastAPI backend service for the MedDiagnose platform -- AI-powered medical diagnosis with MedGemma.

## Tech Stack

- **Framework**: FastAPI + Uvicorn (async)
- **Database**: PostgreSQL (asyncpg) + SQLAlchemy 2.0 + Alembic migrations
- **Cache / Broker**: Redis (caching, rate limiting, Celery broker)
- **AI Inference**: MedGemma via Ollama (local) or Google Vertex AI (cloud)
- **Task Queue**: Celery (notifications, background jobs) + Kafka (bulk diagnosis)
- **Auth**: JWT with RBAC (patient, doctor, reviewer, admin) + Keycloak SSO + Google OAuth

## Quick Start

```bash
# 1. Create virtualenv
python -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env   # Edit with your DB, Redis, and AI settings

# 4. Run database migrations
alembic upgrade head

# 5. Start the server
uvicorn app.main:app --reload --port 8000
```

## With Docker

```bash
# Uses docker-compose from meddiagnose-infra repo
docker compose up -d
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login (JWT) |
| POST | `/api/v1/auth/google/login` | Google OAuth SSO |
| POST | `/api/v1/auth/keycloak/login` | Keycloak SSO |
| GET | `/api/v1/patients` | List patients |
| POST | `/api/v1/patients` | Create patient |
| POST | `/api/v1/diagnoses/analyze` | Upload reports + symptoms, get AI diagnosis |
| GET | `/api/v1/diagnoses` | List diagnoses |
| PUT | `/api/v1/diagnoses/{id}/review` | Doctor reviews diagnosis |
| POST | `/api/v1/batches/upload` | Upload batch CSV/XLSX |
| POST | `/api/v1/uploads` | Upload medical files |
| GET | `/api/v1/medications/search` | Medication lookup |
| GET | `/api/v1/pharmacies/nearby` | Nearby pharmacies |
| POST | `/api/v1/insurance/policies` | Add insurance policy |
| POST | `/api/v1/insurance/claims` | File insurance claim |
| GET | `/api/v1/fitness` | Fitness tracker data |
| GET | `/api/v1/health-tracker` | Health metrics |
| GET | `/api/v1/wearables` | Wearable integrations (Fitbit, Google Fit) |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

## Project Structure

```
app/
  api/          # Route handlers (auth, diagnoses, patients, insurance, ...)
  core/         # Config, database, security, caching, storage
  models/       # SQLAlchemy ORM models
  schemas/      # Pydantic request/response schemas
  services/     # Business logic (MedGemma, knowledge graph, drug interactions, ...)
  tasks/        # Celery tasks (inference, notifications)
  workers/      # Kafka consumers
alembic/        # Database migrations
scripts/        # Utility scripts (knowledge graph, data download, seeding)
tests/          # Regression tests, accuracy tests
data/           # Sample patient data (synthetic + MIMIC-IV)
```

## Key Services

- **medgemma_diagnosis** -- Primary AI diagnosis via Ollama (local MedGemma 4B/27B)
- **vertex_ai_diagnosis** -- Cloud-based MedGemma via GCP Vertex AI
- **disease_knowledge_brain** -- RAG retrieval from medical knowledge base
- **prescription_safety** -- Drug interaction checks, allergy warnings, dosage adjustment
- **insurance_service** -- Insurance policy management and claims via ABDM/NHCX

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `SECRET_KEY` | JWT signing key |
| `OLLAMA_BASE_URL` | Ollama server URL (default: `http://localhost:11434`) |
| `OLLAMA_MODEL` | MedGemma model name (default: `alibayram/medgemma:4b`) |
| `GCP_PROJECT_ID` | Google Cloud project for Vertex AI |
| `KAFKA_ENABLED` | Enable Kafka for bulk processing |
| `DIAGNOSIS_BRAIN` | `medgemma` (AI) or `books` (knowledge graph only) |

## Testing

```bash
# Unit / regression tests
python -m pytest tests/ -v

# Knowledge graph + MedGemma integration test
python -m pytest tests/test_knowledge_graph_medgemma.py -v

# Accuracy regression test (requires Ollama running)
python -m pytest tests/test_diagnosis_regression.py -v
```

## Related Repos

- [meddiagnose-ml](https://github.com/AngadBindra46/meddiagnose-ml) -- ML inference library
- [meddiagnose-knowledge](https://github.com/AngadBindra46/meddiagnose-knowledge) -- Disease knowledge base
- [meddiagnose-infra](https://github.com/AngadBindra46/meddiagnose-infra) -- Docker/K8s deployment
- [meddiagnose-monitoring](https://github.com/AngadBindra46/meddiagnose-monitoring) -- Prometheus/Grafana
- [meddiagnose-web](https://github.com/AngadBindra46/meddiagnose-web) -- Web dashboard
- [meddiagnose-mobile](https://github.com/AngadBindra46/meddiagnose-mobile) -- Mobile app
- [meddiagnose-airflow](https://github.com/AngadBindra46/meddiagnose-airflow) -- Batch pipelines
