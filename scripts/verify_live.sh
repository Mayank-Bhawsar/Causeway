#!/usr/bin/env bash
# End-to-end smoke: mesh + fault + correlator window + top-1 score.
set -euo pipefail
API="${API:-http://localhost:8000}"
EXPECTED="${EXPECTED:-svc:payment-svc}"

echo "=== verify-live: prerequisites ==="
curl -sf -m 5 "$API/healthz" >/dev/null
curl -sf -m 5 http://localhost:8081/ >/dev/null
echo "mesh_and_api_ok"

echo "=== verify-live: traffic + fault (may take ~2 min) ==="
bash loadgen/traffic.sh http://localhost:8080/ 50 &
TPID=$!
sleep 3
bash loadgen/fault_and_load.sh 75 250
wait "$TPID" 2>/dev/null || true

echo "=== verify-live: wait for correlator window (90s + buffer) ==="
sleep 100

INC=$(curl -s "$API/api/v1/incidents" | python3 -c "
import sys, json
d = json.load(sys.stdin)
incs = d.get('incidents') or []
print(incs[0]['incident_id'] if incs else '')
")
if [[ -z "$INC" ]]; then
  echo "verify_live_failed: no incidents (check: make logs)"
  exit 1
fi
echo "incident=$INC"

docker compose exec -T causeway-api python -m bench.score_incident \
  --incident-id "$INC" --expected "$EXPECTED"

echo "verify_live_ok"
