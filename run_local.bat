@echo off
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install -r requirements.txt
python scripts\prepare_data.py
python scripts\bootstrap.py --reset
uvicorn app.main:app --reload
