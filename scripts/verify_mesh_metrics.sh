#!/usr/bin/env bash
# Confirm vmagent scraped meshgen metrics into VictoriaMetrics.
set -euo pipefail
VM="${VM_URL:-http://localhost:8428}"

echo "=== verify-mesh-metrics: meshgen_requests_total ==="
curl -sf -G "$VM/api/v1/query" \
  --data-urlencode 'query=count(meshgen_requests_total)' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
r = d.get('data', {}).get('result', [])
if not r:
    raise SystemExit('no meshgen_requests_total in VM — is vmagent up?')
n = float(r[0]['value'][1])
print('series_count', int(n))
assert n >= 1, 'expected at least one meshgen_requests_total series'
"

echo "=== verify-mesh-metrics: meshgen_fault_active ==="
curl -sf -G "$VM/api/v1/query" \
  --data-urlencode 'query=count(meshgen_fault_active)' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
r = d.get('data', {}).get('result', [])
if not r:
    raise SystemExit('no meshgen_fault_active in VM')
print('fault_gauge_series', int(float(r[0]['value'][1])))
"

echo "=== verify-mesh-metrics: sample by service label ==="
curl -sf -G "$VM/api/v1/query" \
  --data-urlencode 'query=meshgen_requests_total{service="payment-svc"}' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
r = d.get('data', {}).get('result', [])
print('payment_svc_samples', len(r))
"

echo "=== verify-mesh-metrics: fault gauge (payment-svc after demo fault) ==="
curl -sf -G "$VM/api/v1/query" \
  --data-urlencode 'query=meshgen_fault_active{service="payment-svc"}' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
r = d.get('data', {}).get('result', [])
print('payment_fault_series', len(r))
"

echo "verify_mesh_metrics_ok"
