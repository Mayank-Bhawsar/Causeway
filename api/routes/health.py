import os

import asyncpg
from aiokafka.admin import AIOKafkaAdminClient
from fastapi import APIRouter
from httpx import AsyncClient

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict:
    status: dict[str, str] = {}


    #postgres
    try:
        conn = await asyncpg.connect(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            user=os.getenv("POSTGRES_USER", "causeway"),
            password=os.getenv("POSTGRES_PASSWORD", "causeway"),
            database=os.getenv("POSTGRES_DB", "causeway"),

        )
        await conn.fetchval("SELECT 1")
        await conn.close()
        status["postgres"] = "ok"
    except Exception as exc:
        status["postgres"] = f"error: {exc}"

    #kafka / Redpanda
    try:
        bootstrap = os.getenv("KAFKA_BOOTSTRAP", "redpanda:9092")
        admin = AIOKafkaAdminClient(bootstrap_servers=bootstrap)
        await admin.start()
        await admin.list_topics()
        await admin.close()
        status["redpanda"] = "ok"
    except Exception as exc:
        status["redpanda"] = f"error: {exc}"

    #VictoriaMetrics
    try:
        vm = os.getenv("VM_URL", "http://victoria-metrics:8428")
        async with AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{vm}/-/healthy")
            status['victoria-metrics'] = "ok" if r.status_code == 200 else f"error: {r.status_code}"
    except Exception as exc:
        status['victoria-metrics'] = f"error: {exc}"

    overall = "ok" if all(v == "ok" for v in status.values()) else "degraded"
    return {"status": overall, "components": status}