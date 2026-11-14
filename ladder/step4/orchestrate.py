"""Step 4: step 3's five moves (read -> split -> fill -> check -> group -> match), now behind a
database. Nothing about the matching is new -- the grouping below is step 3's d_group.py, the
matching is step 3's e_match.py, unchanged. What is new: every paper and every shipment becomes
a row in Postgres (app/db/models.py), the same tables the finished system on `main` uses, so more
than one person can see the answer and it survives a restart.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Batch, Document, DocStatus, PackDocument, PackStatus, Priority, ShipmentPack
from app.ingestion.storage import get_storage, raw_path
from app.rules.match_engine import GRNSnapshot, PackSnapshot, POSnapshot, run_match
from app.rules.normalize import norm_po
from app.services.grouping import UnionFind, doc_keys

from common import fingerprint
from pipeline import read_papers

MASTER = json.loads(Path("demo-data/master.json").read_text())


def group(papers: list[dict]) -> list[list[dict]]:
    """Same union-find as step 3's d_group.py: papers that share a strong key belong to one shipment."""
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
    """Same as step 3's e_match.py: everything the match engine needs, as plain data -- the shipment's
    papers plus the order, the receipt and the product rules."""
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


def ingest_batch(db: Session, name: str, uploads: list[tuple[str, bytes]]) -> tuple[Batch, list[str]]:
    """Save every file, read it (step 3's a-c), group the papers into shipments (step 3d), match each
    one (step 3e) -- and write every step as a row, in the same tables the finished system uses.

    A file already in the database (same SHA-256, from any earlier batch) does no new work --
    the same "layer 1 dedupe" rule as main's app/services/pipeline.py:ingest_file. A shipment row
    links to a paper's file at most once, ever, so re-reading a file already linked would also break
    that link; skipping it here is not an optimisation, it is required."""
    storage = get_storage()
    batch = Batch(name=name, priority=Priority.normal, status="processing", created_by="recording")
    db.add(batch)
    db.flush()

    papers: list[dict] = []
    duplicates: list[str] = []
    for filename, data in uploads:
        file_hash = fingerprint(data)
        existing = db.scalars(select(Document).where(Document.file_hash == file_hash)).first()
        if existing:
            duplicates.append(filename)
            continue
        storage.put(raw_path(file_hash, filename), data)
        doc = Document(batch_id=batch.id, file_hash=file_hash, filename=filename,
                        storage_path=raw_path(file_hash, filename), status=DocStatus.extracted)
        db.add(doc)
        db.flush()
        for p in read_papers(filename, data):
            p["filename"] = filename
            p["document_id"] = doc.id
            papers.append(p)

    for members in group(papers):
        result = run_match(snapshot(members))
        invoice = next((m["form"] for m in members if m["kind"] == "invoice"), {})
        shipment = ShipmentPack(
            batch_id=batch.id,
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
        # A bundle scan (0002_bundle_scan.pdf) splits into several papers that share one document_id
        # -- a shipment links to the FILE once, however many papers step 3's split found inside it.
        for document_id in dict.fromkeys(m["document_id"] for m in members):
            db.add(PackDocument(pack_id=shipment.id, document_id=document_id, linked_by="key"))

    batch.status = "grouped"
    db.commit()
    return batch, duplicates
