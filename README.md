# Airport Data Warehouse and Flight Operations Data Mart

A FastAPI-based data warehousing project for airport operations and ticket-sales analytics. It loads raw airline, airport, passenger, flight, corporate-sales, travel-agency-sales, and flight-status event files into a dimensional warehouse with staging tables, cleaned dimensions/facts, SCD Type 2 passenger history, and reporting marts.

![Airport data warehouse pipeline](docs/pipeline_architecture.svg)

## What this project shows

- ETL pipeline with staging, validation, rejected-record tracking, and repair counts
- Dimensional model with date, airline, airport, passenger, and flight dimensions
- SCD Type 2 handling for passenger profile changes
- Corporate and travel-agency sales fact tables
- Ticket-level and monthly sales-summary data marts
- FastAPI dashboard for ingestion, quality review, passenger lookup, and flight disruption eligibility
- Optional Kafka event path for flight-status updates
- SQLite for local demo runs, with PostgreSQL/Supabase-ready schema and configuration

## Local quick start

These steps run the verified local version with SQLite.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/bootstrap.py --reset
uvicorn app.main:app --reload
```

Open the app at:

```text
http://localhost:8000
```

If port 8000 is already in use, run another port:

```bash
uvicorn app.main:app --reload --port 8001
```

## Required source files

Raw source files are stored in `data/raw/` and are intentionally kept unchanged. Demo event/update files are in `data/demo/`.

```text
data/raw/airlines.csv
data/raw/airports.csv
data/raw/passengers.csv
data/raw/flights.csv
data/raw/corporate_sales.csv
data/raw/travel_agency_sales.csv
data/demo/passenger_updates.csv
data/demo/flight_status_events.csv
```

## Database behavior

By default, the project creates a local SQLite database named `airport_dw.db`. This file is ignored by Git because it is generated locally.

The date dimension starts on `2023-01-01` and extends through the end of the next calendar year based on the day the bootstrap runs. For example, if the project is bootstrapped during 2026, `dim_date` is populated through `2027-12-31`.

To rebuild the local warehouse:

```bash
python scripts/bootstrap.py --reset
```

To export the data marts:

```bash
python scripts/export_marts.py
```

Exports are written to `data/exports/`, which is also ignored by Git.

## Upload validation

The web upload endpoint checks dataset type, file extension, file size, UTF-8 readability, and required columns before the ETL run starts. Rows that fail business rules are recorded as rejected records. Unexpected failed batches are saved with `FAILED` status for audit review.

## Kafka and Docker

Kafka is optional for the local demo. The app can process flight-status changes by uploading the demo event CSV or by calling the FastAPI endpoint directly.

Docker Compose is included for running Kafka locally when that path is needed:

```bash
docker compose up -d
```

Then run the producer and consumer scripts from separate terminals if you want to demonstrate the Kafka flow.

## Supabase / PostgreSQL

The default verified local setup uses SQLite. PostgreSQL/Supabase support is prepared through SQLAlchemy and the included SQL scripts, but a live Supabase deployment still requires your own project credentials.

Copy `.env.example` to `.env` and update only local/private values:

```text
DATABASE_URL=sqlite:///./airport_dw.db
KAFKA_BOOTSTRAP_SERVERS=localhost:19092
API_BASE_URL=http://localhost:8000
```

Do not commit `.env`, passwords, database files, exports, or generated caches.

## Tests and validation

Run the project checks with:

```bash
python scripts/bootstrap.py --reset
pytest -q
python -m compileall -q app scripts kafka tests
python scripts/export_marts.py
```

The latest local validation passed with 14 tests.

## Notes

This is an academic data warehouse prototype prepared for local demonstration and portfolio review. The included datasets are sample/demo data, not a production airport system. Authentication, role-based access, cloud deployment hardening, and live Kafka/Supabase runtime verification are documented as future production steps.
