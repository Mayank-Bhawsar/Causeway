# Causeway — Knowledge Transfer (engineering journey)

This document is an onboarding / evolution guide for a new backend/DevOps engineer. It reconstructs how the project was built, why each stage existed, and how the architecture looks **today**.

**As of:** 15 Sep 2026.

**Important distinction:**
- `02-causeway.md` is the **target architecture**.
- `understanding.md` is the **living status** (phases A–M1).
- This file is the **chronological engineering journey**.
- Terraform, Kubernetes manifests, Tempo, Loki/Drain3, embeddings on the hot path, snapshot-at-window-start, seasonal models, and a mutating ActionExecutor are **not** implemented.

Git now has ~97 commits (was 59 at the first MVP write-up). Phases **A–K, L1/L3/L4, M1** are implemented.

---

# Causeway — engineering journey (current)

The first half of the repo is still the original MVP: Compose stack, mesh, OTel, Kafka, worker, blame PageRank, evidence, optional LLM. After that, the project stopped being “one window, one incident, fixed 200 ms threshold” and became a **testable local AIOps product**: clustering, statistical detectors, operator UI, CI, optional auth/OPA/Slack.

**Still not in the repo:** Terraform, Kubernetes manifests, Tempo, Loki/Drain3, embeddings on the hot path, snapshot-at-window-start, seasonal models, mutating ActionExecutor.

---

## Chronological evolution

### Stages 0–18 — original MVP (Aug 2026)

These stages are unchanged in purpose. They still exist as the foundation.

| Stage | What landed | Why |
|-------|-------------|-----|
| **0** | Spec + repo (`02-causeway.md`, `pyproject.toml`) | Shared contract before code |
| **1** | Postgres, Redpanda, VictoriaMetrics, schema | Persistence + event bus + TSDB |
| **2** | FastAPI + `/healthz` | Observable first process |
| **3** | Canonical `Signal` + topics | Heterogeneous events → one envelope |
| **4** | `causeway-worker` consumer | API must not do correlation |
| **5** | Go meshgen + 12 services + faults | Known root cause (`payment-svc`) |
| **6** | OTLP → collector → spanmetrics/servicegraph | Observed topology, not YAML |
| **7** | vmalert + Alertmanager + `/ingest/alerts` | Standard alert path |
| **8** | Latency detector → `signals.traces` | Direct PromQL path |
| **9** | Time-window correlator + incident tables | Compression, not 1:1 alerts |
| **10** | Incident REST | Operators can read incidents |
| **11** | Severity RCA | Fallback ranking |
| **12** | Topology persist (`edge_observation`, snapshots) | Graph for blame |
| **13** | Personalized PageRank RCA | Rank origin, not loudest symptom |
| **14** | Evidence pack | Determinism boundary for LLM |
| **15** | OpenAI narrate (key-gated) | Language after math |
| **16** | Feedback POST | Human labels |
| **17** | Graph API + top-1 bench | Inspect + score demo |
| **18** | Diagnostic action + `audit_log` | Suggest only, `applied: false` |

**Dependency still holds:** no Signals → no incidents → no RCA → no evidence → no narration/actions.

The sections below expand each original stage, then continue through Phases A–M1.

---

### Stage 0 — Product specification and repository bootstrap

**Goal:** Define Causeway as a topology-aware AIOps system rather than a generic alerting or chatbot project.

**Motivation:** Traditional alert grouping cannot determine causal relationships between services. The initial specification therefore proposed:

signals → correlation → topology-aware RCA → evidence → narration → actions.

**Components:** Architecture specification, Python package structure, dependency declaration, initial README and environment template.

**Technologies:** Python 3.12, FastAPI, Pydantic, PostgreSQL, Kafka-compatible messaging, OpenTelemetry and pgvector were selected as the intended platform.

**Architecture change:**

```
Specification
     |
Repository skeleton
```

**Without this stage:** Later components would lack shared terminology, data contracts, node identity rules, evidence boundaries and an agreed RCA direction.

**Files:** `02-causeway.md`, `README.md`, `pyproject.toml`, `.env.example`, `.gitignore`

---

### Stage 1 — Local data and messaging infrastructure

**Goal:** Provide persistent storage, an event bus and reproducible local startup.

**Motivation:** Causeway needs two different storage models:

1. Kafka/Redpanda for replayable, asynchronous telemetry.
2. PostgreSQL for durable topology, incidents, candidates and evidence.

**Components:**
- PostgreSQL 16 with pgvector and btree_gist.
- Redpanda as a lightweight Kafka-compatible broker.
- VictoriaMetrics as the telemetry query source.
- Docker Compose health checks and persistent PostgreSQL volume.
- Initial database schema.

**Tables introduced:** `node_version`, `edge_observation`, `topology_snapshot`, `signal`, `incident`, `incident_signal`, `cause_candidate`, `evidence_pack`, `narrative`, `feedback`, `audit_log`, `ground_truth`.

Not all tables were used immediately. The migration established the intended domain model before every producer existed.

**DevOps concepts:** Infrastructure as containers, persistent volumes, dependency health checks, internal versus host Kafka advertised addresses, database initialization through mounted SQL.

**Architecture:**

```
PostgreSQL       Redpanda       VictoriaMetrics
```

**Without this stage:** Signals could not survive process restarts, incidents could not be queried, and asynchronous workers could not be introduced.

**Files:** `docker-compose.yml`, `db/migrations/0001_init.sql`, `.env.example`

---

### Stage 2 — FastAPI service and dependency health

**Goal:** Introduce the first executable Causeway service.

**Motivation:** Before accepting telemetry, engineers needed an observable API process that could verify its own infrastructure dependencies.

**Components:** FastAPI application, APIRouter-based modular routing, `GET /healthz`, Python Docker image, Makefile lifecycle commands.

`GET /healthz` checks PostgreSQL (`SELECT 1`), Redpanda (list topics), VictoriaMetrics (`/-/healthy`). Later it also probes the worker.

**Architecture:**

```
Operator
   |
FastAPI /healthz
   |
   +-- PostgreSQL
   +-- Redpanda
   +-- VictoriaMetrics
```

**Without this stage:** Infrastructure failures would appear later as obscure producer, consumer or database errors.

**Files:** `Dockerfile`, `api/main.py`, `api/routes/health.py`, `Makefile`, `docker-compose.yml`

---

### Stage 3 — Canonical Signal model and Kafka topic strategy

**Goal:** Create a common representation for heterogeneous operational events.

**Dependency:** Correlation cannot be implemented before signals have consistent node IDs, severity, timestamps and kinds.

**Motivation:** Alertmanager alerts, trace anomalies, deployments, logs and Kubernetes events have incompatible schemas. Correlation should consume one contract rather than contain source-specific parsing logic.

**Components:** Pydantic `Signal` model, `SignalKind` enum, validation for namespaced node IDs such as `svc:payment-svc`, topic and partition-key selection, idempotent Kafka topic creation script.

**Topics declared:** `raw.spans`, `signals.alerts`, `signals.k8s`, `signals.deploys`, `signals.logs`, `signals.traces`, `incidents.candidates`, `actions.requests`, `actions.results`.

**Currently active in the worker:** `signals.alerts`, `signals.k8s`, `signals.deploys`, `signals.logs`, `signals.traces`.

The remaining topics are roadmap contracts and are not used by the current runtime.

**New APIs:** `POST /ingest/signal`

**Data flow:**

```
External producer
       |
POST /ingest/signal
       |
Pydantic validation
       |
signals.<kind> in Redpanda
```

**Without this stage:** Every detector would produce a different payload and the worker could not process all signal types uniformly.

**Files:** `api/models/signal.py`, `api/routes/ingest.py`, `scripts/create_topics.py`, `api/main.py`

---

### Stage 4 — Asynchronous worker

**Goal:** Move continuous processing outside the request/response API.

**Motivation:** Kafka consumption, telemetry polling and topology refreshes are long-running activities. Keeping them inside FastAPI would couple API availability to background processing.

**Components:** `causeway-worker` Docker service, AIOKafkaConsumer, consumer group `causeway-worker`, earliest-offset replay, subscriptions to five `signals.*` topics.

**Architecture:**

```
Client → FastAPI → Redpanda → Worker
```

**Communication:** FastAPI produces validated signals. The worker independently consumes them, allowing either component to restart or scale without directly calling the other.

**Without this stage:** The API could accept signals, but nothing would turn those messages into incidents.

**Files:** `worker/main.py`, `worker/__init__.py`, `Dockerfile`, `docker-compose.yml`

---

### Stage 5 — Synthetic microservice mesh and chaos framework

**Goal:** Create controllable distributed-system behavior without production access.

**Motivation:** Topology-aware RCA requires a real request graph and known failure origin.

**Components:** Reusable Go meshgen service, twelve Compose service instances, configurable downstream calls, `/health`, `/metrics` and `/admin/fault`, latency/error/CPU-burn faults, smoke load generator.

**Service graph:**
- frontend → cart, checkout, catalog, search
- cart → inventory, pricing
- checkout → payment, order, inventory
- catalog → inventory, pricing
- search → catalog
- order → notification

**Without this stage:** There would be no multi-hop blast radius, service topology or repeatable payment-service failure to validate RCA.

**Files:** `meshgen/main.go`, `meshgen/fault/fault.go`, `meshgen/Dockerfile`, `meshgen/go.mod`, `meshgen/topology-small.yaml`, `loadgen/smoke.sh`, `docker-compose.yml`

---

### Stage 6 — OpenTelemetry and VictoriaMetrics integration

**Goal:** Observe service interactions instead of relying on static topology files.

**Dependency:** Topology requires traffic. Traffic was supplied by meshgen in Stage 5.

**Motivation:** A configured dependency does not prove that an edge was active during an incident. OTLP traces allow Causeway to derive actual caller-to-callee traffic.

**Components:** Go OTLP/gRPC trace exporter, server and client HTTP instrumentation, trace-context propagation, OpenTelemetry Collector, spanmetrics connector, servicegraph connector, Prometheus remote-write exporter.

**Data flow:**

```
meshgen HTTP spans
       |
OTLP/gRPC
       |
OTel Collector
   |          |
spanmetrics  servicegraph
   \          /
    VictoriaMetrics
```

**Current limitation:** The collector exports derived metrics only. It does not export traces to Tempo or raw spans to Kafka.

**Without this stage:** The worker would have only declared Compose dependencies, not observed runtime edges or latency metrics.

**Files:** `meshgen/otel.go`, `meshgen/main.go`, `deploy/otel/gateway.yaml`, `docker-compose.yml`

---

### Stage 7 — Alerting pipeline

**Goal:** Convert metric threshold violations into operational signals.

**Dependency:** vmalert needs metrics produced by the OTel/VictoriaMetrics stage.

**Components:** `HighServiceLatency` rule, vmalert evaluation, Alertmanager grouping and routing, Alertmanager webhook adapter, `POST /ingest/alerts`, one canonical Signal per firing alert.

**Data flow:**

```
VictoriaMetrics
      |
   vmalert
      |
 Alertmanager
      |
POST /ingest/alerts
      |
signals.alerts
      |
   Worker
```

**Without this stage:** Only manual signals or internally generated detector signals would reach the correlator.

**Files:** `deploy/vmalert/rules.yaml`, `deploy/alertmanager/alertmanager.yml`, `api/routes/ingest.py`, `docker-compose.yml`

---

### Stage 8 — Direct latency detector

**Goal:** Generate trace anomaly signals directly from telemetry.

**Motivation:** The project needed a detector path independent of Alertmanager and an input for `signals.traces`.

**Components:** VictoriaMetrics PromQL polling, configurable latency threshold (later EWMA z-score), worker `detect_loop`, publishing to `signals.traces`.

**Architecture change:** The worker became multiple logical services in one process (consumer, detectors, topology refresher).

**Without this stage:** The `signals.traces` topic would remain unused and RCA would depend solely on Alertmanager.

**Files:** `detectors/latency.py`, `worker/main.py`, `docker-compose.yml`

---

### Stage 9 — Correlation engine and persistent incidents

**Goal:** Compress multiple signals into an incident.

**Dependency:** Correlation needs canonical signals and a continuously running consumer.

**Motivation:** Operators should investigate incidents, not individual alerts.

**Tables activated:** `signal`, `incident`, `incident_signal`

**Data flow:**

```
signals.*
    |
windowBuffer
    |
window expires
    |
signal + incident + incident_signal rows
```

**Without this stage:** Causeway would remain a telemetry forwarding system rather than an incident compression system.

**Files:** `correlator/window.py`, `correlator/db.py`, `worker/main.py`, `loadgen/fault_and_load.sh`

---

### Stage 10 — Incident query APIs

**Goal:** Make generated incidents inspectable.

**APIs:** `GET /api/v1/incidents`, `GET /api/v1/incidents/{incident_id}`, `GET /api/v1/incidents/{incident_id}/candidates`

**Without this stage:** Incidents would exist only as database rows and worker logs.

**Files:** `api/routes/incidents.py`, `api/main.py`, `Makefile`

---

### Stage 11 — RCA v1: severity ranking

**Goal:** Produce the first probable-cause list.

**Dependency:** RCA cannot run until an incident contains signals associated with nodes.

**Algorithm:** For each node, keep its maximum signal severity and rank descending.

**Tables activated:** `cause_candidate`

**Without this stage:** An incident would describe symptoms but provide no localization hypothesis.

**Files:** `localiser/rank.py`, `correlator/window.py`, `correlator/db.py`

---

### Stage 12 — Trace-derived topology persistence

**Goal:** Persist the service graph used by RCA.

**Dependency:** Topology queries depend on servicegraph metrics from Stage 6.

**Components:** PromQL over `traces_service_graph_request_total`, periodic `topology_loop`, `edge_observation` persistence, JSON topology snapshots, stub snapshot fallback, linking each incident to a `snapshot_id`.

**Tables activated:** `edge_observation`, `topology_snapshot`

**Without this stage:** `rank_by_blame` returns no results and RCA falls back to severity ranking.

**Files:** `topology/servicegraph.py`, `topology/persist.py`, `worker/main.py`, `correlator/db.py`, `correlator/window.py`

**Current limitations:** `node_version` is not populated; no Kubernetes ownership graph; correlator still queries recent edges rather than strictly loading the incident’s historical snapshot.

---

### Stage 13 — Topology-aware blame PageRank

**Goal:** Rank likely origins rather than merely the loudest symptoms.

**Dependency:** Blame PageRank requires incident signals plus graph edges.

**Motivation:** A downstream payment failure may trigger severe alerts in frontend and checkout. Severity alone can therefore rank symptoms above the origin.

**Algorithm:**
- Personalization mass comes from signal severity.
- Earlier onset receives an additional boost.
- CALLS edges follow caller → callee.
- A reverse edge models retry or symptom amplification.
- Personalized PageRank is divided by uniform PageRank to reduce structural popularity bias.
- Severity ranking remains the fallback.

**Without this stage:** The project would not demonstrate its central topology-aware RCA claim.

**Files:** `localiser/blame.py`, `correlator/window.py`, `correlator/db.py`

---

### Stage 14 — Evidence pack

**Goal:** Create a stable machine-readable boundary between deterministic RCA and an LLM.

**Dependency:** Evidence cannot be assembled before incidents, candidates and topology exist.

**Components:** `EV-SIG-*`, `EV-RCA-*`, `EV-TOPO-*` entries, incident window and top-cause metadata, `evidence_pack` persistence, `GET /api/v1/incidents/{incident_id}/evidence`.

**Without this stage:** Narration would require direct access to raw telemetry and could invent or misrepresent facts without stable references.

**Files:** `evidence/build.py`, `correlator/window.py`, `correlator/db.py`, `api/routes/incidents.py`, `Makefile`

---

### Stage 15 — Optional OpenAI narration

**Goal:** Translate deterministic evidence into operator-friendly language.

**Dependency:** The narrator is intentionally downstream of the evidence pack. The LLM does not perform RCA.

**Components:** OpenAI asynchronous client, JSON response mode, evidence-reference instructions, `POST /api/v1/incidents/{incident_id}/narrate`, `narrative` table, `OPENAI_API_KEY` feature gate.

**Without this stage:** The RCA system still works, but operators receive structured evidence rather than a concise explanation.

**Files:** `narrator/openai_narrator.py`, `api/routes/incidents.py`, `.env.example`

---

### Stage 16 — Feedback collection

**Goal:** Capture human truth about the actual root cause.

**Dependency:** Feedback has meaning only after Causeway has produced ranked candidates.

**Components:** `POST /api/v1/incidents/{incident_id}/feedback`, `actual_root`, predicted rank lookup, `submitted_by` identity.

**Without this stage:** The team could not measure whether localization was correct or collect labels for future calibration.

**Files:** `api/routes/incidents.py`, `Makefile`, `db/migrations/0001_init.sql`

---

### Stage 17 — Graph visualization surface and benchmarking

**Goal:** Make RCA inspectable and verify the demonstration’s expected root cause.

**Components:** `GET /api/v1/incidents/{incident_id}/graph`, snapshot nodes and edges plus ranked candidates, top-1 benchmark against `svc:payment-svc`, ground-truth seed command.

**Without this stage:** The system could produce a ranking, but engineers could not inspect the graph behind it or run a repeatable acceptance check.

**Files:** `api/routes/incidents.py`, `bench/score_incident.py`, `Makefile`

---

### Stage 18 — Diagnostic action recommendation

**Goal:** Convert RCA output into a safe next investigation step.

**Dependency:** An action requires a top candidate and evidence pack.

**Components:** Handwritten action allow-list, `dump_pool_stats` recommendation, `POST /api/v1/incidents/{incident_id}/actions`, `audit_log` persistence, explicit `applied: false`.

**Without this stage:** Causeway would answer “where should I investigate?” but not “what diagnostic step should I take next?”

**Files:** `actions/suggest.py`, `api/routes/incidents.py`, `Makefile`

**Current limitation (at this stage):** Advisory only. Policy/OPA came later.

---

### Stage 19 — Narrative validator (Phase A)

**Goal:** Stop ungrounded LLM text.

**Problem:** Prompt-only “cite evidence” does not enforce citations.

**Added:** `narrator/validate.py` — dangling `EV-*` refs, uncited claims, numbers not present in cited entries. Wired into `POST .../narrate`. Unit tests.

**Without this:** Hallucinated RCA stories would look authoritative.

**Files:** `narrator/validate.py`, `narrator/test_validate.py`, `api/routes/incidents.py`

---

### Stage 20 — Template narrator + 90s window

**Goal:** Narration must work without OpenAI; correlation window must match cascade time.

**Problem:** Docker often cannot reach OpenAI; 30s windows split one outage.

**Added:** `narrator/template_narrator.py` (facts from pack only). `CORR_WINDOW_SEC=90` in Compose and worker default. JSON helper / GET narrative route.

**Architecture:** LLM is optional. Template is the offline path.

**Without this:** Demos fail whenever the key is missing; incidents fragment.

**Files:** `narrator/template_narrator.py`, `worker/main.py`, `docker-compose.yml`, `Makefile` (`narrate` / `narrative`)

---

### Stage 21 — Offline RCA bench (Phase B)

**Goal:** Regression-test ranking without Docker mesh.

**Added:** Frozen fixtures, `bench/replay.py`, `bench/metrics.py` (top-1 / top-3 floors), `make bench`.

**Without this:** Every detector/correlator change would require a 4-minute live demo.

**Files:** `bench/replay.py`, `bench/metrics.py`, `bench/fixtures/`

---

### Stage 22 — Topology-aware clustering (Phase C)

**Goal:** One window can become **multiple incidents**.

**Problem:** Time-only grouping merges concurrent unrelated outages.

**Added:**
- `correlator/graph.py` — hop distance
- `correlator/affinity.py` — time × graph × kind distance, hop cutoff
- `correlator/cluster.py` — connected components + **HDBSCAN**
- Flush loops **per cluster** (each gets rank + evidence)

**Data flow:** window → distance matrix → clusters → N incidents

**Without this:** Two independent faults in 90s look like one incident.

**Files:** `correlator/{graph,affinity,cluster}.py`, `correlator/window.py`, `bench/replay_correlate.py`

---

### Stage 23 — Statistical detectors (Phase D)

**Goal:** Fire on **distribution shift**, not a hard 200 ms rule.

**Added:** `detectors/baseline.py` (EWMA), `detectors/changepoint.py` (Page-Hinkley onset), `detectors/errors.py`. Latency still has a cold-start absolute floor.

**Worker:** `DETECTORS` tuple — latency + errors (+ later saturation).

**Without this:** Quiet services with high normal latency would false-fire; onset would be “now”, weakening PageRank.

**Files:** `detectors/{baseline,changepoint,latency,errors}.py`, `worker/main.py`

---

### Stage 24 — Dedupe, traffic, Slack, action policy (Phases E–F)

**Goal:** Dual alert+detector paths must not double-count; actions must be gated.

**Added:**
- `correlator/dedupe.py` — merge same-service alert + latency in the window
- `scripts/verify_alerts.sh`, `loadgen/traffic.sh`
- `correlator/notify.py` — optional Slack webhook
- `actions/policy.py` + `deploy/opa/policy.rego` — allowlist, optional OPA

**Without this:** Duplicate signals inflate incidents; any string could be a “suggested action”.

---

### Stage 25 — Saturation, live verify, GitHub CI (Phase G)

**Goal:** Detect load/saturation; prove the live path; lock quality in CI.

**Added:** `detectors/saturation.py`, error bench fixture, `scripts/verify_live.sh`, `.github/workflows/ci.yml` (pytest), OPA Compose profile.

**Without this:** Fault injection would only show up as latency; regressions would be local-only.

---

### Stage 26 — vmagent + fault-aware saturation (Phase H)

**Goal:** Scrape **app metrics**, not only OTel-derived series.

**Problem:** `meshgen_fault_active` lived on `/metrics` but nothing scraped it.

**Added:** `vmagent` + `deploy/vmagent/scrape.yml`. Saturation detector reads `meshgen_fault_active` (severity ~0.85, stable onset). `make verify-mesh-metrics`, `make verify-alerts-live`.

**Architecture:**

```
meshgen /metrics → vmagent → VictoriaMetrics
OTLP traces     → otel-collector → VictoriaMetrics
```

**Without this:** Injected faults would be invisible except through span latency.

---

### Stage 27 — Operator UI + timeline (Phase I)

**Goal:** Incidents must be visible without curling JSON.

**Added:** Static `ui/` served by FastAPI (`/ui`, `/`). `GET .../timeline`. Makefile `make ui`.

**Without this:** The product stays a CLI/API demo.

**Files:** `ui/`, `api/main.py`, `api/routes/incidents.py`

---

### Stage 28 — Feedback loop surfaces (Phase J / J+)

**Goal:** Feedback should be **measurable**, not only stored.

**Added:** `bench/feedback_report.py`, `GET /api/v1/metrics/rca`, `BLAME_*` env weights, UI feedback form, `scripts/live_demo.sh`, alert+latency bench fixture with replay dedupe.

**Still not:** automatic β-weight refit from feedback (report + tunable weights only).

---

### Stage 29 — Auth, worker health, bench in CI (Phase K)

**Goal:** Harden the demo toward production-shaped ops.

**Added:**
- `api/auth.py` — optional `INGEST_API_KEY` / `API_READ_KEY`
- Worker HTTP `/healthz` on **:8085**, heartbeat file, Compose healthcheck
- API `/healthz` can probe worker
- CI `bench-rca` job (`make bench`)
- K8s migration **sketch in docs only**

**Without this:** Open ingest on a shared laptop; worker failures look like “no incidents”.

---

### Stage 30 — Certified E2E + deploy ingest + partition (Phases L / M1)

**Goal:** Repeatable demo certification; a third signal kind; keep disconnected graph components as separate incidents.

**Added:**
- `scripts/demo_e2e.sh`, `e2e_helpers.sh`, `demo_e2e_alerts.sh`
- `POST /ingest/deploy` + `make sample-deploy` + deploy bench fixture
- UI localStorage for API keys
- `correlator/partition.py` — post-cluster split when no graph path within hop limit

**Without this:** Clustering can still glue two islands if affinity is noisy; deploys never enter the bus; live demos stay tribal knowledge.

**Files:** `scripts/demo_e2e*.sh`, `api/routes/ingest.py`, `correlator/partition.py`, `correlator/test_partition.py`

---

==========================
Architecture Evolution
==========================

**Stage 1–4**

```
Client → FastAPI → Redpanda → Worker
         PostgreSQL / VictoriaMetrics
```

**After mesh + OTel**

```
Loadgen → meshgen → OTel Collector → VictoriaMetrics
                         ↓
              FastAPI → Redpanda → Worker → Postgres
```

**After alerts**

```
VM → vmalert → Alertmanager → FastAPI → Kafka → Worker
```

**After detector + topology + PageRank (Aug MVP)**

```
VM ── detect_loop ── Kafka ── window ── incident ── blame PPR
VM ── topology_loop ── edge_observation ─────────────┘
```

**Current (Sep 2026)**

```
meshgen ──OTLP──► otel-collector ──► VictoriaMetrics
   │ /metrics                          ▲
   └──────────► vmagent ───────────────┘
                    │
         ┌──────────┼──────────┐
         ▼          ▼          ▼
   EWMA latency  errors   saturation(+fault_active)
         │          │          │
         └──── signals.* ──────┘
                    │
         Alertmanager webhooks + /ingest/deploy
                    │
                 Redpanda
                    │
              Worker consume
                    │
         dedupe → 90s window
                    │
         affinity + HDBSCAN + graph partition
                    │
         per-cluster: blame PPR → evidence → Slack?
                    │
              PostgreSQL
                    │
         FastAPI + /ui  (optional API keys)
              │
    narrate (OpenAI + validate, else template)
    actions (allowlist + optional OPA)
    feedback-report /metrics/rca
```

Worker process now runs **five** loops: consume, detect, topology, heartbeat, health HTTP.

---

==========================
Developer Learning Journey
==========================

If you were building this project from scratch, implement in this order:

1. **Spec + `understanding.md`** — target vs what actually runs.
   - Required knowledge: AIOps, observability, incident management.
   - Learn: Signal, incident, cause candidate, evidence and narrative.
   - Why first: Data models depend on these definitions.
   - Common mistake: Letting the LLM perform RCA.
   - Test: Agree on example input and expected root cause.

2. **Compose + Makefile** — `make demo-e2e` is the certified path.
   - Required knowledge: Docker Compose, PostgreSQL and Kafka.
   - Learn: Health checks, volumes, advertised listeners.
   - Common mistake: Using localhost addresses inside containers.
   - Test: PostgreSQL query, Kafka topic listing and VM health.

3. **`Signal` model** — still the contract.
   - Required knowledge: Pydantic and event-schema design.
   - Learn: Validation, event timestamps, idempotency and partition keys.
   - Common mistake: Confusing `observed_at` with `onset_at`.
   - Test: Every `SignalKind` maps to the correct topic and rejects invalid nodes.

4. **Mesh + OTel + vmagent** — two metric planes.
   - Required knowledge: tracing, propagation, span kinds, Prometheus scrape.
   - Common mistake: Instrumenting servers but not outbound clients.
   - Test: Confirm frontend→checkout→payment edges in VictoriaMetrics; `make verify-mesh-metrics`.

5. **Detectors** — EWMA + Page-Hinkley + errors + saturation.
   - Test with `pytest detectors/`.
   - Common mistake: Treating one threshold as production anomaly detection.

6. **Worker** — five concurrent tasks.
   - Required knowledge: asyncio, consumer groups, replay.
   - Test: Publish one signal and verify worker consumption.

7. **Correlator** — dedupe → affinity → HDBSCAN → partition → per-cluster RCA.
   - Test `make bench-correlate`.
   - Common mistake: Time-only grouping of concurrent unrelated outages.

8. **Blame weights** — `BLAME_*` env; `localiser/test_blame_weights.py`.
   - Common mistake: Reversing caller/callee direction.
   - Test: Payment ranks above checkout and frontend during payment latency.

9. **Evidence → validate → template/LLM**.
   - Common mistake: Sending raw databases or unrestricted telemetry to an LLM.
   - Test: Every claimable fact has a stable evidence key; validator rejects dangling refs.

10. **UI + auth + policy**.
    - Common mistake: Allowing an LLM to issue unrestricted mutations.

11. **CI** — unit + bench; live E2E stays local.
    - Test before moving on: `make test` → `make bench` → mesh metrics → `make demo-e2e`.

---

==========================
DevOps Journey
==========================

```
Docker
  ↓
Docker Compose (healthchecks, volumes, DNS workaround)
  ↓
PostgreSQL + pgvector schema
  ↓
Redpanda (signals.*)
  ↓
VictoriaMetrics
  ↓
OTel Collector (spanmetrics + servicegraph)
  ↓
vmalert + Alertmanager
  ↓
Background worker (consumer + detectors + topology)
  ↓
vmagent (scrape mesh /metrics)
  ↓
Optional OPA profile
  ↓
Worker liveness :8085 + API health aggregation
  ↓
GitHub Actions (pytest + make bench)
  ↓
Verify ladder: alerts → mesh metrics → alerts-live → demo-e2e
  ↓
Optional Slack / API keys / OPENAI
```

**Operational problems each solved:** local reproducibility; durable incidents; replayable signals; PromQL; traces without Tempo; Prometheus-compatible alerts; async RCA; app-native fault gauges; policy; liveness vs “process is up”; regression without a laptop stack; proof of each integration hop.

**Still missing:** Terraform, Helm, Tempo, Loki, live E2E in CI, HA workers.

| Path | Purpose |
|------|---------|
| `docker-compose.yml` | Full stack definition, healthchecks, volumes |
| `Dockerfile` | API + worker image |
| `deploy/otel/gateway.yaml` | Collector pipelines (spanmetrics, servicegraph) |
| `deploy/vmalert/rules.yaml` | Alert rules |
| `deploy/alertmanager/alertmanager.yml` | Webhook to Causeway API |
| `deploy/vmagent/scrape.yml` | Mesh Prometheus scrape |
| `deploy/opa/policy.rego` | Sample action policy |
| `db/migrations/0001_init.sql` | Schema bootstrap on Postgres init |
| `.github/workflows/ci.yml` | Unit tests + RCA bench |

---

==========================
Feature Dependency Graph
==========================

```
Health endpoint
      │
      ▼
Signal ingest ──► Kafka ──► Worker consume
      │
Mesh + OTel ──► VM ──► Topology loop
      │
      ├── vmalert → AM → /ingest/alerts
      ├── EWMA latency / errors / saturation(+fault scrape)
      └── /ingest/deploy
              │
              ▼
         Dedupe in window
              │
              ▼
         90s correlator window
              │
              ▼
    Affinity + HDBSCAN + graph partition
              │
              ▼
         Incident(s)  (one per cluster)
              │
              ▼
         Blame PageRank (severity fallback)
              │
              ▼
         Candidates + Evidence pack
              │
    ┌─────────┼─────────┬──────────┐
    ▼         ▼         ▼          ▼
  Graph     Timeline   Slack     UI
    │
    ├─► Narrate (validate; template if no LLM)
    ├─► Action (policy / optional OPA)
    ├─► Feedback → feedback-report / /metrics/rca
    └─► Bench fixtures + CI + demo-e2e
```

**Hard dependencies:**

- We cannot build RCA until we have Signals because signals are the input.
- We cannot build topology-aware RCA until we have trace-derived edges.
- We cannot build Evidence Pack until RCA candidates exist.
- We cannot narrate incidents until Evidence Packs are generated.
- Action recommendation requires evidence and a top candidate.
- Feedback requires a prediction to evaluate.
- Automated learning cannot begin until sufficient feedback exists.
- No traces/metrics → no topology → blame falls back to severity.
- No clustering/partition → concurrent faults merge.
- Auth is optional; empty keys keep the open demo.

---

## Honest current state

Causeway is now a **local, interview-grade AIOps MVP**, not a Compose sketch:

- Dual telemetry (OTel + Prometheus scrape)
- Three detector families + Alertmanager + deploy ingest
- Topology-aware **HDBSCAN** + **partition split**
- Blame PageRank with tunable weights
- Grounded narration (validator + template)
- Operator UI, optional keys, optional Slack/OPA
- Unit tests, fixture benches, GitHub CI, certified `make demo-e2e`

Largest remaining gaps vs `02-causeway.md`: K8s informers, Drain3/Loki/Tempo, true seasonal baselines, snapshot-at-T, embedding affinity, conformal calibration, feedback **refit**, mutating actions, cloud IaC.

Treat **`understanding.md` phases A–M1 as the implemented product** and the 1059-line spec as the roadmap.

---

## Related docs

- `README.md` — quick demo commands
- `understanding.md` — plain-language guide, phase table, build log
- `02-causeway.md` — full target architecture
- `db/migrations/0001_init.sql` — database schema
