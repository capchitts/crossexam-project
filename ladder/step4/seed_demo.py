"""Load the same 9 demo papers steps 1-3 used (PO-40002, PO-40010) straight into step 4's database --
no browser needed. Run inside the api container, where DATABASE_URL points at Postgres:

    docker compose run --rm api python ladder/step4/seed_demo.py

Then open http://localhost:8010 and the screen shows exactly what this prints.
"""
from __future__ import annotations

import pathlib

from db import init_db, session_scope
from orchestrate import ingest_batch

FILES = sorted(p for p in pathlib.Path("demo-data/files").iterdir() if p.name.startswith(("0002", "0010")))


def main() -> None:
    init_db()
    uploads = [(p.name, p.read_bytes()) for p in FILES]
    with session_scope() as db:
        batch, duplicates = ingest_batch(db, "Demo: PO-40002 and PO-40010", uploads)
        print(f"batch {batch.id}: {len(uploads) - len(duplicates)} file(s) loaded, {len(duplicates)} already seen.")
        print("Open http://localhost:8010 to see the shipments.")


if __name__ == "__main__":
    main()
