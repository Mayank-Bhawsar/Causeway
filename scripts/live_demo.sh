#!/usr/bin/env bash
# Causeway — ~5 minute live demo script (Phase J+)
# Usage: bash scripts/live_demo.sh          # print steps only
#        bash scripts/live_demo.sh --run    # execute commands (needs stack up)
set -euo pipefail

API="${API:-http://localhost:8000}"
RUN=false
if [[ "${1:-}" == "--run" ]]; then
  RUN=true
fi

step() {
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  $1"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "$2"
}

step "0 · Before the room (2 min)" \
"Terminal 1: make up
Terminal 2 (optional): make logs
Browser: http://localhost:8000/ui
Certify before presenting: make demo-e2e   (or make verify-live for a shorter check)
Say: 'Synthetic shop mesh → OTel → VictoriaMetrics; worker detects + correlates in 90s windows.'"

step "1 · Start traffic + fault (~30 s talking)" \
"make demo
# Slows payment-svc and loads frontend — root should be svc:payment-svc
Say: 'We inject latency on payment; checkout and frontend show symptoms downstream.'"

if $RUN; then
  curl -sf -m 3 http://localhost:8081/ >/dev/null || {
    echo "ERROR: payment-svc not on :8081 — run: make up" >&2
    exit 1
  }
  bash loadgen/fault_and_load.sh 90 500
fi

step "2 · Wait for correlator (90 s window + flush)" \
"Watch worker: 'detected …' then 'correlator flushed …'
~2 minutes wall clock after demo start.
Say: 'Signals dedupe alert+detector on the same service; HDBSCAN groups one incident.'"

if $RUN; then
  echo "(waiting 120s for window + rank…)"
  sleep 120
fi

step "3 · Prove RCA (~30 s)" \
"make score
make graph | head -40
Say: 'PageRank on the call graph — payment ranked first, not just loudest symptom.'"

if $RUN; then
  make score || true
  make graph | head -40 || true
fi

step "4 · Explain with evidence (~45 s)" \
"make evidence | head -60
make narrate   # OpenAI if key set, else template
curl -s \$API/api/v1/incidents/\$(curl -s \$API/api/v1/incidents | python3 -c \"import sys,json; print(json.load(sys.stdin)['incidents'][0]['incident_id'])\")/narrative | python3 -m json.tool | head -30
UI: open Narrative panel · Copy incident ID · submit feedback actual_root=svc:payment-svc"

if $RUN; then
  make evidence | head -60 || true
  make narrate 2>/dev/null || echo "(narrate skipped — set OPENAI_API_KEY or use template via API)"
fi

step "5 · Learning loop (~30 s)" \
"make feedback
make feedback-report
curl -s \$API/api/v1/metrics/rca | python3 -m json.tool
Say: 'Operator feedback closes the loop — we track top-1 accuracy, not black-box RCA.'"

if $RUN; then
  make feedback 2>/dev/null || echo "(no incident yet — complete step 2 wait)"
  make feedback-report 2>/dev/null || true
fi

step "6 · Optional depth (if time)" \
"make verify-mesh-metrics   # vmagent scrape path
make bench                 # offline fixtures incl. alert+latency dedupe
Closing: 'Group on topology + time, rank root cause, explain with grounded evidence.'"

echo ""
echo "Done. Re-run with --run to execute automated steps (still present live for steps 2–4)."
