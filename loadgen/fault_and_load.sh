#!/usr/bin/env bash
set -euo pipefail

FRONTEND="${FRONTEND:-http://localhost:8080}"
PAYMENT_FAULT="${PAYMENT_FAULT:-http://localhost:8081/admin/fault}"
DURATION_SEC="${1:-90}"
DELAY_MS="${2:-500}"

echo "injecting latency ${DELAY_MS}ms on payment-svc for $((DURATION_SEC + 60))s"
curl -s -X POST "$PAYMENT_FAULT" \
  -H 'Content-Type: application/json' \
  -d "{\"kind\":\"latency\",\"delay_ms\":${DELAY_MS},\"duration\":\"$((DURATION_SEC + 60))s\"}"
echo

echo "load: GET ${FRONTEND}/ for ${DURATION_SEC}s"
end=$((SECONDS + DURATION_SEC))
ok=0
n=0
while (( SECONDS < end )); do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND/" || true)
  n=$((n + 1))
  if [[ "$code" == "200" ]]; then ok=$((ok + 1)); fi
  sleep 1
done
echo "done requests=${n} ok=${ok}"