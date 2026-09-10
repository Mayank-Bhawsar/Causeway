"""RCA quality metrics from feedback table."""

from __future__ import annotations

import os

import asyncpg
from fastapi import APIRouter

from bench.feedback_report import collect_rca_metrics

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


def _dsn() -> str:
    return os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql://causeway:causeway@postgres:5432/causeway",
    ).replace("postgresql+asyncpg://", "postgresql://")


@router.get("/rca")
async def rca_metrics() -> dict:
    conn_dsn = _dsn()
    return await collect_rca_metrics(conn_dsn)
