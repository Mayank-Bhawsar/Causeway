from datetime import datetime, timezone

from detectors.saturation import build_fault_active_signals


def test_fault_onset_stable_while_active():
    since: dict[str, datetime] = {}
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 9, 1, 12, 0, 45, tzinfo=timezone.utc)

    s0 = build_fault_active_signals({"payment-svc": 1.0}, t0, since)
    assert len(s0) == 1
    assert s0[0].onset_at == t0
    assert s0[0].payload.get("fault_active") == 1

    s1 = build_fault_active_signals({"payment-svc": 1.0}, t1, since)
    assert len(s1) == 1
    assert s1[0].onset_at == t0


def test_fault_clears_onset_map():
    since: dict[str, datetime] = {}
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    build_fault_active_signals({"payment-svc": 1.0}, t0, since)
    assert "payment-svc" in since

    out = build_fault_active_signals({}, t0, since)
    assert out == []
    assert "payment-svc" not in since
