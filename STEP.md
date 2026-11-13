# Step 0: get it running

**The goal of this step:** be able to run any file of this repository with one command, and know where everything is. No model is called.

## Where things are
| Path | What it is |
|---|---|
| `demo-data/files/` | the 51 invented papers of Kaveri Distributors (the same files in every step) |
| `demo-data/master.json` | the purchase orders and goods receipts the papers are checked against |
| `demo-data/ground_truth.json` | the answer key |
| `run.sh` | runs a Python file inside the lab image |
| `Dockerfile`, `requirements-lab.txt` | the lab image: Python and a few libraries |
| `.env` | your key (created by `make setup`, never committed) |

## Run it
```bash
make setup      # creates .env; put your Gemini key in it
make check
```
The first `make check` builds the image (about a minute). Later ones start at once.

## What you should see
```
Python           3.12.x (inside the lab image)
Demo papers      51 files in demo-data/files
Answer key       found
Master data      found
Gemini key       set (or: not set (steps 1 to 3 need it))
Libraries        langchain 1.4.6, pypdf 6.21.1
```

## Questions people ask
- **Why Docker?** So the same command gives the same result on every machine, and nothing is installed on yours.
- **Why mount the folder?** So you can edit a file and run it again without rebuilding.
- **Do I need a key now?** No. Step 1 is the first that calls a model.

Next: `git switch build/step-1-one-agent`
