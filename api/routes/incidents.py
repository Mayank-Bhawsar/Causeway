import os
import asyncpg
from fastapi import APIRouter
from narrator.openai_narrator import narrate
from actions.suggest import suggest_action
from narrator.validate import validate_narrative

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
            return {"incident_id": incident_id, "candidates": []}
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
        errs = validate_narrative(row["pack"] if isinstance(row["pack"], dict) else json.loads(row["pack"]), body)
        if errs:
            return {"incident_id": incident_id, "narrative": None, "errors": errs}
        await conn.execute(
            """
            INSERT INTO narrative (incident_id, body, provider)
            VALUES ($1, $2::jsonb, 'openai')
            ON CONFLICT (incident_id) DO UPDATE
            SET body = EXCLUDED.body, provider = EXCLUDED.provider
            """,
            incident_id,
            json.dumps(body),
        )
        return {"incident_id": incident_id, "narrative": body}
    finally:
        await conn.close()


@router.get("/incidents/{incident_id}/graph")
async def get_incident_graph(incident_id: str) -> dict:
    conn = await asyncpg.connect(_dsn())
    try:
        inc = await conn.fetchrow(
            "SELECT incident_id, snapshot_id FROM incident WHERE incident_id = $1",
            incident_id,
        )
        if not inc:
            return {"error": "not found"}

        snap = await conn.fetchrow(
            """
            SELECT snapshot_id, taken_at, node_count, edge_count, body
            FROM topology_snapshot WHERE snapshot_id = $1
            """,
            inc["snapshot_id"],
        )
        body = {}
        if snap and snap["body"]:
            import json
            try:
                body = json.loads(bytes(snap["body"]).decode())
            except Exception:
                body = {}

        cands = await conn.fetch(
            """
            SELECT node_id, rank, score FROM cause_candidate
            WHERE incident_id = $1 ORDER BY rank
            """,
            incident_id,
        )
        return {
            "incident_id": incident_id,
            "snapshot_id": inc["snapshot_id"],
            "nodes": body.get("nodes", []),
            "edges": body.get("edges", []),
            "candidates": [dict(c) for c in cands],
            "taken_at": snap["taken_at"] if snap else None,
        }
    finally:
        await conn.close()


@router.post("/incidents/{incident_id}/feedback")
async def submit_feedback(incident_id: str, body: dict) -> dict:
    conn = await asyncpg.connect(_dsn())
    try:
        top = await conn.fetchrow(
            """
            SELECT node_id, rank FROM cause_candidate
            WHERE incident_id=$1 AND node_id=$2
            """,
            incident_id, body["actual_root"],
        )
        await conn.execute(
            """
            INSERT INTO feedback (incident_id, actual_root, correct_rank, submitted_by)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (incident_id, submitted_by) DO UPDATE
            SET actual_root = EXCLUDED.actual_root,
            correct_rank = EXCLUDED.correct_rank
            """,
            incident_id,
            body["actual_root"],
            top["rank"] if top else None,
            body.get("submitted_by", "local"),
        )
        return {"ok": True, "correct_rank": top["rank"] if top else None}
    finally:
        await conn.close()


@router.get("/incidents/{incident_id}/evidence")
async def get_evidence(incident_id: str) -> dict:
    conn = await asyncpg.connect(_dsn())
    try:
        row = await conn.fetchrow(
            "SELECT pack FROM evidence_pack WHERE incident_id = $1",
            incident_id,
        )
        if not row:
            return {"error": "no evidence pack"}
        return {"incident_id": incident_id, "pack": row["pack"]}
    finally:
        await conn.close()

@router.post("/incidents/{incident_id}/actions")
async def propose_action(incident_id: str) -> dict:
    conn = await asyncpg.connect(_dsn())
    try:
        row = await conn.fetchrow(
            "SELECT pack FROM evidence_pack WHERE incident_id = $1",
            incident_id,
        )
        if not row:
            return {"error": "no evidence pack"}
        pack = row["pack"]
        if isinstance(pack, str):
            pack = json.loads(pack)
        body = await narrate(pack)
        errs = validate_narrative(pack,body)
        suggestion = suggest_action(pack)
        await conn.execute(
            """
            INSERT INTO audit_log (actor, incident_id, action, row_hash)
            VALUES ('causeway', $1, $2::jsonb, $3)
            """,
            incident_id,
            __import__("json").dumps(suggestion),
            b"\x00",
        )
        return {"incident_id": incident_id, "suggested_action": suggestion, "applied": False}
    finally:
        await conn.close()