"""Step 5's Celery tasks: step 4's read (step 3's a/b/c) runs here, in a worker, instead of inline in
the request. celery_app.py carries the same queue names, retries and priorities main's real
app/workers/celery_app.py uses (see that file's own docstring for why this step has its own copy).

A bundle scan splits into several papers from one file (step 3b). main's own schema has a rule for
this: a bundle's Document row becomes the *parent* of one child Document per paper found inside it
(DocStatus.split is "parent of split children; terminal for the parent itself"), and each child gets
its own Extraction row. That rule is reused here, not reinvented.
"""
from __future__ import annotations

from sqlalchemy import func, select

from app.db.models import Document, DocStatus, Extraction
from app.ingestion.storage import get_storage

from celery_app import celery_app, queue_for
from db import session_scope
from match import finalize_batch
from pipeline import read_papers

PROMPT_VERSION = "step5-v1"
RETRYABLE = (ConnectionError, OSError, TimeoutError)


@celery_app.task(bind=True, max_retries=3, autoretry_for=RETRYABLE, retry_backoff=True)
def read_one(self, document_id: str) -> None:
    """Read one uploaded file (step 3a/b/c): pick the cheapest reader, split a bundle if it is one,
    fill and check every paper's form. When every document in the batch has reached a terminal state,
    queue finalize_batch to group and match the whole batch."""
    with session_scope() as db:
        doc = db.get(Document, document_id)
        data = get_storage().get(doc.storage_path)
        papers = read_papers(doc.filename, data)

        if len(papers) == 1:
            targets = [(doc, papers[0])]
            doc.status = DocStatus.extracted
        else:
            doc.status = DocStatus.split  # parent of split children; terminal for the parent itself
            targets = []
            for i, p in enumerate(papers):
                child = Document(batch_id=doc.batch_id, parent_id=doc.id, filename=f"{doc.filename}#{i + 1}",
                                 storage_path=doc.storage_path, status=DocStatus.extracted)
                db.add(child)
                db.flush()
                targets.append((child, p))

        for target_doc, p in targets:
            db.add(Extraction(document_id=target_doc.id, doc_type=p["kind"], data=p["form"],
                              confidence=p["form"].get("confidence", 1.0), model="gemini-3.5-flash-lite",
                              prompt_version=PROMPT_VERSION, validation_issues=p["issues"]))

        batch_id = doc.batch_id
        remaining = db.scalar(select(func.count()).select_from(Document).where(
            Document.batch_id == batch_id, Document.parent_id.is_(None), Document.status == DocStatus.queued))

    if remaining == 0:
        finalize_batch_task.apply_async((batch_id,), queue=queue_for("agent"))


@celery_app.task(bind=True, max_retries=3)
def finalize_batch_task(self, batch_id: str) -> None:
    """Group the batch's papers into shipments (step 3d) and match each one (step 3e) -- a second
    worker pool (agent.*), possibly on a different machine from the one that read the papers."""
    finalize_batch(batch_id)


def enqueue_document(document_id: str, priority: str = "normal") -> None:
    read_one.apply_async((document_id,), queue=queue_for("reader", priority))
