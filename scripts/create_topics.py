#!/usr/bin/env python3
"""Create Kafka topics for Causeway.(Idempotent)"""

from __future__ import annotations

import os
import sys
import asyncio

from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError

TOPICS: list[tuple[str, int, int]] = [
    # name, partitions, retention_ms
    ("raw.spans", 12, 6 * 3600 * 1000),
    ("signals.alerts", 6, 7 * 24 * 3600 * 1000),
    ("signals.k8s", 6, 7 * 24 * 3600 * 1000),
    ("signals.deploys", 3, 30 * 24 * 3600 * 1000),
    ("signals.logs", 6, 7 * 24 * 3600 * 1000),
    ("signals.traces", 6, 7 * 24 * 3600 * 1000),
    ("incidents.candidates", 3, 30 * 24 * 3600 * 1000),
    ("actions.requests", 1, 90 * 24 * 3600 * 1000),
    ("actions.results", 1, 90 * 24 * 3600 * 1000),
]

async def main() -> int:
    bootstrap = os.getenv("KAFKA_BOOTSTRAP", "localhost:19092")
    admin = AIOKafkaAdminClient(bootstrap_servers=bootstrap)
    await admin.start()
    try:
        existing = set(await admin.list_topics())
        to_create = []
        for name, parts, retention_ms in TOPICS:
            if name in existing:
                print(f"exists: {name}")
                continue
            to_create.append(
                NewTopic(
                    name=name,
                    num_partitions=parts,
                    replication_factor=1,
                    topic_configs={
                        "retention.ms": str(retention_ms),
                        "cleanup.policy": "delete",
                    },
                )
            )

        if not to_create:
            print("all topics already exist")
            return 0
        try:
            await admin.create_topics(to_create)
        except TopicAlreadyExistsError:
            pass
        for t in to_create:
            print(f"create: {t.name} partitions={t.num_partitions} ")
        return 0
    finally:
        await admin.close()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))