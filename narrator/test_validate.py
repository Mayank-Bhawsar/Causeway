from narrator.validate import validate_narrative

def test_rejects_dangling_ref():
    pack = {"entries": [{"key": "EV-SIG-0001", "kind": "signal", "severity": 0.4}]}
    body = {"claims": [{"text": "latency 0.4", "evidence_refs": ["EV-MISSING"]}], "ranked_causes": []}
    assert validate_narrative(pack, body)

def test_accepts_grounded():
    pack = {"entries": [{"key": "EV-SIG-0001", "severity": 0.4, "node_id": "svc:payment-svc"}]}
    body = {
        "claims": [{"text": "severity 0.4 on payment", "evidence_refs": ["EV-SIG-0001"]}],
        "ranked_causes": [{"node_id": "svc:payment-svc", "why": "top", "evidence_refs": ["EV-SIG-0001"]}],
    }
    assert validate_narrative(pack, body) == []