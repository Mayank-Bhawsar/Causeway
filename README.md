# Causeway

Local AIOps engine: topology from OTel servicegraph → correlate signals → blame-graph RCA → evidence pack.

## Demo

```bash
make up
make build
make demo          # payment-svc latency + load (~90s)
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
