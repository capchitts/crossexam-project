.PHONY: setup check up demo down reset logs kill-reader
setup:  ## create .env from the template (never overwrites an existing one)
	@test -f .env && echo ".env already exists" || (cp .env.example .env && echo "Created .env: put your Gemini key in it")
check:  ## prove Docker, the papers and (if set) the key work
	./run.sh check.py

# --- step 5: a queue ---------------------------------------------------------------------------
up:  ## build and start Postgres, Redis, the API/screen and two worker pools for step 5
	docker compose up --build -d
	@echo "Screen + API  http://localhost:8011   (Swagger at /docs)   Postgres 5434   Redis 6380"
demo:  ## upload PO-40002 and PO-40010 through the real API; the request returns at once
	docker compose run --rm api python ladder/step5/seed_demo.py
logs:  ## watch both worker pools pick up work
	docker compose logs -f --tail=50 worker-reader worker-agent
kill-reader:  ## kill the reader worker mid-batch, to watch its task get redelivered (upload a batch first)
	docker compose kill -s SIGKILL worker-reader
	docker compose up -d worker-reader
down:  ## stop step 5's stack
	docker compose down
reset:  ## stop step 5's stack and delete the database
	docker compose down -v
