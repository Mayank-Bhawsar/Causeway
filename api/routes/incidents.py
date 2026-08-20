import os
import asyncpg
from fastapi import APIRouter
from narrator.openai_narrator import narrate

router = APIRouter(prefix="/api/v1", tags=["incidents"])

def _dsn() -> str:
    return os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql://causeway:causeway@postgres:5432/causeway"
    ).replace("postgresql+asyncpg://", "postgresql://")


@router.get("/incidents")
async def list_incidents() -> dict:
    conn = await asyncpg.connect(_dsn())
    try:
        rows = await conn.fetch(
            """
            SELECT incident_id, signal_count, status, lower(win) AS win_start,
                    upper(win) AS win_end, created_at
            FROM incident
            ORDER BY created_at DESC
            LIMIT 20
            """
        )
        return {"incidents": [dict(r) for r in rows]}
    finally:
        await conn.close()


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str) -> dict:
    conn = await asyncpg.connect(_dsn())
    try:
        inc = await conn.fetchrow(
            "SELECT * FROM incident WHERE incident_id = $1", incident_id
        )
        if not inc:
            return {"error": "not found"}
        signals = await conn.fetch(
            """
            SELECT s.signal_id, s.kind, s.node_id, s.severity, s.onset_at, s.payload
            FROM incident_signal i
            JOIN signal s ON s.signal_id = i.signal_id
            WHERE i.incident_id = $1
            ORDER BY s.onset_at
            """,
            incident_id,
        )
        return {"incident": dict(inc), "signals": [dict(s) for s in signals]}
    finally:
        await conn.close()


@router.get("/incidents/{incident_id}/candidates")
async def get_candidates(incident_id: str) -> dict:
    conn = await asyncpg.connect(_dsn())
    try:
        rows =await conn.fetch(
            """
            SELECT node_id, rank, score, confidence, conformal_k, features
            FROM cause_candidate
            WHERE incident_id = $1
            ORDER BY rank
            """,
            incident_id,
        )
        if not rows:
            return {"incident_id": incident_id, "candidate": []}
        return {
            "incident_id": incident_id,
            "candidates": [dict(r) for r in rows],
        }
    finally:
        await conn.close()


@router.post("/incidents/{incident_id}/narrate")
async def narrate_incident(incident_id: str) -> dict:
    if not os.getenv("OPENAI_API_KEY"):
        return {
            "error": "OPENAI_API_KEY not set - narrative deferred",
            "incident_id": incident_id,
        }
    conn = await asyncpg.connect(_dsn())
    try:
        row = await conn.fetchrow(
            "SELECT pack FROM evidence_pack WHERE incident_id = $1", incident_id
        )
        if not row:
            return {"error": "no evidence pack - run correlator first"}
        body = await narrate(row["pack"])
        await conn.execute(
            """
            INSERT INTO narrative (incident_id, body, provider)
            VALUES ($1, $2::jsonb, 'openai')
            ON CONFLICT (incident_id) DO UPDATE
            SET body = EXCLUDED.body, provider = EXCLUDED.provider
            """,
            incident_id,
            json_dumps(body),
        )
        return {"incident_id": incident_id, "narrative": body}
    finally:
        await conn.close()