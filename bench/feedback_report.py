"""Summarize RCA quality from operator feedback and latest incident predictions."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

import asyncpg


async def collect_rca_metrics(dsn: str) -> dict:
    conn = await asyncpg.connect(dsn)
    try:
        rows = await conn.fetch(
            """
            SELECT f.incident_id, f.actual_root, f.correct_rank, f.submitted_by, f.submitted_at,
                   (
                     SELECT c.node_id FROM cause_candidate c
                     WHERE c.incident_id = f.incident_id
                     ORDER BY c.rank LIMIT 1
                   ) AS predicted_top1
            FROM feedback f
            ORDER BY f.submitted_at DESC
            """
        )
        items = [dict(r) for r in rows]
        n = len(items) or 1
        top1_hits = sum(
            1 for r in items if r.get("predicted_top1") and r["predicted_top1"] == r["actual_root"]
        )
        rank1_hits = sum(1 for r in items if r.get("correct_rank") == 1)
        in_top3 = 0
        for r in items:
            ranks = await conn.fetch(
                """
                SELECT node_id, rank FROM cause_candidate
                WHERE incident_id = $1 AND node_id = $2
                """,
                r["incident_id"],
                r["actual_root"],
            )
            if ranks and ranks[0]["rank"] <= 3:
                in_top3 += 1

        gt = await conn.fetch("SELECT scenario, true_root FROM ground_truth")
        return {
            "feedback_count": len(items),
            "top1_accuracy": top1_hits / n if items else None,
            "rank1_rate": rank1_hits / n if items else None,
            "top3_rate": in_top3 / n if items else None,
            "entries": items,
            "ground_truth_scenarios": [dict(g) for g in gt],
        }
    finally:
        await conn.close()


async def main_async(out_path: str | None) -> int:
    dsn = os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql://causeway:causeway@postgres:5432/causeway",
    ).replace("postgresql+asyncpg://", "postgresql://")
    report = await collect_rca_metrics(dsn)
    text = json.dumps(report, indent=2, default=str)
    if out_path:
        open(out_path, "w", encoding="utf-8").write(text)
    else:
        print(text)
    if report["feedback_count"] == 0:
        print("note: no feedback rows yet — run make demo && make feedback", file=sys.stderr)
    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=str, default=None)
    args = p.parse_args()
    raise SystemExit(asyncio.run(main_async(args.out)))


if __name__ == "__main__":
    main()
