"""Summarize replay report and optionally assert accuracy floors."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def summarize(report: dict) -> dict:
    rows = report["results"]
    n = len(rows) or 1
    top1 = sum(1 for r in rows if r["top1_ok"])
    top3 = sum(1 for r in rows if r["top3_ok"])
    return {
        "n": len(rows),
        "top1": top1 / n,
        "top3": top3 / n,
        "failures": [r["scenario"] for r in rows if not r["top1_ok"]],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="inp", type=Path, required=True)
    p.add_argument("--assert-top1", type=float, default=None)
    p.add_argument("--assert-top3", type=float, default=None)
    args = p.parse_args()

    report = json.loads(args.inp.read_text())
    summary = summarize(report)
    print(json.dumps(summary, indent=2))

    ok = True
    if args.assert_top1 is not None and summary["top1"] < args.assert_top1:
        print(f"FAIL top1 {summary['top1']:.2f} < {args.assert_top1}", file=sys.stderr)
        ok = False
    if args.assert_top3 is not None and summary["top3"] < args.assert_top3:
        print(f"FAIL top3 {summary['top3']:.2f} < {args.assert_top3}", file=sys.stderr)
        ok = False
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()