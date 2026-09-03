"""Replay frozen fixtures through the localiser (no DB/Kafka)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from localiser.blame import rank_by_blame
from localiser.rank import rank_by_severity

FIXTURES = Path(__file__).parent / "fixtures"


def replay_fixture(path: Path) -> dict:
    fx = json.loads(path.read_text())
    signals = fx["signals"]
    edges = fx.get("edges") or []
    true_root = fx["true_root"]
    # Multi-incident fixtures are scored by replay_correlate, not top-1 ranking.
    if int(fx.get("expected_incidents", 1)) != 1:
        return {
            "scenario": fx.get("scenario", path.stem),
            "true_root": true_root,
            "top1": None,
            "top3": [],
            "method": None,
            "top1_ok": True,
            "top3_ok": True,
            "signal_count": len(signals),
            "skipped_rank": True,
        }

    cands = rank_by_blame(signals, edges) or rank_by_severity(signals)
    ranked = [c["node_id"] for c in cands]
    top1 = ranked[0] if ranked else None

    return {
        "scenario": fx.get("scenario", path.stem),
        "true_root": true_root,
        "top1": top1,
        "top3": ranked[:3],
        "method": (cands[0]["features"].get("method") if cands else None),
        "top1_ok": top1 == true_root,
        "top3_ok": true_root in ranked[:3],
        "signal_count": len(signals),
        "skipped_rank": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--fixtures", type=Path, default=FIXTURES)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    results = []
    for path in sorted(args.fixtures.glob("*.json")):
        results.append(replay_fixture(path))

    report = {"results": results, "n": len(results)}
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text)
    else:
        print(text)


if __name__ == "__main__":
    main()