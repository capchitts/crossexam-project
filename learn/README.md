# Learn CrossExam step by step (this branch only)

This branch adds one folder, `learn/`. It changes **no project file**: the `main` branch is the real project and stays as it is. Everything here is small scripts that call the real code and print what happened, so you can see each part work on its own before meeting the whole system.

## How to run a lesson
```bash
git switch learn/step-by-step         # you are here
make setup                            # once: creates .env (put your Gemini key in it; only lesson 4 needs it)
make up                               # once: builds the image and starts the system (a few minutes the first time)
./learn/run.sh part-3-reading-the-papers/01_what_came_in.py
```
`run.sh` runs the script inside the project's own image, so nothing else needs installing. The papers come from `demo-data/` (the exact 51 files used in the course).

To go back to the full project: `git switch main`.

## Where things live (the whole project on one screen)
| Folder | What is in it | In plain words |
|---|---|---|
| `app/ingestion/` | `readers.py`, `storage.py` | open a file and say what format it is |
| `app/agents/` | `vision.py`, `agents.py`, `prompts.py`, `tools/` | the parts that call a model |
| `app/rules/` | `validation.py`, `normalize.py`, `dedupe.py`, `match_engine.py` | plain checks: exact, free, no model |
| `app/services/` | `pipeline.py`, `grouping.py`, `packs.py` | the order of the steps, and grouping papers into a shipment |
| `app/api/` | `main.py` | the 17 endpoints the screen and other programs call |
| `app/db/` | `models.py`, `seed.py` | the tables in PostgreSQL |
| `app/workers/` | `celery_app.py`, `tasks.py`, `ratelimit.py` | the queue: work that waits its turn |
| `app/observability/` | `metrics.py`, `tracing.py`, `logging.py` | what happened, and how long it took |
| `web/` | React pages | the screen |
| `ladder/` | `step1_one_agent.py`, `step2_three_small_fixes.py` | the first two steps, as readable scripts |
| `demo-data/` | 51 papers, master data, answer key | the invented shipments of Kaveri Distributors |
| `infra/` | Terraform, Kubernetes | the cloud (not covered here) |
| `learn/` | this folder | lessons, one question each |

## The lessons
| Part | Lessons | Status |
|---|---|---|
| Reading the papers | 5 lessons, about 3 minutes each | ready: `part-3-reading-the-papers/` |
| The cross-examination | grouping, matching, agents | to come |
| Safeguards and people | approval and roles | to come |
| Volume and trust | queue, numbers, evaluation | to come |
