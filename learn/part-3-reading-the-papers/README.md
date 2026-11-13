# Reading the papers: five lessons

**The use case.** Kaveri Distributors receives a shipment as a pile of papers: scans, PDFs, photos, spreadsheets, government files. Before anyone can check the money, the system must turn each paper into named fields (supplier, invoice number, PO number, total). We follow shipments 0002 and 0010.

Each lesson answers one question, runs in a few seconds, and opens one file of the real project.

| # | The question | Run | The real code it opens | Needs the key? |
|---|---|---|---|---|
| 1 | What came in? | `./learn/run.sh part-3-reading-the-papers/01_what_came_in.py` | `app/ingestion/readers.py` (`detect_format`) | no |
| 2 | Who reads each paper? | `.../02_who_reads_each.py` | `app/ingestion/readers.py` (`read_document`) | no |
| 3 | Have we seen this paper before? | `.../03_seen_before.py` | `app/services/pipeline.py` (`ingest_file`) | no |
| 4 | What does the paper say? | `.../04_the_model_reads.py` | `app/agents/vision.py`, `app/services/pipeline.py` (`extract_step`); the lesson uses `ladder/step2_three_small_fixes.py` | yes, a fraction of a rupee |
| 5 | Is what was read sensible? | `.../05_is_it_sensible.py` | `app/rules/validation.py` (`validate`) | no |

## What you will see
1. Nine papers, each with a format: `scanned_pdf`, `digital_pdf`, `gov_json`.
2. Of the 51 papers only 11 need a model; the rest are copied or read as text. (Lesson 2 prints this.)
3. The same file gives the same fingerprint, one extra byte gives a new one.
4. The model fills a form for each paper: supplier, invoice number, PO number, total.
5. Plain code accepts the real invoice and flags a total that is off by 1,000. It does **not** flag `PQ-40010`: that is the assignment at the end of lesson 5.

## The order in the real system
`app/services/pipeline.py` runs these as steps: `ingest_file` (lesson 3) → `read_step` (lessons 1 and 2) → `transcribe_step` and `extract_step` (lesson 4) → `validate` (lesson 5). The lessons are the same steps, one at a time.
