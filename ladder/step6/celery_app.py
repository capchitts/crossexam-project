"""Step 5's Celery app. The queue names, priorities and resilience settings are the same ones
main's real app/workers/celery_app.py uses (reader.*/agent.* queues, task_acks_late,
task_reject_on_worker_lost, worker_prefetch_multiplier=1). Left out on purpose: main's version also
imports app.observability.* on worker startup (step 7) and eagerly includes app.workers.tasks, which
imports app.services.pipeline, which imports the agents (step 6). Neither exists yet at step 5.
"""
from __future__ import annotations

from celery import Celery

from app.config import settings

PRIORITIES = ("urgent", "normal", "bulk")
READER_QUEUES = [f"reader.{p}" for p in PRIORITIES]
AGENT_QUEUES = [f"agent.{p}" for p in PRIORITIES]

celery_app = Celery("crossexam-step5", broker=settings.redis_url, include=["tasks"])
celery_app.conf.update(
    task_ignore_result=True,  # results live in PostgreSQL, not in the broker
    task_acks_late=True,  # a task is removed from the queue only after it finishes...
    task_reject_on_worker_lost=True,  # ...so a killed worker's task is redelivered
    worker_prefetch_multiplier=1,
    broker_transport_options={"visibility_timeout": 20},  # main uses 3600; see tasks.py
    broker_connection_retry_on_startup=True,
    task_default_queue="reader.normal",
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
)


def queue_for(kind: str, priority: str = "normal") -> str:
    p = priority if priority in PRIORITIES else "normal"
    return f"{kind}.{p}"
