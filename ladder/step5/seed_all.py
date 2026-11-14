"""Upload all 51 demo papers through the real API, for the worker-kill resilience test. Not part of
the normal demo (that's seed_demo.py, 9 files)."""
from __future__ import annotations
import pathlib
import httpx

API = "http://api:8000"
FILES = sorted(pathlib.Path("demo-data/files").iterdir())


def main() -> None:
    files = [("files", (p.name, p.read_bytes())) for p in FILES]
    res = httpx.post(f"{API}/batches", files=files, data={"name": "All 51 papers"}, timeout=60)
    res.raise_for_status()
    print(res.json())


if __name__ == "__main__":
    main()
