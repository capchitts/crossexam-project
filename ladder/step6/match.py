"""Step 6's finalize step: step 4/5's group (step 3d) and match (step 3e) are unchanged. What is new:
a shipment that is not a clean auto_approve now also gets a real agent's plain-language finding
(supervisor.py) before it waits for a person -- and its status becomes awaiting_approval, not just
needs_review, because now there IS a proposal to approve or reject, not only a fact to notice.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.db.models import Batch, Document, Extraction, PackDocument, PackStatus, ShipmentPack
from app.rules.match_engine import GRNSnapshot, PackSnapshot, POSnapshot, run_match
from app.rules.normalize import norm_po
from app.services.grouping import UnionFind, doc_keys

from db import session_scope
from supervisor import investigate, stricter_route

MASTER = json.loads(Path("demo-data/master.json").read_text())


def group(papers: list[dict]) -> list[list[dict]]:
    """Unchanged from step 4/5: papers that share a strong key belong to one shipment."""
    uf = UnionFind()
    for i, p in enumerate(papers):
        p["strong"], p["weak"] = doc_keys(p["kind"], p["form"])
        uf.find(f"paper:{i}")
        for key in p["strong"]:
            uf.union(f"paper:{i}", f"key:{key}")
    shipments: dict[str, list[dict]] = {}
    for i, p in enumerate(papers):
        shipments.setdefault(uf.find(f"paper:{i}"), []).append(p)
    return list(shipments.values())


def snapshot(members: list[dict]) -> PackSnapshot:
    """Unchanged from step 4/5: everything the match engine needs, as plain data."""
    invoice = next((m["form"] for m in members if m["kind"] == "invoice"), {})
    po = next((p for p in MASTER["purchase_orders"] if p["po_number"] == norm_po(invoice.get("po_number", ""))), None)
    suppliers = {s["code"]: s for s in MASTER["suppliers"]}
    po_snap, grns, tol = None, [], Decimal("2.0")
    if po:
        supplier = suppliers[po["supplier_code"]]
        tol = Decimal(str(supplier.get("price_tolerance_pct") or 2.0))
        po_snap = POSnapshot(po["po_number"], supplier["gstin"],
                              {l["sku"].upper(): {"qty": l["qty_cartons"], "price": Decimal(str(l["price_per_carton"]))}
                               for l in po["lines"]})
        grns = [GRNSnapshot(g["grn_number"], date.fromisoformat(g["received_date"]), g["vehicle_no"],
                             {l["sku"].upper(): {"qty": l["qty_cartons"], "batch": l["batch_no"]} for l in g["lines"]})
                for g in MASTER["goods_receipts"] if g["po_number"] == po["po_number"]]
    products = {p["sku"].upper(): {"gst_rate": Decimal(str(p["gst_rate"])), "requires_coa": p["requires_coa"], "hsn": p["hsn"]}
                for p in MASTER["products"]}
    documents = [{"id": f"{m['filename']}:{m['kind']}", "doc_type": m["kind"], "data": m["form"], "flags": [],
                  "confidence": m["form"].get("confidence", 1.0), "uncertain_fields": m["form"].get("uncertain_fields", []),
                  "duplicate_of": None, "filename": m["filename"]} for m in members]
    return PackSnapshot(documents=documents, po=po_snap, grns=grns, products=products, price_tolerance_pct=tol,
                        qty_tolerance_pct=Decimal("0.0"), eway_value_tolerance_pct=Decimal("1.0"),
                        min_shelf_life_days=180, confidence_threshold=0.8)


def finalize_batch(batch_id: str) -> None:
    """Group the batch's papers into shipments, match each one, and -- new in this step -- ask a
    real agent to explain any shipment that is not a clean auto_approve, before it waits for a
    person to approve or reject it."""
    with session_scope() as db:
        docs = db.scalars(select(Document).where(Document.batch_id == batch_id)).all()
        papers: list[dict] = []
        for doc in docs:
            for ex in db.scalars(select(Extraction).where(Extraction.document_id == doc.id)).all():
                papers.append({"kind": ex.doc_type, "form": ex.data, "filename": doc.filename, "document_id": doc.id})

        for members in group(papers):
            result = run_match(snapshot(members))
            invoice = next((m["form"] for m in members if m["kind"] == "invoice"), {})
            code_finding = "; ".join(i.message for i in result.issues) or "No issue found."
            route, finding = result.route, code_finding

            if result.route != "auto_approve":
                decision = investigate(norm_po(invoice.get("po_number", "")) or None, result.route,
                                       result.issue_codes, code_finding, result.invoice_total,
                                       result.payable_amount, result.debit_note_amount)
                route = stricter_route(result.route, decision.route)
                finding = f"{code_finding} Agent: {decision.summary} (confidence {decision.confidence:.2f})"

            shipment = ShipmentPack(
                batch_id=batch_id,
                po_number=norm_po(invoice.get("po_number", "")) or None,
                status=PackStatus.auto_approved if route == "auto_approve" else PackStatus.awaiting_approval,
                route=route,
                match_result={"issues": [{"code": i.code, "message": i.message} for i in result.issues],
                              "debit_note_amount": str(result.debit_note_amount)},
                issue_codes=result.issue_codes,
                invoice_total=result.invoice_total,
                payable_amount=result.payable_amount,
                finding=finding,
            )
            db.add(shipment)
            db.flush()
            for document_id in dict.fromkeys(m["document_id"] for m in members):
                db.add(PackDocument(pack_id=shipment.id, document_id=document_id, linked_by="key"))

        batch = db.get(Batch, batch_id)
        batch.status = "grouped"
