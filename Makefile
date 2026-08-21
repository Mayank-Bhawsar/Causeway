.PHONY: help up down build logs demo score graph health seed-gt feedback

API      ?= http://localhost:8000
EXPECTED ?= svc:payment-svc

help:
	@echo "Targets:"
	@echo "  make up        - start stack"
	@echo "  make down      - stop stack"
	@echo "  make build     - rebuild api + worker"
	@echo "  make health    - hit /healthz"
	@echo "  make demo      - inject payment fault + load"
	@echo "  make score     - score latest incident top-1"
	@echo "  make graph     - print latest incident graph"
	@echo "  make seed-gt   - insert payment_latency ground truth"
	@echo "  make logs      - follow worker logs"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose up -d --build causeway-api causeway-worker

health:
	curl -s $(API)/healthz | python3 -m json.tool

demo:
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