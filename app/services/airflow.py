import httpx
from datetime import datetime, timezone
from app.core.config import get_settings

settings = get_settings()


async def trigger_diagnosis_dag(batch_id: int, priority: str = "normal") -> dict:
    """Trigger the Airflow diagnosis_pipeline DAG for a batch."""
    dag_id = "diagnosis_pipeline"
    run_id = f"batch_{batch_id}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.AIRFLOW_API_URL}/dags/{dag_id}/dagRuns",
            json={
                "dag_run_id": run_id,
                "conf": {
                    "batch_id": batch_id,
                    "priority": priority,
                },
            },
            auth=(settings.AIRFLOW_USERNAME, settings.AIRFLOW_PASSWORD),
            timeout=30.0,
        )

    if resp.status_code not in (200, 201):
        raise Exception(f"Airflow trigger failed: {resp.status_code} {resp.text}")

    return {"dag_run_id": run_id, "status": "triggered"}


async def get_dag_run_status(dag_run_id: str) -> dict:
    dag_id = "diagnosis_pipeline"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.AIRFLOW_API_URL}/dags/{dag_id}/dagRuns/{dag_run_id}",
            auth=(settings.AIRFLOW_USERNAME, settings.AIRFLOW_PASSWORD),
            timeout=15.0,
        )

    if resp.status_code != 200:
        return {"state": "unknown", "error": resp.text}

    data = resp.json()
    return {"state": data.get("state"), "start_date": data.get("start_date"), "end_date": data.get("end_date")}
