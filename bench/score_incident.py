""" Score whether top-1 candidate matches expected root cause."""
from __future__ import annotations

import argparse
import asyncio
import os

import asyncpg


async def main(incident_id: str, expected: str) -> None:
    dsn = os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql://causeway:causeway@localhost:5432/causeway",
    )
    conn = await asyncpg.connect(dsn)
    try:
        row = await conn.fetchrow(
            """
            SELECT node_id, rank, score, features FROM cause_candidate
            WHERE incident_id = $1 ORDER BY rank LIMIT 1
            """,
            incident_id,
        )
        if not row:
            print("FAIL: no candidates")
            return
        top = row["node_id"]
        ok = top == expected
        print(f"incident={incident_id} top1={top} expected={expected} ok={ok}")
        print(f"score={row['score']} features={row['features']}")
    finally:
        await conn.close()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--incident-id", required=True)
    p.add_argument("--expected", default="svc:payment-svc")
    args = p.parse_args()
    asyncio.run(main(args.incident_id, args.expected))