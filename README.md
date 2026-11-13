# CrossExam, one step at a time

The same system as the course, built up in small steps. Every step is a **branch** you can check out and run. Each branch adds one idea to the one before it, and only when the step before it showed a problem that idea answers.

**The use case.** Kaveri Distributors receives a shipment as a pile of papers (scans, PDFs, photos, spreadsheets, government files). The software must turn them into one decision: *is the supplier asking for the right amount, and what do we pay?* The papers, the purchase orders and the answer key are in `demo-data/` and are invented.

## Start here
```bash
git clone <this repository>
cd <your clone of the repository>
git switch build/step-0-start       # the setup
make setup                    # creates .env: put your Gemini key in it (only steps that call a model need it)
make check                    # proves Docker, the papers and (optionally) the key work
```
Then move one step at a time: `git switch build/step-1-one-agent`, read `STEP.md`, run what it says.
To see exactly what a step added: `git diff build/step-1-one-agent..build/step-2-three-fixes --stat`.

## The steps
| Branch | What is new | Runs |
|---|---|---|
| `build/step-0-start` | Docker image, the papers, `make check` | locally |
| `build/step-1-one-agent` | One LangChain agent reads a paper and fills a form | locally, needs a key |
| `build/step-2-three-fixes` | A kind of paper, a fingerprint, saved results | locally, needs a key |
| `build/step-3-plain-code` | Read cheaply, split bundles, check, group, match: plain code around the model | locally, needs a key |
| `build/step-4-api-db-screen` | FastAPI, PostgreSQL and the React screen | coming |
| `build/step-5-queue` | Celery and Redis | coming |
| `build/step-6-agents-approval` | Investigating agents and approval by role | coming |
| `build/step-7-see-inside` | Flower, metrics, traces, LangSmith | coming |
| `build/step-8-cloud` | Terraform and Kubernetes | coming, not run |

Smaller moves inside a step are **tags** (for example `build/step-3c-check`): `git checkout build/step-3c-check`.

## Rules we keep
- Your key lives only in `.env`, which git ignores.
- Nothing here calls the cloud. Every step runs on your machine.
- Every number printed in a `STEP.md` came from a real run of that branch.
