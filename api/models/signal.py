from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SignalKind(str, Enum):
    ALERT = "alert"
    K8S_EVENT = "k8s_event"
    DEPLOY = "deploy"
    LOG_TEMPLATE = "log_template"
    TRACE_LATENCY_SHIFT = "trace_latency_shift"
    TRACE_ERROR_SHIFT = "trace_error_shift"
    SATURATION = "saturation"

class Signal (BaseModel):
    """Canonical envelope on signals.* topics (and mirrored into Postgres signal table)."""

    signal_id: str
    kind: SignalKind
    node_id: str = Field(..., description="e.g. svc:payment-svc, pod:..., db:...")
    severity: float = Field(..., ge=0.0, le=1.0)
    onset_at: datetime
    observed_at: datetime
    fingerprint: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    embedding: list[float] | None = None

    @field_validator("node_id")
    @classmethod
    def node_id_has_prefix(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError("node_id must look like kind:name, e.g. svc:payment-svc")
        return v

    def kafka_topic(self) -> str:
        return {
            SignalKind.ALERT: "signals.alerts",
            SignalKind.K8S_EVENT: "signals.k8s",
            SignalKind.DEPLOY: "signals.deploys",
            SignalKind.LOG_TEMPLATE: "signals.logs",
            SignalKind.TRACE_LATENCY_SHIFT: "signals.traces",
            SignalKind.TRACE_ERROR_SHIFT: "signals.traces",
            SignalKind.SATURATION: "signals.traces",
        }[self.kind]

    def kafka_key(self) -> str:
        return self.node_id