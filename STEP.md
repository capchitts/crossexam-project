# Step 3: plain code around the model

**What step 2 showed:** a three-paper bundle got one form (and not always the same one), one lorry was written two ways, and nothing compared the invoice with the order.

**The goal of this step:** fix that with ordinary code, one small move at a time. The model still reads, but code decides what is read, how papers are split, what is valid, which papers belong together and whether the money is right. Each move is a tag you can check out.

| Tag | Move | Model needed? |
|---|---|---|
| `build/step-3a-read-cheaply` | pick the cheapest reader for each format | no |
| `build/step-3b-split` | read the scans, split a bundle into its papers | vision, on 4 pages |
| `build/step-3c-check` | fill one form per paper, check it with code | yes |
| `build/step-3d-group` | put the papers of one shipment together | no |
| `build/step-3e-match` | compare the invoice with the order, exactly | no |

All five scripts are in `ladder/step3/`. They call the same real modules the full system uses (`app/ingestion/readers.py`, `app/rules/`, `app/services/grouping.py`, `app/schemas.py`).

---

## 3a. Read cheaply (`git checkout build/step-3a-read-cheaply`)
Only scans and photos need a vision model. Everything else can be read for free.
```bash
./run.sh ladder/step3/a_read.py
```
```
  0002_bundle_scan.pdf   scanned_pdf  fingerprint 214b2588   pages for a vision model: 3
  0002_coa_1.pdf         digital_pdf  fingerprint c79ffc7c   pages for a vision model: 0
  0010_einvoice.json     gov_json     fingerprint d7c772a8   pages for a vision model: 0
  0010_lr_scan.pdf       scanned_pdf  fingerprint d1b71151   pages for a vision model: 1
  ...
All 51 papers: {'scanned_pdf': 8, 'digital_pdf': 26, 'gov_json': 10, 'image': 3, 'spreadsheet': 4}
Papers that need the vision model: 11 (15 pages). Government JSON needs no model at all: 10.
```
**Notice:** a 2,034-byte PDF is real text; a 237,255-byte PDF is a picture. The rule is plain: a PDF is digital only if every page holds at least 40 characters of text. Only **11 of 51** papers (15 pages) need the vision model.

---

## 3b. Split a bundle (`git checkout build/step-3b-split`)
A scan has no text, so the vision model copies each page into text. The answer is saved, so a second run is free and prints the same thing. Then **plain code** decides where one paper ends: a page that starts with a title (`TAX INVOICE`, `PACKING LIST`, `LORRY RECEIPT`, ...) starts a new paper; a page with no title continues the one before.
```bash
./run.sh ladder/step3/b_split.py        # first run: 4 pages go to the vision model
./run.sh ladder/step3/b_split.py        # second run: nothing is called
```
```
0002_bundle_scan.pdf   read by vision  3 page(s) -> invoice (pages 1-1), packing_list (pages 2-2), lorry_receipt (pages 3-3)
0002_coa_1.pdf         read by text    1 page(s) -> quality_certificate (pages 1-1)
0002_ewaybill.pdf      read by text    1 page(s) -> eway_bill (pages 1-1)
0010_einvoice.json     government JSON, already a form: invoice
0010_lr_scan.pdf       read by vision  1 page(s) -> lorry_receipt (pages 1-1)
...
```
First run 12 seconds for the whole command; second run 2 seconds.

**Notice:** the three-paper scan is now three papers, and the invoice of PO-40002 is back. **What is AI here and what is not:** the model only copies a page into text. *Where a paper ends* is a rule you can read in `title_kind` and `split_papers`. (The full system asks a model to propose the split, then repairs it with code. Plain rules are enough for these papers and give the same answer every run.)

**A doubt worth saying out loud:** *"What if a bundle has a page with no title and no continuation?"* It joins the paper before it, or becomes `other` if it is the first. That is a rule you chose, so you can change it and rerun for free.

---

## 3c. Fill one form per paper, check it with code (`git checkout build/step-3c-check`)
For each paper the model fills the matching form (the same forms the full system uses, in `app/schemas.py`). The answer is saved, so a second run is free and identical. Government JSON is copied by code and needs no model. Then **plain code** checks every form with `validate` (`app/rules/validation.py`): required fields, a valid tax ID check digit, each line, the subtotal, the tax, the total.
```bash
./run.sh ladder/step3/c_check.py        # first run: one model call per paper that is not government JSON
./run.sh ladder/step3/c_check.py        # again: every line says "saved", nothing is called
```
```
0002_bundle_scan.pdf   model  invoice SI/26-27/56132  PO PO-40002  total 700010.85           checks: ok
0002_bundle_scan.pdf   model  packing list PL-29901  for invoice SI/26-27/56132              checks: ok
0002_bundle_scan.pdf   model  lorry receipt LR561504  vehicle KA28 JQ 4940                   checks: ok
0002_ewaybill.pdf      model  e-way bill 742795434833  vehicle KA28 JQ 4940                  checks: ok
0010_einvoice.json     code   invoice SI/26-27/14044  PO PO-40010  total 92040.0             checks: ok
0010_ewaybill.json     code   e-way bill 394144262876  vehicle KL19KI5987                    checks: ok
0010_lr_scan.pdf       model  lorry receipt LR587234  vehicle KL19 KI 5987                   checks: ok
...  (eleven papers from nine files)
```
First run 15 seconds for the whole command; second run 3 seconds. Eleven papers, all checks ok.

**See what the checks catch.** Pretend the model read every invoice total 1,000 too high (no model is called):
```bash
./run.sh ladder/step3/c_check.py --misread
```
```
0002_bundle_scan.pdf   saved  invoice SI/26-27/56132  PO PO-40002  total 701010.85           checks: ['total_mismatch']
0010_einvoice.json     code   invoice SI/26-27/14044  PO PO-40010  total 93040.0             checks: ['total_mismatch']
```
**Notice:** subtotal plus tax no longer equals the total, so code names the check that failed. Exact, free, and explainable.

**What the checks do not catch.** Pretend PO-40002 was read as `PQ-40002`:
```bash
./run.sh ladder/step3/c_check.py --bad-po
```
`checks: ok`. Nothing looks at the PO number. Plain code only catches what someone wrote a rule for.
**Try it:** in `app/rules/validation.py`, function `_invoice`, add one check so that a PO number that is not `PO-` and five digits gives `invalid:po_number`. In this repository `run.sh` mounts the whole folder, so your edit is used straight away. Run `--bad-po` again. (`git restore app/rules/validation.py` undoes it.)

---

## 3d. Put a shipment's papers together (`git checkout build/step-3d-group`)
Each paper carries identifiers. **Strong keys** (a PO number, an e-way bill number, the supplier plus the invoice number, a batch number) link papers automatically: two papers that share one belong together. A **vehicle number is a weak key** (one lorry carries many shipments a month), so it is shown as a hint and never used to group. Identifiers are **normalised** first, so spelling and spacing differences do not split a shipment. This is plain code (`app/services/grouping.py`, the same union-find the full system uses). No model is called.
```bash
./run.sh ladder/step3/d_group.py
```
```
Shipment 1: PO PO-40002   6 papers
    invoice              0002_bundle_scan.pdf   strong keys: ['ewb:742795434833', 'inv:27UMYCJ2170J1ZQ:SI262756132', 'po:PO-40002']
    packing_list         0002_bundle_scan.pdf   strong keys: ['batch:B17F569', 'batch:B43J529', 'inv:27UMYCJ2170J1ZQ:SI262756132', 'po:PO-40002']
    lorry_receipt        0002_bundle_scan.pdf   strong keys: ['inv:27UMYCJ2170J1ZQ:SI262756132']
    quality_certificate  0002_coa_1.pdf         strong keys: ['batch:B43J529']
    quality_certificate  0002_coa_2.pdf         strong keys: ['batch:B17F569']
    eway_bill            0002_ewaybill.pdf      strong keys: ['ewb:742795434833', 'inv:27UMYCJ2170J1ZQ:SI262756132']
    vehicle written as ['KA28 JQ 4940'] -> one vehicle after normalising: ['KA28JQ4940']
Shipment 2: PO PO-40010   5 papers
    ...
    vehicle written as ['KL19 KI 5987', 'KL19KI5987'] -> one vehicle after normalising: ['KL19KI5987']
```
**Notice:** the lorry receipt shares no PO number with the invoice, and a certificate shares only a batch number. They still end up in the same shipment, linked through a chain: lorry receipt, invoice number, invoice, PO. Eleven papers from nine files become **two shipments, 6 and 5 papers**. And the one lorry written two ways (`KL19 KI 5987` and `KL19KI5987`) is one vehicle after normalising.

**A doubt worth saying out loud:** *"Why not group by vehicle? It is on three papers."* Because one lorry carries many shipments in a month. A weak key as a hint is fine; as a rule it would merge unrelated shipments.

---

## 3e. Compare the invoice with the order, exactly (`git checkout build/step-3e-match`)
`demo-data/master.json` holds the purchase orders and the warehouse's goods receipts. For each shipment the match engine (`app/rules/match_engine.py`) compares what was billed with what was ordered and received, line by line, in **exact decimals**, and says what is wrong, what to pay and what to raise as a debit note. **A model never decides an amount.** The snapshot the engine reads is plain data, so you can read every number it used.
```bash
./run.sh ladder/step3/e_match.py
```
```
PO-40002: route investigate, issues ['PRICE_MISMATCH']
    billed 700,010.85   pay 678,300.00   debit note 21,710.85
    - PRICE_MISMATCH: SKU-2201: billed ₹3306.77 per carton vs PO price ₹3100.00 (6.67% higher, tolerance 2.0%).
    answer key expects ['PRICE_MISMATCH']: matches
PO-40010: route auto_approve, issues none
    billed 92,040.00   pay 92,040.00   debit note 0.00
    answer key expects []: matches
```
**Notice:** the supplier billed 3,306.77 a carton for Assam Tea; the order says 3,100.00. That is 6.67% over a 2% tolerance, so the engine pays the order price, **678,300.00**, and raises a **debit note for 21,710.85**. The clean shipment needs no person at all. Both results agree with the answer key.

**This is the answer to the question we started with** ("is the supplier asking for the right amount?") using a script of about 150 lines, one model call per paper and ordinary code for everything else. It runs only for you, on one laptop, and prints to a terminal.

## What step 3 still cannot do
- **Nobody else can see the result.** It is a printout on one laptop.
- **There is nowhere to decide.** A person must approve a payment, and nothing here lets them.
- **It reads papers one after another.** Month end brings thousands.

Each of those is the reason for the next steps: an API, a database and a screen (step 4), a queue (step 5), investigating agents and approval by role (step 6).

## Questions people ask
- **Where is the AI in all this?** In two places only: copying a scanned page into text, and filling a form from text. Everything that decides (where a paper ends, what is valid, what belongs together, what to pay) is code you can read.
- **Why does a second run print the same amounts?** Every model answer is saved by the file's fingerprint (`data/cache/`). Delete that folder to start again; the first run may differ in small ways, and the checks are there for exactly that.
- **Is this the real system?** The real system is these same modules plus a database, a queue and agents. The last branch is the real project, unchanged.

Next: `git switch build/step-4-api-db-screen`
