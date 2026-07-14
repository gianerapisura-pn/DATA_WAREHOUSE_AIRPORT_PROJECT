#!/usr/bin/env sh
set -eu
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/prepare_data.py
python scripts/bootstrap.py --reset
uvicorn app.main:app --reload
