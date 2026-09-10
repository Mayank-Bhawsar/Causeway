#!/usr/bin/env bash
# End-to-end: traffic + payment latency fault -> vmalert -> Alertmanager -> API -> Kafka.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="${API:-http://localhost:8000}"
AM="${ALERTMANAGER_URL:-http://localhost:9093}"
VM="${VM_URL:-http://localhost:8428}"
TIMEOUT="${ALERT_LIVE_TIMEOUT:-150}"

echo "=== verify-alerts-live: prerequisites ==="
curl -sf "$API/healthz" >/dev/null
curl -sf -m 5 http://localhost:8080/ >/dev/null
curl -sf -m 5 http://localhost:8081/ >/dev/null
curl -sf -m 5 "$AM/api/v2/status" >/dev/null
docker compose ps --status running vmalert alertmanager causeway-api redpanda >/dev/null 2>&1 || {
  echo "missing services — run: make up"
  exit 1
}
echo "api_mesh_am_ok"

OUT="${TMPDIR:-/tmp}/causeway_alert_live.json"
rm -f "$OUT"

echo "=== verify-alerts-live: Kafka listener (expect payment + HighServiceLatency) ==="
docker compose exec -T causeway-api python /app/scripts/check_alert_kafka.py \
  --timeout "$TIMEOUT" --expect payment > "$OUT" &
LISTEN_PID=$!
sleep 3

cleanup() {
  kill "$LISTEN_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "=== verify-alerts-live: fault + load (payment ${DELAY_MS:-500}ms) ==="
bash "$ROOT/loadgen/fault_and_load.sh" 75 500

echo "=== verify-alerts-live: VM payment latency (best-effort) ==="
curl -sf -G "$VM/api/v1/query" \
  --data-urlencode 'query=(
    sum(increase(traces_span_metrics_duration_milliseconds_sum{span_kind="SPAN_KIND_SERVER",service_name="payment-svc"}[1m]))
    /
    clamp_min(sum(increase(traces_span_metrics_duration_milliseconds_count{span_kind="SPAN_KIND_SERVER",service_name="payment-svc"}[1m])),1)
  )' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
r = d.get('data', {}).get('result', [])
if r:
    print('payment_avg_latency_ms', round(float(r[0]['value'][1]), 1))
else:
    print('payment_avg_latency_ms unknown')
" || true

echo "=== verify-alerts-live: Alertmanager active alerts (best-effort) ==="
curl -sf "$AM/api/v2/alerts" 2>/dev/null | python3 -c "
import sys, json
try:
    alerts = json.load(sys.stdin)
except Exception:
    print('alertmanager_skip')
    raise SystemExit(0)
firing = [a for a in alerts if a.get('status',{}).get('state')=='active']
print('alertmanager_active_count', len(firing))
for a in firing[:3]:
    print(' ', a.get('labels',{}).get('alertname'), a.get('labels',{}).get('service_name'))
" || true

echo "=== verify-alerts-live: waiting for Kafka consumer ==="
wait "$LISTEN_PID"
trap - EXIT

cat "$OUT"
python3 -c "
import json, sys
d = json.load(open('$OUT'))
assert d.get('ok') is True, d
print('kafka_alert_ok alertname=', d.get('alertname'), 'node=', d.get('node_id'))
"

echo "verify_alerts_live_ok"
