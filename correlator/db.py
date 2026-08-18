from __future__ import annotations

import os
from datetime import datetime, timezone

import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://causeway:causeway@postgres:5432/causeway",
).replace("postgresql+asyncpg://", "postgresql://")

STUB_SNAPSHOT = "snap_stub_v1"

async def connect() -> asyncpg.Connection:
    return await asyncpg.connect(DATABASE_URL)


async def ensure_stub_snapshot(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        INSERT INTO topology_snapshot (snapshot_id, taken_at, node_count, edge_count, body)
        VALUES ($1, now(), 0, 0, '\x00'::bytea)
        ON CONFLICT (snapshot_id) DO NOTHING
        """,
        STUB_SNAPSHOT,
    )

async def upsert_signal(conn: asyncpg.Connection, s: dict) -> None:
    await conn.execute(
        """
        INSERT INTO signal (
        signal_id, kind, node_id, severity, onset_at, observed_at, fingerprint, payload
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
        ON CONFLICT (signal_id) DO NOTHING
        """,
        s["signal_id"],
        s["kind"],
        s["node_id"],
        float(s["severity"]),
        datetime.fromisoformat(s["onset_at"].replace("Z", "+00:00")),
        datetime.fromisoformat(s["observed_at"].replace("Z", "+00:00")),
        s.get("fingerprint"),
        __import__("json").dumps(s.get("payload") or {}),

    )

async def create_incident(
    conn: asyncpg.Connection,
    incident_id: str,
    win_start: datetime,
    win_end: datetime,
    signal_ids: list[str],
) -> None:
    await ensure_stub_snapshot(conn)
    await conn.execute(
      """
      INSERT INTO incident (
        incident_id, win, snapshot_id, signal_count, status
      ) VALUES (
        $1,
        tstzrange($2::timestamptz, $3::timestamptz, '[)'),
        $4,
        $5,
        'open'
      )
      ON CONFLICT (incident_id) DO NOTHING
      """,
    incident_id,
    win_start,
    win_end,
    STUB_SNAPSHOT,
    len(signal_ids),
    )
    for sid in signal_ids:
        await conn.execute(
            """
            INSERT INTO incident_signal (incident_id, signal_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            incident_id,
            sid,
        )