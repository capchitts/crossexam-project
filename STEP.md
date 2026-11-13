# Step 2: three small fixes, no new component

**What step 1 showed:** every paper was forced into the invoice form, nothing was remembered, and a stop lost everything. Look at the notes of step 1 first.

**The goal of this step:** fix those three things with the smallest possible change. Still one script, still no queue, no database, no screen.

## What is new
`ladder/step2_three_small_fixes.py` is step 1 plus three small ideas:
| Fix | In the code | Why |
|---|---|---|
| 1. Ask what kind of paper it is first | `Kind`, then one small form per kind (`Invoice`, `Shipping`, `Certificate`) | A certificate is not an invoice. The right form follows the kind. |
| 2. Fingerprint every file | `hashlib.sha256(bytes)`, looked up before any call | The same bytes are never read twice. A repeat costs nothing. |
| 3. Save each result as it arrives | one line per paper in `ladder/results.jsonl` | A stop no longer loses what was already read. |

## Run it
```bash
rm -f ladder/results.jsonl                      # start clean
./run.sh ladder/step2_three_small_fixes.py demo-data/files/0002_* demo-data/files/0010_*
./run.sh ladder/step2_three_small_fixes.py demo-data/files/0002_* demo-data/files/0010_*     # again
```

## What you should see (a real run of this branch)
First run (17 s for the whole command, two model calls per file):
```
0002_bundle_scan.pdf     other        {}
0002_coa_1.pdf           certificate  {'batch_number': 'B43J529', 'expiry_date': '11/09/2027', 'result': 'PASS'}
0002_ewaybill.pdf        shipping     {'invoice_number': 'SI/26-27/56132', 'vehicle_number': 'KA28 JQ 4940'}
0010_einvoice.json       invoice      {'supplier_name': 'Tungabhadra Detergents Ltd', 'invoice_number': 'SI/26-27/14044', 'po_number': 'PO-40010', 'total': 92040.0}
0010_ewaybill.json       shipping     {'invoice_number': 'SI/26-27/14044', 'vehicle_number': 'KL19KI5987'}
0010_lr_scan.pdf         shipping     {'invoice_number': 'SI/26-27/14044', 'vehicle_number': 'KL19 KI 5987'}
... (nine lines)
```
Second run: **3.5 seconds for the whole command, every line ends `(skipped: seen before)`, no model call.**

## What to notice
1. **Certificates, e-way bills and lorry receipts now get their own forms.** No tax ID in the name field any more.
2. **The repeat run costs nothing.** The fingerprint is already in `results.jsonl`.
3. **The bundle is still wrong.** `0002_bundle_scan.pdf` is *three papers in one scan* (an invoice, a packing list and a lorry receipt) but it got one kind and one form. In this run the kind was `other` and the invoice of PO-40002 was lost. In other runs the same file came back as `invoice`. The model is not a function: the same file can give a different answer.
4. **Saving the answer saves the wrong answer too.** The second run faithfully returns `other {}`. A cache is only as good as what it caches.
5. **One lorry, written two ways.** `KL19KI5987` (the e-way bill) and `KL19 KI 5987` (the lorry receipt) are the same vehicle. Nothing compares them.
6. **Nothing compares the invoice with the order.** The agent copied what is printed. It cannot say the supplier asked too much.

## Questions people ask
- **Why not retry until the bundle comes back as an invoice?** A retry that "works" this time proves nothing next time. The fix is to split the bundle into its papers, one form each.
- **Is a fingerprint the same as a filename?** No. A filename can change; the bytes decide. One extra space gives a different fingerprint.
- **Is `results.jsonl` a database?** It is one line of JSON per paper, in a file. It is enough for one person on one laptop, and that is exactly the next problem.

Next: `git switch build/step-3-plain-code`
