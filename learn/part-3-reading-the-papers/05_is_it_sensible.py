"""Lesson 5: Is what was read sensible?

A model can misread a number. So plain code checks every form: do the lines add up, does
the tax match the rate, is the tax number valid? This is exact, free and explainable.

The real code is app/rules/validation.py, function validate.

Run:  ./learn/run.sh part-3-reading-the-papers/05_is_it_sensible.py
"""
import copy
import json

from app.ingestion.readers import parse_gov_json
from app.rules.validation import validate

# A real invoice from the demo papers (government JSON, so it is copied, not read by a model).
raw = open("/app/demo-data/files/0010_einvoice.json", "rb").read()
invoice = parse_gov_json(raw)["data"]
print("Invoice", invoice["invoice_number"], "total", invoice["total"])
print("Checks on the real invoice :", validate("invoice", invoice) or "no problems")

# Pretend the model misread the total by one digit.
misread = copy.deepcopy(invoice)
misread["total"] = invoice["total"] + 1000
print("Checks after a misread     :", validate("invoice", misread))

# Pretend the model misread the PO number (PO-40010 read as PQ-40010).
bad_po = copy.deepcopy(invoice)
bad_po["po_number"] = "PQ-40010"
print("Checks on PQ-40010         :", validate("invoice", bad_po) or "no problems")

# Your turn: the last line says 'no problems', but PQ-40010 is not a valid PO number.
# Open app/rules/validation.py, function _invoice, and add one check so it is flagged.
# (A PO number is 'PO-' and five digits.) Do it on your own copy: this branch never edits the project.
