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
