"""Lesson 2: Who reads each paper?

Each format gets the cheapest reader that works:
  government JSON  -> copied by plain code, no model, confidence 1.0
  digital PDF      -> the text is already in the file, no model
  scan or photo    -> the pages are handed to a vision model, one page at a time

The real code is app/ingestion/readers.py, function read_document.

Run:  ./learn/run.sh part-3-reading-the-papers/02_who_reads_each.py
"""
import collections
import pathlib

from app.ingestion.readers import read_document

PAPERS = pathlib.Path("/app/demo-data/files")
count = collections.Counter()
needs_model = 0

for path in sorted(PAPERS.iterdir()):
    result = read_document(path.name, path.read_bytes())     # the real reader
    count[result.fmt] += 1
    needs_model += 1 if result.pages_needing_vision else 0
    if path.name.startswith("0010"):                         # print only shipment 0010
        pages = len(result.pages_needing_vision)
        print(f"{path.name:22} {result.fmt:12} pages for the model: {pages}")

print()
print("All 51 papers:", dict(count))
print(f"Papers that need a model at all: {needs_model} of {sum(count.values())}")
