#!/usr/bin/env bash
# End-to-end smoke: mesh + fault + correlator window + top-1 score.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=e2e_helpers.sh
source "${ROOT}/scripts/e2e_helpers.sh"

echo "=== verify-live: prerequisites ==="
e2e_preflight

echo "=== verify-live: short warm-up (30s) ==="
e2e_warm_traffic 30

e2e_inject_fault_and_load

INC="$(wait_for_incident "${E2E_INCIDENT_TIMEOUT_SEC:-180}")"
e2e_score_incident "$INC"

echo "verify_live_ok incident=$INC"
