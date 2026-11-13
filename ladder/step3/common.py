"""Small helpers shared by the step 3 scripts. Nothing clever: which papers, a fingerprint, a disk cache, a model."""
import hashlib
import json
import os
import pathlib

CACHE = pathlib.Path("data/cache")           # git-ignored; delete it to start from nothing
SHIPMENTS = ("0002", "0010")                 # the two shipments we follow: 9 files


def paper_files(prefixes=SHIPMENTS) -> list[pathlib.Path]:
    return sorted(p for p in pathlib.Path("demo-data/files").iterdir() if p.name.startswith(tuple(prefixes)))


def all_papers() -> list[pathlib.Path]:
    return sorted(pathlib.Path("demo-data/files").iterdir())


def fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cached(group: str, key: str, make):
    """The saved answer for `key`, or compute it once with make() and save it. Returns (value, was_saved).
    The model is called only on a miss, so a second run is free and prints the same answers."""
    path = CACHE / group / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text()), True
    value = make()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return value, False


def chat_model():
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(model=os.environ.get("MODEL_SMALL", "gemini-3.5-flash-lite"))
