"""Lesson 4: What does the paper say? (this one calls the model; it costs a fraction of a rupee)

For papers that are scans, a model reads the page and fills a form. That is all "reading" is:
the model copies what it sees into named fields, and plain code checks the result in lesson 5.

This lesson uses the small script from step 2 of the build (ladder/step2_three_small_fixes.py),
which does exactly this on one file. The full system does the same thing with extra safety:
app/agents/vision.py (read a page, cache it) and app/services/pipeline.py (extract_step).

Needs GOOGLE_API_KEY in .env.
Run:  ./learn/run.sh part-3-reading-the-papers/04_the_model_reads.py
"""
import os
import sys
import tempfile

sys.path.insert(0, "/app/ladder")   # the ladder scripts import each other by plain name

# Keep this lesson's saved results away from the real ladder results.
os.environ["STEP2_RESULTS"] = os.path.join(tempfile.mkdtemp(), "lesson4.jsonl")

from ladder.step2_three_small_fixes import read_paper  # noqa: E402  (imported after the setting above)

for name in ("0002_bundle_scan.pdf", "0010_einvoice.json"):
    row = read_paper(f"/app/demo-data/files/{name}")
    print(f"{name:22} kind={row['kind']:12} {row['fields']}")

# Notice: the e-invoice JSON also goes through the model here, because step 2 is a simple script.
# In the real system government JSON is copied by plain code (lesson 2) and never reaches a model.
