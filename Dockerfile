# syntax=docker/dockerfile:1.7
# The lab image for steps 0 to 5: Python and the libraries. The code is mounted at run time, so you can edit a file and run it again.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 PIP_RETRIES=8
WORKDIR /app
COPY requirements-lab.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements-lab.txt
