# Supabase Setup

## 1. Create a project

Create a Supabase project and store the database password in a password manager. Do not reuse the password that appeared in the planning workbook; it was removed from the sanitized copy and should be rotated.

## 2. Run the schema

In Supabase SQL Editor, run:

1. `sql/01_schema.sql`
2. `sql/02_data_mart_views.sql`

`sql/03_verification_queries.sql` is for checking the loaded result after bootstrap.

## 3. Create the server connection string

Use the PostgreSQL connection information from Supabase. Prefer the session pooler when deploying to a serverless platform.

Example environment value:

```text
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/postgres
```

URL-encode special characters in the password.

## 4. Load the data

Set `DATABASE_URL` in `.env`, then run:

```bash
python scripts/prepare_data.py
python scripts/bootstrap.py --reset
```

The bootstrap uses SQLAlchemy and works with PostgreSQL. It creates the date dimension, loads all dimensions and facts, applies the demo SCD updates and flight events, and refreshes the marts.

## 5. Run the application

```bash
uvicorn app.main:app --reload
```

## Security rules

- Keep `.env` out of Git.
- Never expose the database password or service-role key in browser code.
- Do not put credentials in Excel, screenshots, README files, or commit history.
- Use a new password if an old credential was ever shared.
- The included application reads and writes through the backend, so direct public table access is unnecessary.
