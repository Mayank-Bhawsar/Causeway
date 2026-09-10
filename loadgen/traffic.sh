#!/usr/bin/env bash
# Steady background load so vmalert increase() queries see traffic.
set -euo pipefail
URL="${1:-http://localhost:8080/}"
DURATION="${2:-120}"
INTERVAL="${3:-0.5}"

echo "traffic: $URL for ${DURATION}s (interval ${INTERVAL}s)"
end=$((SECONDS + DURATION))
ok=0
total=0
while (( SECONDS < end )); do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$URL" || true)
  total=$((total + 1))
  if [[ "$code" == "200" ]]; then ok=$((ok + 1)); fi
  sleep "$INTERVAL"
done
echo "traffic done ok=$ok/$total"
