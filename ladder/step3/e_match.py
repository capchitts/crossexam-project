"""STEP 3e: compare the invoice with the order, exactly. Plain code, no model.

Master data (demo-data/master.json) holds the purchase orders and the warehouse's goods receipts. For each shipment the match engine
(app/rules/match_engine.py) compares what was billed with what was ordered and received, line by line, in exact decimals, and says
what is wrong, what to pay and what to raise as a debit note. A model never decides an amount.

Run:  ./run.sh ladder/step3/e_match.py
"""
import json
from datetime import date
from decimal import Decimal

from c_check import read_papers
from common import paper_files
from d_group import group

from app.rules.match_engine import GRNSnapshot, PackSnapshot, POSnapshot, run_match
from app.rules.normalize import norm_po


def snapshot(members: list[dict], master: dict) -> PackSnapshot:
    """Everything the engine needs, as plain data: the papers of the shipment plus the order, the receipt and the product rules."""
    invoice = next((m["form"] for m in members if m["kind"] == "invoice"), {})
    po = next((p for p in master["purchase_orders"] if p["po_number"] == norm_po(invoice.get("po_number", ""))), None)
    suppliers = {s["code"]: s for s in master["suppliers"]}
    po_snap, grns, tol = None, [], Decimal("2.0")
    if po:
        supplier = suppliers[po["supplier_code"]]
        tol = Decimal(str(supplier.get("price_tolerance_pct") or 2.0))
        po_snap = POSnapshot(po["po_number"], supplier["gstin"], {l["sku"].upper(): {"qty": l["qty_cartons"], "price": Decimal(str(l["price_per_carton"]))} for l in po["lines"]})
        grns = [GRNSnapshot(g["grn_number"], date.fromisoformat(g["received_date"]), g["vehicle_no"], {l["sku"].upper(): {"qty": l["qty_cartons"], "batch": l["batch_no"]} for l in g["lines"]})
                for g in master["goods_receipts"] if g["po_number"] == po["po_number"]]
    products = {p["sku"].upper(): {"gst_rate": Decimal(str(p["gst_rate"])), "requires_coa": p["requires_coa"], "hsn": p["hsn"]} for p in master["products"]}
    documents = [{"id": f"{m['file']}:{m['kind']}", "doc_type": m["kind"], "data": m["form"], "flags": [], "confidence": m["form"].get("confidence", 1.0),
                  "uncertain_fields": m["form"].get("uncertain_fields", []), "duplicate_of": None, "filename": m["file"]} for m in members]
    return PackSnapshot(documents=documents, po=po_snap, grns=grns, products=products, price_tolerance_pct=tol, qty_tolerance_pct=Decimal("0.0"),
                        eway_value_tolerance_pct=Decimal("1.0"), min_shelf_life_days=180, confidence_threshold=0.8)


def main():
    master = json.load(open("demo-data/master.json"))
    answers = {s["po_number"]: s for s in json.load(open("demo-data/ground_truth.json"))["shipments"]}
    papers = [p for path in paper_files() for p in read_papers(path)]
    for members in group(papers):
        invoice = next(m["form"] for m in members if m["kind"] == "invoice")
        result = run_match(snapshot(members, master))
        po = norm_po(invoice["po_number"])
        print(f"{po}: route {result.route}, issues {result.issue_codes or 'none'}")
        print(f"    billed {result.invoice_total:,.2f}   pay {result.payable_amount:,.2f}   debit note {result.debit_note_amount:,.2f}")
        for issue in result.issues:
            print(f"    - {issue.code}: {issue.message}")
        want = answers.get(po, {}).get("expected_issue_codes")
        print(f"    answer key expects {want}: {'matches' if want is not None and sorted(want) == result.issue_codes else 'DIFFERENT'}")


if __name__ == "__main__":
    main()
