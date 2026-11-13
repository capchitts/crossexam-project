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
