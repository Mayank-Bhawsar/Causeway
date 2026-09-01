from narrator.validate import validate_narrative


def test_rejects_dangling_ref():
    pack = {"entries": [{"key": "EV-SIG-0001", "kind": "signal", "severity": 0.4}]}
    body = {
        "claims": [{"text": "latency issue", "evidence_refs": ["EV-MISSING"]}],
        "ranked_causes": [],
    }
    errs = validate_narrative(pack, body)
    assert errs
    assert any("dangling" in e for e in errs)


def test_accepts_grounded():
    pack = {
        "entries": [
            {"key": "EV-SIG-0001", "severity": 0.4, "node_id": "svc:payment-svc", "kind": "signal"},
        ]
    }
    body = {
        "claims": [{"text": "severity 0.4 on payment", "evidence_refs": ["EV-SIG-0001"]}],
        "ranked_causes": [
            {"node_id": "svc:payment-svc", "why": "top", "evidence_refs": ["EV-SIG-0001"]}
        ],
    }
    assert validate_narrative(pack, body) == []


def test_rejects_ungrounded_number():
    pack = {"entries": [{"key": "EV-SIG-0001", "severity": 0.4, "kind": "signal"}]}
    body = {
        "claims": [{"text": "latency hit 999 ms", "evidence_refs": ["EV-SIG-0001"]}],
        "ranked_causes": [],
    }
    errs = validate_narrative(pack, body)
    assert any("ungrounded" in e for e in errs)


def test_rejects_claim_without_refs():
    pack = {"entries": [{"key": "EV-SIG-0001", "kind": "signal"}]}
    body = {"claims": [{"text": "something broke", "evidence_refs": []}], "ranked_causes": []}
    errs = validate_narrative(pack, body)
    assert any("zero evidence_refs" in e for e in errs)


def test_rejects_unknown_node_on_cause():
    pack = {"entries": [{"key": "EV-SIG-0001", "node_id": "svc:payment-svc", "kind": "signal"}]}
    body = {
        "claims": [],
        "ranked_causes": [
            {"node_id": "svc:unknown-svc", "why": "guess", "evidence_refs": ["EV-SIG-0001"]}
        ],
    }
    errs = validate_narrative(pack, body)
    assert any("not in topology" in e for e in errs)


def test_template_narrative_passes_validation():
    from narrator.template_narrator import template_narrate

    pack = {
        "incident_id": "inc_test",
        "signal_count": 1,
        "top_cause": "svc:payment-svc",
        "entries": [
            {"key": "EV-SIG-0001", "kind": "signal", "node_id": "svc:payment-svc", "severity": 0.5},
            {"key": "EV-RCA-0001", "kind": "ranked_cause", "node_id": "svc:payment-svc", "score": 2.1, "method": "blame_pagerank"},
        ],
    }
    body = template_narrate(pack)
    assert validate_narrative(pack, body) == []