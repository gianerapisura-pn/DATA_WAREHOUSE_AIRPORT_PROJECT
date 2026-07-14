import csv
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.cleaning import (
    clean_agency_sales,
    clean_airlines,
    clean_airports,
    clean_corporate_sales,
    clean_flight_events,
    clean_flights,
    clean_passengers,
    issue_to_dict,
    repair_to_dict,
)

RAW = ROOT / "data" / "raw"
CLEANED = ROOT / "data" / "cleaned"
REJECTED = ROOT / "data" / "rejected"
DEMO = ROOT / "data" / "demo"
DOCS = ROOT / "docs"


def serial(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return value


def write_records(path: Path, records: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fields = [key for key in records[0].keys() if key not in {"record_hash", "source_row"}]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({field: serial(record.get(field)) for field in fields})


def write_rows(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    CLEANED.mkdir(parents=True, exist_ok=True)
    REJECTED.mkdir(parents=True, exist_ok=True)

    airlines = clean_airlines(RAW / "airlines.csv")
    airports = clean_airports(RAW / "airports.csv", add_missing=True)
    passengers = clean_passengers(RAW / "passengers.csv")
    flights = clean_flights(
        RAW / "flights.csv",
        [row["airline_key"] for row in airlines.records],
        [row["airport_key"] for row in airports.records],
    )
    corporate = clean_corporate_sales(
        RAW / "corporate_sales.csv",
        [row["passenger_id"] for row in passengers.records],
        [row["flight_key"] for row in flights.records],
    )
    agency = clean_agency_sales(
        RAW / "travel_agency_sales.csv",
        [row["passenger_id"] for row in passengers.records],
        [row["flight_key"] for row in flights.records],
    )
    flight_events = clean_flight_events(
        DEMO / "flight_status_events.csv",
        [row["flight_key"] for row in flights.records],
    )
    passenger_updates = clean_passengers(DEMO / "passenger_updates.csv")

    results = {
        "airlines": airlines,
        "airports": airports,
        "passengers": passengers,
        "flights": flights,
        "corporate_sales": corporate,
        "travel_agency_sales": agency,
        "passenger_updates": passenger_updates,
        "flight_status_events": flight_events,
    }

    write_records(CLEANED / "airlines.csv", airlines.records)
    write_records(CLEANED / "airports.csv", airports.records)
    write_records(CLEANED / "passengers.csv", passengers.records)
    write_records(CLEANED / "flights.csv", flights.records)
    write_records(CLEANED / "corporate_sales.csv", corporate.records)
    write_records(CLEANED / "travel_agency_sales.csv", agency.records)
    write_records(CLEANED / "passenger_updates.csv", passenger_updates.records)
    write_records(CLEANED / "flight_status_events.csv", flight_events.records)

    audit = {}
    for name, result in results.items():
        write_rows(REJECTED / f"{name}_rejected.csv", [issue_to_dict(issue) for issue in result.rejected])
        write_rows(REJECTED / f"{name}_repairs.csv", [repair_to_dict(repair) for repair in result.repairs])
        audit[name] = {
            "rows_received": len(result.staged),
            "rows_cleaned": len(result.records),
            "rows_rejected": len(result.rejected),
            "repairs_logged": len(result.repairs),
        }

    (DOCS / "data_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    lines = [
        "# Data Audit",
        "",
        "The raw files were profiled before warehouse loading. Repairs are logged in `data/rejected/*_repairs.csv`; rejected rows are stored beside them.",
        "",
        "| Dataset | Received | Cleaned | Rejected | Repairs logged |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, values in audit.items():
        lines.append(
            f"| {name} | {values['rows_received']} | {values['rows_cleaned']} | {values['rows_rejected']} | {values['repairs_logged']} |"
        )
    lines.extend(
        [
            "",
            "## Main decisions",
            "",
            "- `corporate_sales.sql` duplicates the corporate CSV record-for-record and is retained only as a legacy reference.",
            "- The original `DimDate.sql` uses SQL Server syntax. The project generates a PostgreSQL/SQLite-compatible date dimension instead.",
            "- Airport rows were trimmed, country names standardized, duplicate KEF and MDW records collapsed, and seven airport codes required by the flight file were added.",
            "- Flight `AF023` used `JK`; it was corrected to `JFK`.",
            "- Passenger marker rows and a repeated header were rejected. Corrupted passenger keys and one malformed email were repaired.",
            "- Sales passenger IDs were mapped to the passenger dimension. The professor-confirmed P90001/P90002 mappings resolve to P1001/P1002.",
            "- Travel transaction IDs `4AN`, `4GW`, and `4G4` were restored from sequence. One exact duplicate was rejected. The missing flight on transaction 40011 was restored as LH400.",
            "- Two travel rows with no passenger ID remain rejected because no reliable passenger identity can be inferred.",
            "- Corporate transaction 10092 had an incorrect total. The total was recalculated from its three components.",
            "- Flight-status and passenger-update files are clearly labeled demo inputs because the raw sources did not contain disruption events or repeated business-key updates.",
        ]
    )
    (DOCS / "data_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
