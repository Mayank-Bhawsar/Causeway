"""Bench replay applies correlator dedupe like production."""
from __future__ import annotations

import json
from pathlib import Path

from bench.replay import dedupe_signals, replay_fixture

FIXTURE = Path(__file__).parent / "fixtures" / "payment_alert_latency.json"


def test_payment_alert_latency_dedupe_and_top1():
    result = replay_fixture(FIXTURE)
    assert result["raw_signal_count"] == 4
    assert result["signal_count"] == 3
    assert result["dedupe_ok"] is True
    assert result["top1_ok"] is True
    assert result["top1"] == "svc:payment-svc"


def test_fixture_file_has_expected_signal_count():
    fx = json.loads(FIXTURE.read_text())
    assert fx["expected_signal_count"] == 3
