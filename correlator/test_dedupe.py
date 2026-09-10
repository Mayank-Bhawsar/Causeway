from correlator.dedupe import dedupe_key, merge_into_buffer


def test_latency_alert_same_key():
    a = {"signal_id": "s1", "kind": "trace_latency_shift", "node_id": "svc:payment-svc"}
    b = {"signal_id": "s2", "kind": "alert", "node_id": "svc:payment-svc"}
    assert dedupe_key(a) == dedupe_key(b)


def test_merge_keeps_one_buffer_row():
    buf: list[dict] = []
    s1 = {
        "signal_id": "sig_a",
        "kind": "trace_latency_shift",
        "node_id": "svc:payment-svc",
        "severity": 0.5,
        "onset_at": "2026-09-01T12:00:00+00:00",
        "observed_at": "2026-09-01T12:00:15+00:00",
        "payload": {"z_score": 3.1},
    }
    s2 = {
        "signal_id": "sig_b",
        "kind": "alert",
        "node_id": "svc:payment-svc",
        "severity": 0.7,
        "onset_at": "2026-09-01T11:59:00+00:00",
        "observed_at": "2026-09-01T12:00:20+00:00",
        "payload": {"alertname": "HighServiceLatency"},
    }
    merge_into_buffer(buf, s1)
    out, merged = merge_into_buffer(buf, s2)
    assert merged is True
    assert len(buf) == 1
    assert out["signal_id"] == "sig_a"
    assert out["severity"] == 0.7
    assert "z_score" in out["payload"]
    assert out["payload"]["alertname"] == "HighServiceLatency"
