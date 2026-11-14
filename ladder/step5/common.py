"""Small helpers for step 4: a fingerprint and a saved-answer cache. Unchanged from step 3's own
common.py (ladder/step3/common.py) -- this step does not touch how a paper is read."""
import hashlib
import json
import os
import pathlib

CACHE = pathlib.Path("data/cache")  # git-ignored; delete it to make every paper call the model again


def fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cached(group: str, key: str, make):
    """The saved answer for `key`, or compute it once with make() and save it. A second run of the
    same paper is free and prints the same answer."""
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
