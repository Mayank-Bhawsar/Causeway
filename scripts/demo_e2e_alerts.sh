#!/usr/bin/env bash
# Phase L4: certified demo + alert ingest paths.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

bash scripts/demo_e2e.sh

echo "=== demo-e2e-alerts: webhook ingest (verify-alerts) ==="
bash scripts/verify_alerts.sh

if [[ "${DEMO_E2E_ALERTS_LIVE:-0}" == "1" ]]; then
  echo "=== demo-e2e-alerts: live vmalert path (slow) ==="
  bash scripts/verify_alerts_live.sh
else
  echo "skip live vmalert (set DEMO_E2E_ALERTS_LIVE=1 to run verify-alerts-live)"
fi

echo "demo_e2e_alerts_ok"
