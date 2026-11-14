"""Database setup for step 4: create the tables this step actually uses.

The full system's migrate step (`python -m app.db.session`, in app/db/session.py) also creates the
Postgres `vector` extension and the resumable agent-thread tables -- neither exists yet at step 4
(the model has no memory of past turns until step 6's exception agent). So this step has its own,
smaller init, and `ENABLE_PGVECTOR=0` turns the embedding column into a plain JSON column (see
app/db/models.py) so the `vector` extension is never needed here.
"""
from __future__ import annotations

from app.db.models import Base
from app.db.session import engine, session_scope  # re-exported: api.py and seed_demo.py both need session_scope

__all__ = ["init_db", "engine", "session_scope"]


def init_db() -> None:
    Base.metadata.create_all(engine)
