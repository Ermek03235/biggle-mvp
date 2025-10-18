#!/usr/bin/env bash
set -e
export PYTHONUNBUFFERED=1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
