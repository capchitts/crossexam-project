# Step 1: one agent reads one paper

**The goal of this step:** the simplest thing that could work. Give a model a paper and a form, and see what comes back. No queue, no database, no checks, no screen.

**The use case:** shipments 0002 and 0010, nine files. Read the invoice of PO-40002: who is the supplier, what is the invoice number, which order is it for, what is the total?

## What is new
| File | What it does |
|---|---|
| `ladder/step1_one_agent.py` | About 65 lines. A form (`Invoice`, four fields), one agent (`create_agent` with a model, no tools), and `read_file`, which turns a file into text or pictures the model can read. |

An **agent** at this step is nothing more than a loop around a model that must return the form. There are no tools yet.

## Run it
```bash
./run.sh ladder/step1_one_agent.py demo-data/files/0002_bundle_scan.pdf
./run.sh ladder/step1_one_agent.py $(ls demo-data/files/0002_* demo-data/files/0010_*)     # all nine
```

## What you should see (a real run of this branch)
```
0002_bundle_scan.pdf     supplier_name='Deccan Hygiene Industries' invoice_number='SI/26-27/56132' po_number='PO-40002' total=700010.85   (2.0 s)
0002_coa_1.pdf           supplier_name='Deccan Hygiene Industries' invoice_number='' po_number='' total=0   (0.7 s)
0002_ewaybill.pdf        supplier_name='27UMYCJ2170J1ZQ' invoice_number='SI/26-27/56132' po_number='' total=700010.85   (1.1 s)
0010_einvoice.json       supplier_name='Tungabhadra Detergents Ltd' invoice_number='SI/26-27/14044' po_number='PO-40010' total=92040.0   (0.8 s)
0010_lr_scan.pdf         supplier_name='SOUTHERN CARGO MOVERS' invoice_number='SI/26-27/14044' po_number='' total=0   (1.5 s)
... (nine lines in all; about 9 s of model time, about 14 s for the whole command)
```
The three invoices are read exactly right, including PO-40002 and the total 700,010.85. Your timings and cost will differ a little. (Measured earlier on the same nine files with this script: about US$0.003, under a rupee.)

## What to notice
Look at the lines again before reading on.
1. **A tax ID in the name field.** The e-way bill is not an invoice, but the agent had only the invoice form, so it forced the paper in: `supplier_name='27UMYCJ2170J1ZQ'`.
2. **Quality certificates and lorry receipts get "invoice" fields.** `0010_lr_scan.pdf` has `supplier_name='SOUTHERN CARGO MOVERS'`, which is the transporter.
3. **Nothing is kept.** The answers are printed and gone. Run it again and you pay again.
4. **Nothing says what kind of paper it was.**

Step 2 fixes these three things without adding a single new component.

## Questions people ask
- **Why not add a database, a queue and a screen right now?** Because nothing so far has asked for one. The first version is fast and cheap. A new part must earn its place by fixing something we can see.
- **Why LangChain `create_agent` for something this simple?** It is the same building block the real system uses, so nothing is thrown away later.
- **Is the model right?** On the invoices, yes. On the other papers it answers a question that does not apply to them. That is the lesson of step 2.

Next: `git switch build/step-2-three-fixes`
