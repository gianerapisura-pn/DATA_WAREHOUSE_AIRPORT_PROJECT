# Validation Report

Validation date: 2026-07-14

## Commands run

```bash
python scripts/prepare_data.py
python scripts/bootstrap.py --reset
pytest -q
python -m compileall -q app scripts kafka tests
python scripts/export_marts.py
```

## Results

- Data preparation completed.
- Warehouse bootstrap completed.
- 11 tests passed.
- Python compilation completed without syntax errors.
- Ticket and sales-summary data marts exported successfully.

## Verified database counts

| Table/output | Count |
|---|---:|
| `dim_date` | 731 |
| `dim_airline` | 39 |
| `dim_airport` | 221 |
| `dim_passenger` versions | 2,824 |
| Current passengers | 2,822 |
| `dim_flight` | 390 |
| `fact_corporate_sales` | 100 |
| `fact_agency_sales` | 298 |
| `flight_status_events` | 12 |
| `mart_passenger_ticket` | 398 |
| `mart_sales_summary` | 13 |

## Integrity checks

- Corporate amount mismatches after cleaning: 0
- Agency amount mismatches after cleaning: 0
- Orphan corporate passenger keys: 0
- Orphan agency passenger/flight keys: 0
- Duplicate loaded fact transaction IDs: 0
- Current passenger rows: one per passenger business key
- SCD history verified for P1001 and P1002

Kafka broker execution and a live Supabase connection were not tested in this environment. Their code, Docker configuration, PostgreSQL schema, and setup instructions are included, while the tested local implementation uses SQLite.
