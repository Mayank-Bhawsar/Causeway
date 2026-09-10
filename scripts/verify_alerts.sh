#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="${API:-http://localhost:8000}"
FIXTURE="$ROOT/bench/fixtures/alertmanager_webhook.json"

echo "=== verify-alerts: API health ==="
curl -sf "$API/healthz" >/dev/null
echo "health_ok"

echo "=== verify-alerts: POST sample Alertmanager webhook ==="
INGEST_HDR=()
if [[ -n "${INGEST_API_KEY:-}" ]]; then
  INGEST_HDR=(-H "Authorization: Bearer ${INGEST_API_KEY}")
fi
resp=$(curl -sf -X POST "$API/ingest/alerts" \
  -H "Content-Type: application/json" \
  "${INGEST_HDR[@]}" \
  --data-binary "@$FIXTURE")
echo "$resp" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d.get('accepted_count', 0) >= 1, d
print('ingest_ok accepted_count=', d['accepted_count'])
"

echo "=== verify-alerts: optional mesh check (for vmalert path) ==="
if curl -sf -m 3 http://localhost:8080/ >/dev/null; then
  echo "mesh_ok (run: make traffic & inject fault for live vmalert fires)"
else
  echo "mesh_skip (make up to test vmalert end-to-end)"
fi

echo "verify_alerts_ok"
