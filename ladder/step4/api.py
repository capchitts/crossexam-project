"""Step 4's API and screen: upload papers, see them become shipments, see the answer.

Three routes, all synchronous -- no queue yet (step 5 adds one), no agent deciding a route (step 6
adds that). A big upload simply makes the request take longer; that is exactly the problem step 5
exists to fix, and you can watch it happen by uploading many files at once.

Run (from the repository root): docker compose up --build
"""
from __future__ import annotations

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.db.models import Batch, ShipmentPack

from db import init_db, session_scope
from orchestrate import ingest_batch
from web import PAGE

app = FastAPI(title="CrossExam -- step 4: API and database")


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def screen() -> str:
    return PAGE


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.post("/batches")
async def create_batch(files: list[UploadFile] = File(...), name: str = "") -> dict:
    uploads = [(f.filename or "upload.bin", await f.read()) for f in files]
    with session_scope() as db:
        batch, duplicates = ingest_batch(db, name or f"Upload ({len(uploads)} file(s))", uploads)
        return {"batch_id": batch.id, "accepted": len(uploads) - len(duplicates), "duplicate_files": duplicates}


@app.get("/batches")
def list_batches() -> list[dict]:
    with session_scope() as db:
        rows = db.scalars(select(Batch).order_by(Batch.created_at.desc())).all()
        return [{"id": b.id, "name": b.name, "status": b.status, "created_at": b.created_at.isoformat()} for b in rows]


@app.get("/batches/{batch_id}/shipments")
def batch_shipments(batch_id: str) -> list[dict]:
    with session_scope() as db:
        rows = db.scalars(select(ShipmentPack).where(ShipmentPack.batch_id == batch_id)
                          .order_by(ShipmentPack.created_at)).all()
        return [_shipment_json(p) for p in rows]


@app.get("/shipments")
def list_shipments() -> list[dict]:
    with session_scope() as db:
        rows = db.scalars(select(ShipmentPack).order_by(ShipmentPack.created_at.desc())).all()
        return [_shipment_json(p) for p in rows]


def _shipment_json(p: ShipmentPack) -> dict:
    debit = (p.match_result or {}).get("debit_note_amount", "0")
    return {"id": p.id, "po_number": p.po_number, "status": p.status.value, "route": p.route,
            "issue_codes": p.issue_codes, "invoice_total": str(p.invoice_total), "payable_amount": str(p.payable_amount),
            "debit_note_amount": debit, "finding": p.finding}
