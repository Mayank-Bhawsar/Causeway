import json 
import uuid
import os
from datetime import datetime, timezone

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, HTTPException, Request

from api.models.signal import Signal, SignalKind

router = APIRouter(prefix="/ingest", tags=["ingest"])

async def _publish(signal: Signal) -> dict:
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



@router.post("/signal")
async def ingest_signal(signal: Signal) -> dict:
    return await _publish(signal)

    
@router.post("/alerts")
async def ingest_alerts(request: Request) -> dict:
    """Alertmanager webhook -> one Signal per firing alert."""
    body = await request.json()
    now = datetime.now(timezone.utc)
    accepted = []

    for alert in body.get("alerts", []):
        if alert.get("status") not in (None, "firing"):
            if alert.get("status") == "resolved":
                continue

        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        service = labels.get("service_name") or labels.get("server") or labels.get("job") or "unknown"
        node_id = service if ":" in service else f"svc:{service}"

        starts = alert.get("startsAt") or now.isoformat()
        try:
            onset = datetime.fromisoformat(starts.replace("Z", "+00:00"))
        except ValueError:
            onset = now
        
        severity_map = {"critical": 0.95, "warning": 0.7, "info":0.4}
        sev = severity_map.get(str(labels.get("severity", "warning")).lower(), 0.7)

        signal = Signal(
            signal_id=f"sig_{uuid.uuid4().hex[:16]}",
            kind=SignalKind.ALERT,
            node_id=node_id,
            severity=sev,
            onset_at=onset,
            observed_at=now,
            fingerprint=alert.get("fingerprint"),
            payload={
                "alertname": labels.get("alertname"),
                "labels": labels,
                "annotations": annotations,
                "generatorURL": alert.get("generatorURL"),
            },
        )
        accepted.append(await _publish(signal))

    return {"accepted_count": len(accepted), "items": accepted}