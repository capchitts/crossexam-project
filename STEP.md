# Step 4: a shared database, an API and a screen

**What step 3 showed:** the right answer -- `PO-40002` needs a debit note, `PO-40010` is clean -- printed to one terminal, on one laptop, gone the moment it closed.

**The goal of this step:** put that same answer somewhere more than one person can see it, and give a screen a way to ask for it. Nothing about *how* a paper is read, split, filled, checked, grouped or matched changes -- that is still exactly step 3's code (`ladder/step3/`), called the same way. What changes is where the answer goes afterwards.

| New file | What it does | Is it new logic? |
|---|---|---|
| `app/config.py`, `app/db/session.py`, `app/db/models.py` | The real settings and tables the finished system (`main`) uses. | No -- the exact files from `main`. |
| `app/ingestion/storage.py` | Saves an uploaded file's bytes once, by its fingerprint. | No -- the exact file from `main`. |
| `ladder/step4/pipeline.py` | Step 3's `b_split.py` + `c_check.py`, taking bytes from an upload instead of a path on disk. | No -- same functions, same prompts. |
| `ladder/step4/orchestrate.py` | Step 3's `d_group.py` + `e_match.py`, writing `Batch` / `Document` / `ShipmentPack` rows instead of printing. | The only genuinely new code in this step. |
| `ladder/step4/api.py` | Three routes: upload, list batches, list a batch's shipments. | New, but each route is a few lines calling `orchestrate.py`. |
| `ladder/step4/web.py` | One HTML page, no build step, no framework. | New, and deliberately small -- see "Why not the real screen?" below. |

## Run it

```bash
make up      # build and start Postgres (5433) + the API/screen (8010)
make demo    # load PO-40002 and PO-40010 straight into the database
```
```
batch 7e6c...: 9 file(s) loaded.
Open http://localhost:8010 to see the shipments.
```
Open **http://localhost:8010**. The batch you just loaded is the first row; click it and the two shipments appear:
```
PO-40002   investigate       billed 700,010.85   pay 678,300.00   debit note 21,710.85
PO-40010   auto_approve      billed  92,040.00   pay  92,040.00   debit note      0.00
```
Both match `demo-data/ground_truth.json` exactly -- the same two numbers step 3 printed to the terminal.

## Upload through the screen

Drag any file from `demo-data/files/` onto the upload box (even one that is already loaded -- a repeat is still accepted as a new batch here; de-duplicating *across* batches is step 5's job, once there is a queue to hold the work while it checks). A new row appears in **Batches** within a few seconds, and clicking it shows its own shipments.

The same thing works from a terminal, with no screen at all:
```bash
curl -F "files=@demo-data/files/0002_bundle_scan.pdf" \
     -F "files=@demo-data/files/0002_coa_1.pdf" \
     -F "files=@demo-data/files/0002_ewaybill.pdf" \
     http://localhost:8010/batches
```
**Notice:** the screen is not special. It calls the exact same `POST /batches` that `curl` just called. There is no logic that only the browser can reach.

## What a row looks like

After `make demo`, `docker compose exec postgres psql -U crossexam -c "select po_number, route, invoice_total, payable_amount from shipment_packs;"` shows:
```
 po_number | route       | invoice_total | payable_amount
-----------+-------------+---------------+----------------
 PO-40002  | investigate |     700010.85 |      678300.00
 PO-40010  | auto_approve|      92040.00 |       92040.00
```
This is the same table the finished system's screen (the real React app on `main`) reads from. Step 4 does not change the shape of the answer -- only how far away from the terminal it can now be seen.

## A doubt worth saying out loud

*"Why not just build the real React screen (`web/` on `main`) now, instead of a new one-page screen?"* Because the real screen also expects routes this step has not built yet -- approving a shipment, exporting it, seeing a live queue -- and wiring it to only three routes would mean either a broken app or a lot of code whose only job is to hide missing features. This step's screen is small on purpose: it proves the database and the API work, and nothing more. `build/step-6-agents-approval` is where approving a shipment first matters, and that is also where reusing the real screen starts paying off.

## What it still gets wrong

Every upload runs inside the one request that received it -- read, split, fill, check, group, match, all before the browser gets a response. Nine files already take a few seconds; a month-end batch of thousands would make that one request wait minutes, and a restart of the API mid-upload would lose whatever had not been written yet. `build/step-5-queue` answers this: the request returns immediately, and workers do the actual reading in the background, picking the work back up if one of them dies partway through.
