#!/usr/bin/env python3
"""Wait for an alert signal on signals.alerts (verify-alerts-live)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys


async def wait_for_alert(timeout_sec: int, expect: str) -> int:
    from aiokafka import AIOKafkaConsumer

    bootstrap = os.getenv("KAFKA_BOOTSTRAP", "redpanda:9092")
    consumer = AIOKafkaConsumer(
        "signals.alerts",
        bootstrap_servers=bootstrap,
        group_id=f"verify-alerts-live-{os.getpid()}",
        auto_offset_reset="latest",
        consumer_timeout_ms=2000,
    )
    await consumer.start()
    try:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_sec
        while loop.time() < deadline:
            try:
                msg = await asyncio.wait_for(consumer.getone(), timeout=5.0)
            except asyncio.TimeoutError:
                continue
            body = json.loads(msg.value.decode())
            payload = body.get("payload") or {}
            alertname = str(payload.get("alertname") or "")
            node_id = str(body.get("node_id") or "")
            haystack = f"{alertname} {node_id} {json.dumps(payload)}".lower()
            if expect.lower() in haystack:
                print(
                    json.dumps(
                        {
                            "ok": True,
                            "signal_id": body.get("signal_id"),
                            "kind": body.get("kind"),
                            "node_id": node_id,
                            "alertname": alertname,
                        }
                    )
                )
                return 0
        print(f"timeout: no alert matching {expect!r} within {timeout_sec}s", file=sys.stderr)
        return 1
    finally:
        await consumer.stop()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--expect", default="payment")
    args = p.parse_args()
    return asyncio.run(wait_for_alert(args.timeout, args.expect))


if __name__ == "__main__":
    sys.exit(main())
