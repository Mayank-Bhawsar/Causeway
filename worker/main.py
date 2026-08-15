import asyncio
import json
import os

from aiokafka import AIOKafkaConsumer

TOPICS = [
    "signals.alerts",
    "signals.k8s",
    "signals.deploys",
    "signals.logs",
    "signals.traces",
]


async def run() -> None:
    bootstrap = os.getenv("KAFKA_BOOTSTRAP", "redpanda:9092")
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=bootstrap,
        group_id="causeway-worker",
        auto_offset_reset="earliest",
    )
    await consumer.start()
    print(f"worker listening on {TOPICS}", flush=True)
    try:
        async for msg in consumer:
            body = json.loads(msg.value.decode())
            print(
                f"got topic={msg.topic} key={msg.key} signal_id={body.get('signal_id')} kind={body.get('kind')}",
                flush=True,
            )
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(run())
