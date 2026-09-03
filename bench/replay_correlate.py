"""Replay fixtures through correlator clustering (no DB/Kafka)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from correlator.affinity import pairwise_distance
from correlator.cluster import cluster_signals

FIXTURES = Path(__file__).parent / "fixtures"


def replay_correlate(path: Path) -> dict:
    fx = json.loads(path.read_text())
    signals = fx["signals"]
    edges = fx.get("edges") or []
    expected = int(fx.get("expected_incidents", 1))
    dist = pairwise_distance(signals, edges)
    clusters = cluster_signals(signals, dist)
    return {
        "scenario": fx.get("scenario", path.stem),
        "clusters": len(clusters),
        "expected": expected,
        "ok": len(clusters) == expected,
        "sizes": [len(c) for c in clusters],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--fixtures", type=Path, default=FIXTURES)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    results = []
    for path in sorted(args.fixtures.glob("*.json")):
        results.append(replay_correlate(path))

    report = {"results": results, "n": len(results)}
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    else:
        print(text)

    failures = [r["scenario"] for r in results if not r["ok"]]
    if failures:
        print(f"FAIL cluster count: {failures}", file=sys.stderr)
        sys.exit(1)
    print("OK all fixtures matched expected_incidents", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
