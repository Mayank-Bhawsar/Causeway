# Causeway

Local AIOps engine: topology from OTel servicegraph → correlate signals → blame-graph RCA → evidence pack.

## Demo

```bash
make up
make build
make demo          # payment-svc latency + load (~90s)
make ui            # operator dashboard http://localhost:8000/ui
# wait ~2 minutes for topology + correlator window
make score         # expect svc:payment-svc
make graph
make -B evidence
make feedback
make action        # diagnostic suggestion only
make narrate       # requires OPENAI_API_KEY + outbound HTTPS from Docker
make narrative   # read stored narrative after narrate succeeds
```

Set `OPENAI_API_KEY` in `.env`. The API container must reach `api.openai.com` (fix WSL/Docker DNS if you see `APIConnectionError`).

Optional: `SLACK_WEBHOOK_URL` in `.env` for incident notifications. Optional: `OPA_URL` for external policy (`deploy/opa/policy.rego`); start OPA with `docker compose --profile opa up -d opa`.

```bash
make verify-all    # unit tests + bench + alert ingest + mesh metrics in VM
make verify-mesh-metrics   # after make up, wait ~30s for first scrape
make verify-alerts-live    # vmalert + fault + load → Kafka (~2-3 min)
make verify-live   # live mesh demo + top-1 score (~3 min, needs make up)
```
