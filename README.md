# Airport Data Warehouse and Flight Disruption Data Mart

This project cleans airport, airline, passenger, flight, corporate-sales, and travel-agency files; loads them into a dimensional warehouse; preserves passenger history with Slowly Changing Dimension Type 2; builds ticket-level and time-hierarchy data marts; and exposes the results through a FastAPI website.

## Main outputs

- Raw and staging layers
- Data-quality and rejection logs
- `dim_date`, `dim_airline`, `dim_airport`, `dim_passenger`, and `dim_flight`
- `fact_corporate_sales` and `fact_agency_sales`
- Passenger SCD Type 2 history
- Flight-ticket/check-in data mart
- Monthly, quarterly, half-year, and yearly sales hierarchy
- File-upload and transformation page
- Passenger and flight lookup page
- Flight disruption eligibility output
- Kafka-compatible producer and consumer
- SQLite local mode, PostgreSQL Docker mode, and Supabase PostgreSQL mode

## Verified project counts

After a clean bootstrap with the included demo updates and events:

| Output | Rows |
|---|---:|
| Date dimension | 731 |
| Current airlines | 39 |
| Current airports | 221 |
| Current passengers | 2,822 |
| Passenger dimension versions | 2,824 |
| Flights | 390 |
| Corporate sales facts | 100 |
| Agency sales facts | 298 |
| Flight-status events | 12 |
| Ticket data mart | 398 |

The travel source contains 301 rows. One exact duplicate and two rows without passenger IDs are rejected, leaving 298 loadable agency sales.

## Important data decisions

The data audit is in [`docs/data_audit.md`](docs/data_audit.md). Project limitations are listed in [`docs/known_limitations.md`](docs/known_limitations.md).

- The corporate SQL file contains the same 100 records as the corporate CSV. It is kept only as a reference and is not loaded twice.
- The original date script uses Microsoft SQL Server syntax. This project uses a database-neutral Python generator and a PostgreSQL schema.
- Airport country names are standardized, duplicate KEF and MDW keys are collapsed, and airport records required by the flight file are added.
- `AF023` uses `JK` in the source flight file. It is repaired to `JFK`.
- Passenger marker lines, a repeated header, corrupted keys, and one corrupted email are handled explicitly.
- Sales passenger identifiers are mapped to passenger dimension IDs. `P90001` and `P90002` map to `P1001` and `P1002`, matching the professor's clarification.
- Travel transaction IDs `4AN`, `4GW`, and `4G4` are restored as `40021`, `40164`, and `40288` from their sequence.
- Transaction `40011` has a missing flight and is restored as `LH400` from the surrounding source sequence.
- Corporate transaction `10092` has an incorrect total and is recalculated from ticket price, taxes, and baggage fees.

## Demo-only inputs

The raw files do not include flight status, delay duration, or repeated updates for the same passenger business key. Two small files are therefore included under `data/demo`:

- `flight_status_events.csv` demonstrates Kafka and delayed/cancelled eligibility.
- `passenger_updates.csv` demonstrates SCD Type 2.

They are visibly separated from the original source data. The default eligibility rule is:

> Eligible when the flight is cancelled or delayed by at least 180 minutes.

The threshold is configurable through `ELIGIBILITY_DELAY_MINUTES` because the exact delay threshold was not completely legible in the classroom notes.

## Local setup with SQLite

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Prepare the cleaned data and audit logs:

```bash
python scripts/prepare_data.py
```

Build the local warehouse:

```bash
python scripts/bootstrap.py --reset
```

Start the application:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

Useful lookup examples:

```text
P1001
AA100
Mary Smith
JFK
10001
```

## Run with Docker, PostgreSQL, and Kafka

```bash
docker compose up --build
```

The services are:

- Website/API: `http://localhost:8000`
- PostgreSQL: `localhost:5433`
- Kafka-compatible Redpanda broker: `localhost:19092`

Publish the included flight events:

```bash
python kafka/producer.py
```

Run the consumer in another terminal:

```bash
python kafka/consumer.py
```

The consumer sends each Kafka message to the FastAPI endpoint, stores the event, and refreshes the data mart.

## Supabase setup

Read [`docs/supabase_setup.md`](docs/supabase_setup.md). The application connects to Supabase through a server-side PostgreSQL connection string. Do not place a Supabase service-role key or database password in frontend JavaScript, source files, spreadsheets, or GitHub.

## GitHub setup

Read [`docs/github_setup.md`](docs/github_setup.md). The repository already includes `.gitignore` and a GitHub Actions workflow that prepares the data, bootstraps the database, and runs the tests.

## Tests

```bash
pytest -q
```

The tests check cleaning counts, referential integrity, amount reconciliation, SCD history, data-mart row counts, eligibility logic, and API health.

## Export the data marts

```bash
python scripts/export_marts.py
```

Exports are written to `data/exports` and are ignored by Git.

## Project structure

```text
app/                 FastAPI application, models, ETL services, templates
scripts/             Data preparation, bootstrap, and mart export
sql/                 Supabase/PostgreSQL schema and verification queries
kafka/               Producer and consumer
 data/raw/            Original source files
 data/cleaned/        Cleaned source outputs
 data/rejected/       Rejected rows and repair logs
 data/demo/           Clearly labeled demonstration updates/events
 docs/                Audit, architecture, data dictionary, setup guides
 reference/           Sanitized planning workbook and legacy SQL
 tests/               Unit and integration tests
```

## Academic presentation

The accurate contribution statement is that this project implements the unfinished planned architecture using the original files and professor guidance. Demo events and assumptions must remain labeled as demo material. Before presenting or submitting the project, every team member should run it, review the code, and be prepared to explain the cleaning rules, schema, SCD logic, data marts, API flow, and Kafka flow.
