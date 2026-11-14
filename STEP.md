# Step 5: a queue

**What step 4 showed:** the answer in a shared database, reachable over HTTP -- but every paper was read inside the one request that uploaded it. Nine papers already took a few seconds; a restart mid-upload would lose whatever had not been written yet.

**The goal of this step:** the request returns the moment the files are saved and fingerprinted, and two worker pools do the actual reading and matching in the background -- picking the work back up if one of them dies partway through.

| New file | What it does | Is it new logic? |
|---|---|---|
| `ladder/step5/celery_app.py` | Queue names, priorities and resilience settings. | No -- the same shape as main's real `app/workers/celery_app.py`; see its own docstring for why this step does not import main's file directly (it eagerly pulls in step 6's agents and step 7's observability). |
| `ladder/step5/tasks.py` | Two Celery tasks: `read_one` (step 3a/b/c, one task per uploaded file) and `finalize_batch_task` (step 3d/3e, one task per batch, queued once every file in it is read). | The queueing is new; what each task *does* is step 4's `pipeline.py` and `match.py`, unchanged. |
| `ladder/step5/match.py` | Step 4's `orchestrate.py` group+match half, reading saved `Extraction` rows from Postgres instead of an in-memory list. | No -- same two functions (`group`, `snapshot`), same `run_match` call. |
| `ladder/step5/api.py` | The upload route now saves and fingerprints files, then enqueues `read_one` per file and returns. | Only the "then enqueue and return" part is new; the three read-only routes are exactly step 4's. |

## A bundle, for real this time

Step 3 and step 4 only ever showed `0002_bundle_scan.pdf` splitting into three papers on a terminal or in memory. This step is the first one to actually *write* that split to the database, because now a worker reads the file on its own, with no shared memory to hold "the three papers it found." main's own schema already has the rule for this: `app/db/models.py`'s `Document.parent_id` and `DocStatus.split` ("parent of split children; terminal for the parent itself"). `tasks.py:read_one` uses that rule directly: one paper -> the same Document row is marked `extracted`; several papers -> the Document is marked `split` and becomes the parent of one child Document per paper, each with its own `Extraction` row.

## Run it

```bash
make up
make demo
```
```
batch eccae13c-1a64-4bcc-88ad-739128784498: 9 file(s) queued, 0 already seen.
The request returned immediately -- nothing has been read yet. Watching for the workers to finish...
grouped after the workers finished.
```
Measured end to end (`time docker compose run --rm api python ladder/step5/seed_demo.py`): **3.7 seconds**, container start-up included. `curl http://localhost:8011/batches/<id>/shipments` gives:
```json
[{"po_number": "PO-40002", "route": "investigate", "payable_amount": "678300.00", "debit_note_amount": "21710.85"},
 {"po_number": "PO-40010", "route": "auto_approve", "payable_amount": "92040.00", "debit_note_amount": "0.00"}]
```
The same two numbers steps 3 and 4 printed.

## Kill a worker mid-batch, for real

```bash
docker compose run --rm api python ladder/step5/seed_all.py   # a bigger upload: 42 new papers
make kill-reader                                                # SIGKILL worker-reader, then start it again
```
A real run, timestamped:
```
23:17:58  worker-reader killed (SIGKILL), mid-batch
23:18:03  worker-reader started again
23:18:10  batch status: grouped
```
Twelve seconds from the kill to a finished batch -- under the 20-second visibility timeout this demo sets on the Redis broker (main's own default is one hour; see `celery_app.py`). The papers the killed worker had not finished reading were never acknowledged, so Redis redelivered them once a reader worker was listening again. Nothing was lost; nothing needed to be re-uploaded.

**A note on the 20-second number:** it is a demo setting, not a magic constant. A real deployment tunes the visibility timeout to the longest a single task should ever legitimately take (main's one hour accounts for a very large vision page or a very slow model response); a shorter timeout here just means a crashed worker's work resurfaces faster, which is what makes this watchable in a few seconds instead of up to an hour.

## A doubt worth saying out loud

*"If the API container restarts between saving a file and enqueueing its task, is that file lost?"* No -- the file and its `Document` row are committed to Postgres *before* `enqueue_document` is called (see `api.py`'s comment: "Queue only AFTER the commit"). A crash in that narrow window would leave a `Document` row with status `queued` and no task ever sent for it -- step 7's "seeing inside" is where a stuck-looking batch like that becomes visible and `reap_stale`-style sweeping (main's real job for exactly this) would belong. This step does not build that sweep; it only builds the queue the sweep would act on.

## What it still gets wrong

A clean shipment is auto-approved and a problem shipment is marked `needs_review` -- but nothing decides *what to do* about the problem, and nothing routes it to the one person who may approve it. And now that work moves through a queue, there is no way to see how much is queued, which worker is doing what, or why a batch that should take seconds is taking minutes. `build/step-6-agents-approval` (coming) answers the first; `build/step-7-see-inside` (coming) answers the second.
