#!/usr/bin/env bash
# Certified end-to-end demo: preflight → warm → topology → fault → poll → score.
# Usage: make up && make demo-e2e
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=e2e_helpers.sh
source "${ROOT}/scripts/e2e_helpers.sh"

echo "=== demo-e2e: certified live demo path ==="
e2e_preflight
e2e_warm_traffic "${E2E_WARM_SEC:-45}"
e2e_check_mesh_metrics
e2e_check_topology
e2e_inject_fault_and_load
INC="$(wait_for_incident)"
e2e_score_incident "$INC"
e2e_optional_narrate_feedback "$INC"
echo "demo_e2e_ok incident=$INC expected_top1=${EXPECTED}"
