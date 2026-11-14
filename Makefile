.PHONY: setup check up monitoring demo down reset logs kill-reader
setup:  ## create .env from the template (never overwrites an existing one)
	@test -f .env && echo ".env already exists" || (cp .env.example .env && echo "Created .env: put your Gemini key in it")
check:  ## prove Docker, the papers and (if set) the key work
	./run.sh check.py

# --- step 7: seeing inside -------------------------------------------------------------------------
up:  ## build and start Postgres, Redis, the API/screen, both worker pools and Flower
	docker compose up --build -d
	@echo "Screen + API  http://localhost:8013   (Swagger at /docs, metrics at /metrics, queues at /queues)"
	@echo "Flower        http://localhost:5556     Postgres 5436   Redis 6382"
monitoring:  ## also start Prometheus and Grafana (downloads ~0.6 GB the first time; asks nothing, just takes a while)
	docker compose --profile monitoring up --build -d
	@echo "Prometheus    http://localhost:9091     Grafana  http://localhost:3001  (admin/crossexam, or anonymous Viewer)"
demo:  ## upload PO-40002 and PO-40010 through the real API; the request returns at once
	docker compose run --rm api python ladder/step7/seed_demo.py
logs:  ## watch both worker pools pick up work
	docker compose logs -f --tail=50 worker-reader worker-agent
kill-reader:  ## kill the reader worker mid-batch, to watch its task get redelivered (upload a batch first)
	docker compose kill -s SIGKILL worker-reader
	docker compose up -d worker-reader
down:  ## stop step 7's stack
	docker compose down
reset:  ## stop step 7's stack and delete the database
	docker compose down -v
