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
make evidence
make feedback
make action        # diagnostic suggestion only
```

OpenAI narration is deferred until `OPENAI_API_KEY` is set.
