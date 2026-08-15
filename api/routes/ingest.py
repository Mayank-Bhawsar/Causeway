import json 
import os

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, HTTPException

from api.models.signal import signal

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("/signal")
async def ingest_signal(signal: Signal) -> dict:
    bootstrap = os.getenv("KAFKA_BOOTSTRAP", "redpanda:9092")
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap)
    await producer.start()
    try:
        topic = signal.kafka_topic()
        await producer.send_and_wait(
            topic,
            key=signal.kafka_key().encode(),
            value=signal.model_dump_json().encode(),
        )
        return {"accepted": True, "topic": topic, "signal_id": signal.signal_id}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await producer.stop()