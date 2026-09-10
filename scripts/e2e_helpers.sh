#!/usr/bin/env bash
# Shared helpers for verify-live and demo-e2e (source, do not execute alone).
set -euo pipefail

: "${API:=http://localhost:8000}"
: "${EXPECTED:=svc:payment-svc}"
: "${VM_URL:=http://localhost:8428}"
: "${WORKER_HEALTH_URL:=http://localhost:8085/healthz}"
: "${E2E_INCIDENT_TIMEOUT_SEC:=180}"
: "${E2E_INCIDENT_POLL_SEC:=5}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

api_read_headers() {
  if [[ -n "${API_READ_KEY:-}" ]]; then
    printf '%s' "-H" "Authorization: Bearer ${API_READ_KEY}"
  fi
}

api_write_headers() {
  if [[ -n "${INGEST_API_KEY:-}" ]]; then
    printf '%s' "-H" "Authorization: Bearer ${INGEST_API_KEY}"
  fi
}

api_get() {
  local path="$1"
  local -a hdr=()
  if [[ -n "${API_READ_KEY:-}" ]]; then
    hdr=(-H "Authorization: Bearer ${API_READ_KEY}")
  fi
  curl -sf -m 10 "${hdr[@]}" "${API}${path}"
}

api_post_json() {
  local path="$1"
  local body="$2"
  local -a hdr=(-H "Content-Type: application/json")
  if [[ -n "${INGEST_API_KEY:-}" ]]; then
    hdr+=(-H "Authorization: Bearer ${INGEST_API_KEY}")
  fi
  curl -sf -m 30 -X POST "${hdr[@]}" "${API}${path}" -d "$body"
}

e2e_preflight() {
  echo "=== e2e preflight: API /healthz ==="
  curl -sf -m 10 "${API}/healthz" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('health', d.get('status'), d.get('components', {}))
if d.get('status') not in ('ok', 'degraded'):
    raise SystemExit('API health not ok')
"

  echo "=== e2e preflight: mesh payment-svc :8081 ==="
  curl -sf -m 5 http://localhost:8081/ >/dev/null

  if curl -sf -m 3 "${WORKER_HEALTH_URL}" >/dev/null 2>&1; then
    echo "=== e2e preflight: worker health ok ==="
  else
    echo "=== e2e preflight: worker health skip (not on ${WORKER_HEALTH_URL}) ==="
  fi
  echo "preflight_ok"
}

e2e_warm_traffic() {
  local sec="${1:-45}"
  echo "=== e2e warm-up: traffic ${sec}s on frontend ==="
  bash "${ROOT}/loadgen/traffic.sh" http://localhost:8080/ "$sec"
}

e2e_check_mesh_metrics() {
  echo "=== e2e check: vmagent mesh metrics in VM ==="
  bash "${ROOT}/scripts/verify_mesh_metrics.sh"
}

e2e_check_topology() {
  echo "=== e2e check: service graph edges in VM ==="
  curl -sf -G "${VM_URL}/api/v1/query" \
    --data-urlencode 'query=count(traces_service_graph_request_total)' \
    | python3 -c "
import sys, json
d = json.load(sys.stdin)
r = d.get('data', {}).get('result', [])
if not r or float(r[0]['value'][1]) < 1:
    raise SystemExit(
        'no traces_service_graph_request_total in VM — run traffic longer or check otel-collector'
    )
print('service_graph_series', int(float(r[0]['value'][1])))
"

  local rows="0"
  if rows="$(docker compose exec -T postgres psql -U causeway -d causeway -t -A -c \
    "SELECT count(*) FROM edge_observation WHERE upper(bucket) > now() - interval '30 minutes'" \
    2>/dev/null | tr -d '[:space:]')"; then
    echo "edge_observation_rows_30m ${rows:-0}"
    if [[ "${rows:-0}" -lt 1 ]]; then
      echo "e2e_failed: no edge_observation in Postgres — topology_loop needs traffic (make traffic 60)" >&2
      return 1
    fi
  else
    echo "edge_observation check skipped (postgres exec failed)"
  fi
  echo "topology_ok"
}

e2e_inject_fault_and_load() {
  echo "=== e2e inject: background traffic + payment fault ==="
  bash "${ROOT}/loadgen/traffic.sh" http://localhost:8080/ 50 &
  local tpid=$!
  sleep 3
  bash "${ROOT}/loadgen/fault_and_load.sh" 75 250
  wait "$tpid" 2>/dev/null || true
}

latest_incident_id() {
  api_get "/api/v1/incidents" | python3 -c "
import sys, json
d = json.load(sys.stdin)
incs = d.get('incidents') or []
print(incs[0]['incident_id'] if incs else '')
"
}

wait_for_incident() {
  local timeout="${1:-$E2E_INCIDENT_TIMEOUT_SEC}"
  local poll="${2:-$E2E_INCIDENT_POLL_SEC}"
  echo "=== e2e wait: incident (timeout ${timeout}s, poll ${poll}s) ===" >&2
  local deadline=$((SECONDS + timeout))
  local inc=""
  while (( SECONDS < deadline )); do
    inc="$(latest_incident_id || true)"
    if [[ -n "$inc" ]]; then
      echo "incident=$inc" >&2
      echo "$inc"
      return 0
    fi
    sleep "$poll"
  done
  echo "e2e_failed: no incident after ${timeout}s" >&2
  echo "Hint: make logs | tail -50 — look for 'detected' and 'correlator:'" >&2
  docker compose logs --tail=40 causeway-worker 2>/dev/null || true
  return 1
}

e2e_score_incident() {
  local inc="$1"
  echo "=== e2e score: top-1 vs ${EXPECTED} ==="
  docker compose exec -T causeway-api python -m bench.score_incident \
    --incident-id "$inc" --expected "$EXPECTED"
}

e2e_optional_narrate_feedback() {
  local inc="$1"
  if [[ "${DEMO_E2E_NARRATE:-0}" != "1" ]]; then
    return 0
  fi
  echo "=== e2e optional: narrate + feedback ==="
  api_post_json "/api/v1/incidents/${inc}/narrate" "{}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('narrate provider', d.get('provider', '—'))
if d.get('narrative') is None and d.get('error'):
    print('narrate note', d.get('error'))
"
  api_post_json "/api/v1/incidents/${inc}/feedback" \
    '{"actual_root":"svc:payment-svc","submitted_by":"demo-e2e"}' \
    | python3 -m json.tool
}
