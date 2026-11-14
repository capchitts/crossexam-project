"""Load the same 9 demo papers steps 1-4 used (PO-40002, PO-40010) through the real HTTP upload --
there is no shortcut here, step 5's whole point is that the upload now returns before the work is
done. Run inside the api container, on the same compose network as the api and worker services:

    docker compose run --rm api python ladder/step5/seed_demo.py

Then open http://localhost:8010 and watch the batch move from processing to grouped as the workers
pick it up.
"""
from __future__ import annotations

import pathlib
import time

import httpx

API = "http://api:8000"  # the api service's own name on the compose network
FILES = sorted(p for p in pathlib.Path("demo-data/files").iterdir() if p.name.startswith(("0002", "0010")))


def main() -> None:
    files = [("files", (p.name, p.read_bytes())) for p in FILES]
    res = httpx.post(f"{API}/batches", files=files, data={"name": "Demo: PO-40002 and PO-40010"}, timeout=30)
    res.raise_for_status()
    body = res.json()
    print(f"batch {body['batch_id']}: {body['accepted']} file(s) queued, {len(body['duplicate_files'])} already seen.")
    print("The request returned immediately -- nothing has been read yet. Watching for the workers to finish...")

    for _ in range(60):
        batches = httpx.get(f"{API}/batches", timeout=10).json()
        status = next(b["status"] for b in batches if b["id"] == body["batch_id"])
        if status == "grouped":
            print(f"grouped after the workers finished. Open http://localhost:8011 to see the shipments.")
            return
        time.sleep(1)
    print("Still processing after 60s -- check `docker compose logs worker-reader worker-agent`.")


if __name__ == "__main__":
    main()
