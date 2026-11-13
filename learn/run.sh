#!/bin/sh
# Run one lesson script inside the project's own Docker image, so nothing needs installing.
#   ./learn/run.sh part-3-reading-the-papers/01_what_came_in.py
# It sees three folders: learn/ (the lesson scripts), demo-data/ (the papers) and ladder/ (steps 1 and 2).
# It never changes any project file. Needs the image from `make up` and, for lesson 4 only, the key in .env.
cd "$(dirname "$0")/.." || exit 1
script="$1"; shift
exec docker compose run --rm --no-deps \
  -v "$PWD/learn:/app/learn" -v "$PWD/demo-data:/app/demo-data" -v "$PWD/ladder:/app/ladder" \
  -e PYTHONPATH=/app api python "learn/$script" "$@"
