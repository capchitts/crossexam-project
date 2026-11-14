.PHONY: setup check up demo down reset logs kill-reader
setup:  ## create .env from the template (never overwrites an existing one)
	@test -f .env && echo ".env already exists" || (cp .env.example .env && echo "Created .env: put your Gemini key in it")
check:  ## prove Docker, the papers and (if set) the key work
	./run.sh check.py

# --- step 6: agents and approval -----------------------------------------------------------------
up:  ## build and start Postgres, Redis, the API/screen and two worker pools for step 6
	docker compose up --build -d
	@echo "Screen + API  http://localhost:8012   (Swagger at /docs)   Postgres 5435   Redis 6381"
demo:  ## upload PO-40002 and PO-40010 through the real API; the request returns at once
	docker compose run --rm api python ladder/step6/seed_demo.py
logs:  ## watch both worker pools pick up work
	docker compose logs -f --tail=50 worker-reader worker-agent
kill-reader:  ## kill the reader worker mid-batch, to watch its task get redelivered (upload a batch first)
	docker compose kill -s SIGKILL worker-reader
	docker compose up -d worker-reader
down:  ## stop step 6's stack
	docker compose down
reset:  ## stop step 6's stack and delete the database
	docker compose down -v
