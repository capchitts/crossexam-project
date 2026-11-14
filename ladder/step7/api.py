"""Everything from steps 5-6, plus what this step adds: structured logging and real metrics
(app/observability/*, main's own files), a /metrics route Prometheus scrapes (monitoring/prometheus.yml,
also main's own file), and /queues -- the plain question "where is a stuck batch?" answered by reading
the actual Redis queue lengths, not a guess.

Run (from the repository root): docker compose up --build
"""
from __future__ import annotations

import redis
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select

from app.config import settings
from app.db.models import Batch, Document, DocStatus, PackStatus, ReviewAction, ShipmentPack
from app.ingestion.storage import get_storage, raw_path
from app.observability.logging import configure_logging, get_logger
from app.observability.metrics import setup_metrics

from common import fingerprint
from db import init_db, session_scope
from tasks import enqueue_document
from web import PAGE

app = FastAPI(title="CrossExam -- step 7: seeing inside")
log = get_logger(__name__)
_redis = redis.Redis.from_url(settings.redis_url)

ROLES = {"ap_executive": 0, "finance_manager": 1}  # higher may approve anything a lower role may
QUEUES = ["reader.urgent", "reader.normal", "reader.bulk", "agent.urgent", "agent.normal", "agent.bulk"]


@app.on_event("startup")
def _startup() -> None:
    configure_logging()
    setup_metrics(start_http_server=False)  # this process serves /metrics itself, below
    init_db()
    log.info("api startup")


@app.get("/", response_class=HTMLResponse)
def screen() -> str:
    return PAGE


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.get("/readyz")
def readyz() -> dict:
    _redis.ping()
    return {"ok": True}


@app.get("/metrics")
def prometheus_metrics() -> Response:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/queues")
def queue_lengths() -> dict:
    """How many tasks are waiting on each queue, read straight from Redis -- the plain fact behind
    "is it stuck, or just busy?"."""
    return {q: _redis.llen(q) for q in QUEUES}


@app.post("/batches")
async def create_batch(files: list[UploadFile] = File(...), name: str = "") -> dict:
    storage = get_storage()
    uploads = [(f.filename or "upload.bin", await f.read()) for f in files]
    with session_scope() as db:
        batch = Batch(name=name or f"Upload ({len(uploads)} file(s))", status="processing", created_by="recording")
        db.add(batch)
        db.flush()
        accepted: list[str] = []
        duplicates: list[str] = []
        for filename, data in uploads:
            file_hash = fingerprint(data)
            existing = db.scalars(select(Document).where(Document.file_hash == file_hash)).first()
            if existing:
                duplicates.append(filename)
                continue
            storage.put(raw_path(file_hash, filename), data)
            doc = Document(batch_id=batch.id, file_hash=file_hash, filename=filename,
                            storage_path=raw_path(file_hash, filename), status=DocStatus.queued)
            db.add(doc)
            db.flush()
            accepted.append(doc.id)
        if not accepted:
            batch.status = "grouped"
        db.commit()
        batch_id = batch.id
    for doc_id in accepted:
        enqueue_document(doc_id)
    return {"batch_id": batch_id, "accepted": len(accepted), "duplicate_files": duplicates}


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


@app.post("/shipments/{shipment_id}/decide")
def decide_shipment(shipment_id: str, decision: str, actor: str, role: str) -> dict:
    """decision: 'approve' or 'reject'. role: 'ap_executive' or 'finance_manager'. Logged in
    review_actions (app/db/models.py) -- the real audit trail the finished system uses."""
    if decision not in ("approve", "reject"):
        raise HTTPException(400, "decision must be 'approve' or 'reject'")
    if role not in ROLES:
        raise HTTPException(400, f"role must be one of {sorted(ROLES)}")
    with session_scope() as db:
        shipment = db.get(ShipmentPack, shipment_id)
        if shipment is None:
            raise HTTPException(404, "no such shipment")
        if shipment.status != PackStatus.awaiting_approval:
            raise HTTPException(409, f"shipment is {shipment.status.value}, not awaiting_approval")
        if (decision == "approve" and shipment.payable_amount
                and shipment.payable_amount > settings.manager_approval_threshold_inr
                and ROLES[role] < ROLES["finance_manager"]):
            raise HTTPException(403, f"{role} may not approve {shipment.payable_amount:,.2f} -- above "
                                     f"{settings.manager_approval_threshold_inr:,.2f}, this needs a finance_manager.")
        shipment.status = PackStatus.approved if decision == "approve" else PackStatus.rejected
        db.add(ReviewAction(pack_id=shipment_id, actor=actor, role=role, action=decision,
                            detail={"payable_amount": str(shipment.payable_amount)}))
        status = shipment.status.value
    return {"shipment_id": shipment_id, "status": status}


def _shipment_json(p: ShipmentPack) -> dict:
    debit = (p.match_result or {}).get("debit_note_amount", "0")
    return {"id": p.id, "po_number": p.po_number, "status": p.status.value, "route": p.route,
            "issue_codes": p.issue_codes, "invoice_total": str(p.invoice_total), "payable_amount": str(p.payable_amount),
            "debit_note_amount": debit, "finding": p.finding}
