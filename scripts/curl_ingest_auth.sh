#!/usr/bin/env bash
# Emit curl args for INGEST_API_KEY when set (Phase K).
set -euo pipefail
if [[ -n "${INGEST_API_KEY:-}" ]]; then
  printf '%s' "-H" "Authorization: Bearer ${INGEST_API_KEY}"
fi
