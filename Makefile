.PHONY: help up down build build-fast dns-fix logs demo score graph health seed-gt feedback evidence action narrate narrative

API      ?= http://localhost:8000
EXPECTED ?= svc:payment-svc
# WSL2 + missing /etc/resolv.conf breaks BuildKit ([::1]:53). Legacy builder works.
export DOCKER_BUILDKIT ?= 0

help:
	@echo "Targets:"
	@echo "  make up        - start stack"
	@echo "  make down      - stop stack"
	@echo "  make build     - rebuild api + worker"
	@echo "  make dns-fix   - fix WSL DNS (sudo once, then wsl --shutdown)"
	@echo "  make verify-dns - test container DNS + API health"
	@echo "  make health    - hit /healthz"
	@echo "  make demo      - inject payment fault + load"
	@echo "  make score     - score latest incident top-1"
	@echo "  make graph     - print latest incident graph"
	@echo "  make seed-gt   - insert payment_latency ground truth"
	@echo "  make logs      - follow worker logs"
	@echo "  make evidence  - print latest evidence pack"
	@echo "  make action    - propose diagnostic action"
	@echo "  make narrate   - generate OpenAI narrative"
	@echo "  make narrative - fetch stored narrative"

up:
	docker compose up -d

down:
	docker compose down

build:
	DOCKER_BUILDKIT=0 docker compose up -d --build causeway-api causeway-worker

build-fast:
	DOCKER_BUILDKIT=1 docker compose up -d --build causeway-api causeway-worker

dns-fix:
	@echo "Run in WSL: sudo bash scripts/setup-wsl-dns.sh"
	@echo "Then in PowerShell: wsl --shutdown"
	@echo "Restart Docker Desktop, then: make build-fast"

verify-dns:
	bash scripts/verify-docker-dns.sh

health:
	curl -s $(API)/healthz | python3 -m json.tool

demo:
	@curl -sf -m 3 http://localhost:8081/ >/dev/null || { \
	  echo "payment-svc not reachable on :8081 — run: make up"; exit 1; }
	bash loadgen/fault_and_load.sh 90 500

# latest incident id from API
INC = $$(curl -s $(API)/api/v1/incidents | python3 -c "import sys,json; print(json.load(sys.stdin)['incidents'][0]['incident_id'])")

score:
	@INC=$(INC); \
	echo "scoring $$INC"; \
	docker compose exec causeway-api python -m bench.score_incident \
	  --incident-id $$INC --expected $(EXPECTED)

graph:
	@INC=$(INC); \
	echo "graph $$INC"; \
	curl -s "$(API)/api/v1/incidents/$$INC/graph" | python3 -m json.tool | head -80

seed-gt:
	docker compose exec postgres psql -U causeway -d causeway -c \
	  "INSERT INTO ground_truth (scenario, true_root, onset_at, blast) \
	   VALUES ('payment_latency', 'svc:payment-svc', now(), \
	           ARRAY['svc:checkout-svc','svc:frontend']) \
	   ON CONFLICT (scenario) DO UPDATE SET true_root = EXCLUDED.true_root;"

logs:
	docker compose logs -f causeway-worker

feedback:
	@INC=$(INC); \
	curl -s -X POST "$(API)/api/v1/incidents/$$INC/feedback" \
	  -H 'Content-Type: application/json' \
	  -d '{"actual_root":"svc:payment-svc","submitted_by":"local"}' \
	  | python3 -m json.tool

evidence:
	@INC=$(INC); \
	echo "evidence $$INC"; \
	curl -s "$(API)/api/v1/incidents/$$INC/evidence" | python3 -m json.tool | head -100

action:
	@INC=$(INC); \
	echo "action $$INC"; \
	curl -s -X POST "$(API)/api/v1/incidents/$$INC/actions" | python3 -m json.tool

narrate:
	@INC=$(INC); \
	echo "narrate $$INC"; \
	curl -sS -X POST "$(API)/api/v1/incidents/$$INC/narrate" | python3 -m json.tool

narrative:
	@INC=$(INC); \
	echo "narrative $$INC"; \
	curl -sS "$(API)/api/v1/incidents/$$INC/narrative" | python3 -m json.tool