#!/usr/bin/env bash
set -euo pipefail
URL="${1:-http://localhost:8080/}"
N="${2:-50}"
echo "hitting $URL x $N"
ok=0
for i in $(seq 1 "$N"); do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$URL" || true)
  if [[ "$code" == "200" ]]; then ok=$((ok+1)); fi
done
echo "ok=$ok/$N"