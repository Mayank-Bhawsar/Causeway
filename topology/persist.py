from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg

from topology.servicegraph import fetch_edges

async def refresh_topology(conn: asyncpg.Connection) -> str | None:
    """Fetch edges from VM, write edge_observation + topology_snapshot. Returns snapshot_id."""
    edges = await fetch_edges()
    if not edges:
        print("topology: no edges from VM", flush=True)
        return None

    now = datetime.now(timezone.utc)
    bucket_start = now - timedelta(minutes=2)
    total_calls = sum(e["calls"] for e in edges) or 1


    for e in edges:
        share = e["calls"] / total_calls
        await conn.execute(
            """
            INSERT INTO edge_observation (
            src, dst, rel, bucket, calls, errors,
            p50_ms, p95_ms, call_share, lat_share, err_share
            ) VALUES (
            $1, $2, $3,
            tstzrange($4::timestamptz, $5::timestamptz, '[)'),
            $6, 0, NULL, NULL, $7, $7, 0.0
            )
            ON CONFLICT (src, dst, rel, bucket) DO UPDATE
            SET calls = EXCLUDED.calls,
                call_share = EXCLUDED.call_share,
                lat_share = EXCLUDED.lat_share
            """,
            e["src"],
            e["sdt"],
            e["rel"],
            bucket_start,
            now,
            e["calls"],
            share,
        )

    nodes = sorted({e["src"] for e in edges} | {e["dst"] for e in edges})
    body = json.dumps({"nodes": nodes, "edges": edges}).encode()
    snap_id = f"snap_{uuid.uuid4().hex[:12]}"
    await conn.execute(
        """
        INSERT INTO topology_snapshot (snapshot_id, taken_at, node_count, edge_count, body)
        VALUES ($1, $2, $3, $4, $5)
        """,
        snap_id,
        now,
        len(nodes),
        len(edges),
        body,
    )
    print(
        f"topology: snapshot={snap_id} nodes={len(nodes)} edges={len(edges)}",
        flush=True,
    )
    return snap_id