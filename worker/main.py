import asyncio
import json
import os

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from api.models.signal import Signal
from detectors.latency import detect_latency_signals

TOPICS = [
    "signals.alerts",
    "signals.k8s",
    "signals.deploys",
    "signals.logs",
    "signals.traces",
]

async def consume() -> None:
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
                f"got topic={msg.topic} key={msg.key}"
                f"signal_id={body.get('signal_id')} kind={body.get('kind')}",
                flush=True,
            )
    finally:
        await consumer.stop()

async def detect_loop() -> None:
    bootstrap = os.getenv("KAFKA_BOOTSTRAP", "redpanda:9092")
    interval = int(os.getenv("DETECT_INTERVAL_SEC", "30"))
    while True:
        try:
            producer = AIOKafkaProducer(bootstrap_servers=bootstrap)
            await producer.start()
            try:
                for signal in await detect_latency_signals():
                    await producer.send_and_wait(
                        signal.kafka_topic(),
                        key=signal.kafka_key().encode(),
                        value=signal.model_dump_json().encode(),
                    )
                    print(
                        f"detected topic={signal.kafka_topic()} "
                        f"node={signal.node_id} sev={signal.severity:.2f}",
                        flush=True,
                    )
            finally:
                await producer.stop()
        except Exception as exc:  # noqa: BLE001
            print(f"detect_loop error: {exc}", flush=True)
        await asyncio.sleep(interval)


async def run() -> None:
    await asyncio.gather(consume(), detect_loop())

if __name__ == "__main__":
    asyncio.run(run())
