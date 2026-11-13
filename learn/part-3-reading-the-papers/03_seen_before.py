"""Lesson 3: Have we seen this paper before?

Every file gets a fingerprint (a SHA-256 hash of its bytes). The same bytes give the same
fingerprint, so a file uploaded twice is recognised and costs nothing the second time.
Change one byte and it is a different file.

The real code is in app/services/pipeline.py, function ingest_file: it looks the fingerprint
up before it does any work. Here we only show the fingerprint itself.

Run:  ./learn/run.sh part-3-reading-the-papers/03_seen_before.py
"""
import hashlib
import pathlib

data = pathlib.Path("/app/demo-data/files/0002_bundle_scan.pdf").read_bytes()

first = hashlib.sha256(data).hexdigest()
again = hashlib.sha256(data).hexdigest()                  # the same file uploaded again
changed = hashlib.sha256(data + b" ").hexdigest()         # one byte added

print("first upload  :", first[:16], "...")
print("same again    :", again[:16], "...", "-> same file, skipped" if first == again else "")
print("one byte more :", changed[:16], "...", "-> new file, read again" if first != changed else "")
