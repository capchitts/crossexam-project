"""STEP 3a: read cheaply. Plain rules pick the cheapest reader for each file. No model is called.

  government JSON  -> mapped to a form by plain code
  digital PDF      -> the text is already in the file
  spreadsheet      -> each sheet becomes a page of text
  scan or photo    -> only these need a vision model (step 3b)

Run:  ./run.sh ladder/step3/a_read.py
"""
import collections

from common import all_papers, fingerprint, paper_files

from app.ingestion.readers import read_document


def main():
    print("The nine papers of shipments 0002 and 0010:")
    for path in paper_files():
        data = path.read_bytes()
        result = read_document(path.name, data)
        pages = len(result.pages_needing_vision)
        print(f"  {path.name:22} {result.fmt:12} fingerprint {fingerprint(data)[:8]}   pages for a vision model: {pages}")

    count, vision_pages, vision_files = collections.Counter(), 0, 0
    for path in all_papers():
        result = read_document(path.name, path.read_bytes())
        count[result.fmt] += 1
        vision_pages += len(result.pages_needing_vision)
        vision_files += 1 if result.pages_needing_vision else 0
    print(f"\nAll {sum(count.values())} papers: {dict(count)}")
    print(f"Papers that need the vision model: {vision_files} ({vision_pages} pages). Government JSON needs no model at all: {count['gov_json']}.")


if __name__ == "__main__":
    main()
