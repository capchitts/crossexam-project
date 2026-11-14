"""Step 5's finalize step: step 4's group (step 3d) and match (step 3e), unchanged, now reading
saved Extraction rows from Postgres instead of keeping a batch's papers in memory inside one request.
A worker can pick this up on a different machine from the one that read the papers -- the database,
not the process, is what carries the work forward.
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

MASTER = json.loads(Path("demo-data/master.json").read_text())


def group(papers: list[dict]) -> list[list[dict]]:
    """Unchanged from step 4's orchestrate.py: papers that share a strong key belong to one shipment."""
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
    """Unchanged from step 4's orchestrate.py: everything the match engine needs, as plain data."""
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
    """Called once every document of a batch has been read (see tasks.py:read_one). Gathers every
    paper's saved Extraction row, groups them into shipments, matches each one, and writes the
    ShipmentPack rows -- exactly what step 4's ingest_batch did at the end of one request."""
    with session_scope() as db:
        docs = db.scalars(select(Document).where(Document.batch_id == batch_id)).all()
        papers: list[dict] = []
        for doc in docs:
            for ex in db.scalars(select(Extraction).where(Extraction.document_id == doc.id)).all():
                papers.append({"kind": ex.doc_type, "form": ex.data, "filename": doc.filename, "document_id": doc.id})

        for members in group(papers):
            result = run_match(snapshot(members))
            invoice = next((m["form"] for m in members if m["kind"] == "invoice"), {})
            shipment = ShipmentPack(
                batch_id=batch_id,
                po_number=norm_po(invoice.get("po_number", "")) or None,
                status=PackStatus.auto_approved if result.route == "auto_approve" else PackStatus.needs_review,
                route=result.route,
                match_result={"issues": [{"code": i.code, "message": i.message} for i in result.issues],
                              "debit_note_amount": str(result.debit_note_amount)},
                issue_codes=result.issue_codes,
                invoice_total=result.invoice_total,
                payable_amount=result.payable_amount,
                finding="; ".join(i.message for i in result.issues) or "No issue found.",
            )
            db.add(shipment)
            db.flush()
            for document_id in dict.fromkeys(m["document_id"] for m in members):
                db.add(PackDocument(pack_id=shipment.id, document_id=document_id, linked_by="key"))

        batch = db.get(Batch, batch_id)
        batch.status = "grouped"
