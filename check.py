"""Step 0: is everything in place? Prints what it finds. Calls no model."""
import os
import pathlib
import platform

files = sorted(pathlib.Path("demo-data/files").iterdir())
key = os.environ.get("GOOGLE_API_KEY", "")
print(f"Python           {platform.python_version()} (inside the lab image)")
print(f"Demo papers      {len(files)} files in demo-data/files")
print(f"Answer key       {'found' if pathlib.Path('demo-data/ground_truth.json').exists() else 'MISSING'}")
print(f"Master data      {'found' if pathlib.Path('demo-data/master.json').exists() else 'MISSING'}")
print(f"Gemini key       {'set' if key and key != 'your-gemini-api-key' else 'not set (steps 1 to 3 need it)'}")
import langchain, pypdf  # noqa: E402,F401  (proves the libraries are installed)
print(f"Libraries        langchain {langchain.__version__}, pypdf {pypdf.__version__}")
