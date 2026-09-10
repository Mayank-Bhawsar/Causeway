#!/usr/bin/env bash
# Phase L1: sample deploy event → Kafka signals.deploys
set -euo pipefail
API="${API:-http://localhost:8000}"
INGEST_HDR=()
if [[ -n "${INGEST_API_KEY:-}" ]]; then
  INGEST_HDR=(-H "Authorization: Bearer ${INGEST_API_KEY}")
fi
curl -sf -X POST "${API}/ingest/deploy" \
  -H "Content-Type: application/json" \
  "${INGEST_HDR[@]}" \
  -d '{"service":"payment-svc","revision":"demo-rollout","deployer":"make sample-deploy"}' \
  | python3 -m json.tool
