# Causeway

Local AIOps engine: topology from OTel servicegraph → correlate signals → blame-graph RCA → evidence pack.

## Demo

```bash
make up
make build
make demo          # payment-svc latency + load (~90s)
make ui            # operator UI; http://localhost:8000/ui
make demo-script   # 5-min live demo talking points (Phase J+)
make demo-run      # automated demo steps (still ~2 min correlator wait)
# wait ~2 minutes for topology + correlator window
make score         # expect svc:payment-svc
make feedback
make feedback-report
make graph
make -B evidence
make feedback
make action        # diagnostic suggestion only
make narrate       # requires OPENAI_API_KEY + outbound HTTPS from Docker
make narrative   # read stored narrative after narrate succeeds
```

Set `OPENAI_API_KEY` in `.env`. Optional Phase K keys: `INGEST_API_KEY`, `API_READ_KEY` (see `.env.example`).

Worker health: `curl http://localhost:8085/healthz` after `make up`.

Optional: `SLACK_WEBHOOK_URL` in `.env` for incident notifications. Optional: `OPA_URL` for external policy (`deploy/opa/policy.rego`); start OPA with `docker compose --profile opa up -d opa`.

```bash
make verify-all    # unit tests + bench + alert ingest + mesh metrics in VM
make verify-mesh-metrics   # after make up, wait ~30s for first scrape
make verify-alerts-live    # vmalert + fault + load → Kafka (~2-3 min)
make verify-live   # live mesh demo + top-1 score (~3 min, needs make up)
```
