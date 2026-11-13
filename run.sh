#!/bin/sh
# Run a Python file inside the lab image.
#   ./run.sh check.py
#   ./run.sh ladder/step1_one_agent.py demo-data/files/0002_bundle_scan.pdf
cd "$(dirname "$0")" || exit 1
[ -f .env ] || cp .env.example .env
docker build -q -t crossexam-steps:lab . >/dev/null || { echo "Docker build failed: is Docker Desktop running?"; exit 1; }
exec docker run --rm --env-file .env -v "$PWD:/app" -w /app -e PYTHONPATH=/app crossexam-steps:lab python "$@"
