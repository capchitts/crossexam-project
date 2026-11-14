# Step 7: seeing inside

**What step 6 showed:** a real agent explaining a problem, and a real role-gated approval. Nothing about *how the work was moving* was visible -- not the queue, not a worker, not a single number.

**The goal of this step:** make "is it stuck, or just busy?" answerable with a real number, not a guess.

| New file | What it does | Is it new logic? |
|---|---|---|
| `app/observability/logging.py`, `metrics.py`, `tracing.py` | Structured JSON logs, the real OpenTelemetry metric instruments, OTel tracing setup. | No -- the exact files from `main`. |
| `monitoring/prometheus.yml`, `monitoring/grafana/...` | Scrape config and the stock dashboard. | No -- the exact files from `main`. |
| `ladder/step7/tasks.py` | Binds ids to the logger and records the real metrics around `read_one` and `finalize_batch_task`. | The binding/recording calls are new; the task bodies are step 5/6's, unchanged. |
| `ladder/step7/api.py` | Adds `/metrics`, `/readyz`, `/queues`. | New, each a few lines. |

## Two separate places to look, on purpose

`prometheus.yml` has two scrape jobs:
```yaml
- job_name: api
  metrics_path: /metrics
  static_configs: [{ targets: ["api:8000"] }]
- job_name: workers
  dns_sd_configs:
    - names: [worker-reader, worker-agent]
      type: A
      port: 9100
```
This is main's own design, not something this step invented: the API and the two worker pools are separate Python processes, each with its own in-process metrics registry. A counter a worker increments is never visible on the API's `/metrics` -- it is visible on that worker's own port 9100. Prometheus scrapes both, which is how a dashboard sees the whole system; `curl`ing only `/metrics` on the API shows almost nothing, by design, not by bug.

## Run it

```bash
make up
make demo
```
Real numbers, read straight from the running stack after one 9-file upload:
```
curl http://localhost:9101/ | grep crossexam_documents_processed
  crossexam_documents_processed_total{doc_type="quality_certificate",outcome="read"} 3.0
  crossexam_documents_processed_total{doc_type="eway_bill",outcome="read"} 2.0
  crossexam_documents_processed_total{doc_type="invoice",outcome="read"} 2.0
  crossexam_documents_processed_total{doc_type="packing_list",outcome="read"} 2.0
  crossexam_documents_processed_total{doc_type="lorry_receipt",outcome="read"} 2.0

curl http://localhost:9102/ | grep crossexam_packs_routed
  crossexam_packs_routed_total{route="investigate"} 1.0
  crossexam_packs_routed_total{route="auto_approve"} 1.0

curl http://localhost:8013/queues
  {"reader.urgent":0,"reader.normal":0,"reader.bulk":0,"agent.urgent":0,"agent.normal":0,"agent.bulk":0}
```
11 papers from 9 files (`0002_bundle_scan.pdf` alone splits into 3), two shipments, both numbers agreeing with every earlier step. A real structured log line, from the same run:
```json
{"papers": 1, "remaining_in_batch": 0, "event": "read_one done", "task": "read_one",
 "batch_id": "ccd25bf9-...", "document_id": "18e2927c-...", "filename": "0010_lr_scan.pdf",
 "level": "info", "timestamp": "2026-11-14T18:56:15.140013Z", "severity": "INFO"}
```

## Flower, for real

Open **http://localhost:5556/tasks**. A real run shows ten real rows: nine `tasks.read_one` (one per file, on `worker-reader`, 16-171ms each) and one `tasks.finalize_batch_task` (on `worker-agent`, 1.92s -- this one calls the supervisor agent, so it is the slow one). A screenshot of this exact run is in `teaching/`'s reference material for this step.

## Prometheus and Grafana, opt in

```bash
make monitoring
```
This downloads `prom/prometheus` and `grafana/grafana` the first time -- about 0.6 GB together -- which is why it is not part of `make up`. main's own `docker-compose.yml` gates these two services behind the identical `--profile monitoring`, for the identical reason, stated in its own first-line comment. Grafana opens at `http://localhost:3001` with the dashboard `monitoring/grafana/dashboards/crossexam.json` already provisioned, reading from Prometheus at `http://localhost:9091`.

## What was not run

- **LangSmith** (prompt-level and tool-call detail inside the supervisor agent's own run) needs its own API key in `.env`. It was not set for this step, so LangSmith was not run; `otel_exporter` stays `none`, so OpenTelemetry tracing was not run either, and no trace backend was contacted.
- **The Grafana dashboard with a real backlog behind it.** The dashboard shown is the stock one copied from `main`; nobody has pointed it at a genuinely large, slow batch to see whether its panels are the right ones to be looking at.

## What it still gets wrong

A refused approval (step 6's 403) still writes nothing anywhere -- there is no metric or log line for "someone tried and was stopped." And everything so far still runs on one laptop, with no record of *what it would take* to run somewhere else. `build/step-8-cloud` (coming) is where that gets written down as code -- not run, but validated.
