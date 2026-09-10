#!/usr/bin/env bash
set -euo pipefail
cd "/mnt/c/Users/Mayank.Bhawsar/OneDrive - Heuristics Informatics Pvt. Ltd/Desktop/test2/Projects/AIOps_Causeway"
OUT="_phase_d_verify.txt"
{
  echo "=== restart worker with detectors mount ==="
  DOCKER_BUILDKIT=0 docker compose up -d --build causeway-worker causeway-api

  echo "=== wait ==="
  for i in $(seq 1 15); do
    if curl -sf http://localhost:8000/healthz >/dev/null; then echo health_ok; break; fi
    sleep 2
  done

  echo "=== imports ==="
  docker compose exec -T causeway-worker python -c "
from detectors.baseline import EwmaBaseline
from detectors.changepoint import PageHinkley
from detectors.latency import detect_latency_signals
from detectors.errors import detect_error_signals
print('imports_ok')
"

  echo "=== unit tests ==="
  docker compose exec -T causeway-api pip install -q pytest 2>/dev/null || true
  docker compose exec -T causeway-api pytest detectors/test_detectors.py -v

  echo "=== worker log sample ==="
  docker compose logs --tail=30 causeway-worker
} > "$OUT" 2>&1
