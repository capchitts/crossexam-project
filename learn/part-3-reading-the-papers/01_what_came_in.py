"""Lesson 1: What came in?

A shipment arrives as a pile of papers in different formats. Before anything is read,
the system only asks one plain question of each file: what kind of file is it?

The real code is app/ingestion/readers.py, function detect_format. Nothing here calls a model.

Run:  ./learn/run.sh part-3-reading-the-papers/01_what_came_in.py
"""
import pathlib

from app.ingestion.readers import detect_format

PAPERS = pathlib.Path("/app/demo-data/files")

# Shipments 0002 and 0010 are the two we use all through the course.
for path in sorted(PAPERS.iterdir()):
    if path.name.startswith(("0002", "0010")):
        kind = detect_format(path.name, path.read_bytes())   # looks at the name and the bytes
        print(f"{path.name:22} {path.stat().st_size:>8} bytes   {kind}")

# Notice: some PDFs are 'digital_pdf' (the text is in the file) and some are 'scanned_pdf'
# (a photograph of paper, no text at all). That difference decides who reads them next.
