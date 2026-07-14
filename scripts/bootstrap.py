import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import Base, SessionLocal, engine
from app.services.cleaning import (
    clean_agency_sales,
    clean_airlines,
    clean_airports,
    clean_corporate_sales,
    clean_flight_events,
    clean_flights,
    clean_passengers,
)
from app.services.pipeline import (
    complete_batch,
    create_batch,
    current_airlines,
    current_airports,
    current_flights,
    current_passengers,
    load_agency_facts,
    load_airline_dimensions,
    load_airport_dimensions,
    load_corporate_facts,
    load_date_dimension,
    load_flight_dimensions,
    load_flight_status_events,
    load_passenger_dimensions,
    record_rejections,
    record_staging,
    refresh_marts,
)

RAW = ROOT / "data" / "raw"
DEMO = ROOT / "data" / "demo"


def run_stage(db, name, filename, result, loader):
    batch = create_batch(db, name, filename)
    record_staging(db, name, batch.batch_id, result)
    loaded = loader(batch.batch_id)
    record_rejections(db, name, batch.batch_id, result)
    complete_batch(db, batch, result, loaded)
    return {
        "dataset": name,
        "batch_id": batch.batch_id,
        "received": len(result.staged),
        "loaded": loaded,
        "rejected": len(result.rejected),
        "repaired": len(result.repairs),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--without-demo", action="store_true")
    args = parser.parse_args()

    if args.reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    reports = []
    try:
        load_date_dimension(db)

        airlines = clean_airlines(RAW / "airlines.csv")
        reports.append(run_stage(db, "airlines", "airlines.csv", airlines, lambda _: load_airline_dimensions(db, airlines.records, datetime(2023, 1, 1))))

        airports = clean_airports(RAW / "airports.csv", add_missing=True)
        reports.append(run_stage(db, "airports", "airports.csv", airports, lambda _: load_airport_dimensions(db, airports.records, datetime(2023, 1, 1))))

        passengers = clean_passengers(RAW / "passengers.csv")
        reports.append(run_stage(db, "passengers", "passengers.csv", passengers, lambda _: load_passenger_dimensions(db, passengers.records, datetime(2023, 1, 1))))

        flights = clean_flights(RAW / "flights.csv", current_airlines(db).keys(), current_airports(db).keys())
        reports.append(run_stage(db, "flights", "flights.csv", flights, lambda _: load_flight_dimensions(db, flights.records)))

        corporate = clean_corporate_sales(RAW / "corporate_sales.csv", current_passengers(db).keys(), current_flights(db).keys())
        reports.append(run_stage(db, "corporate_sales", "corporate_sales.csv", corporate, lambda batch_id: load_corporate_facts(db, corporate.records, batch_id)))

        agency = clean_agency_sales(RAW / "travel_agency_sales.csv", current_passengers(db).keys(), current_flights(db).keys())
        reports.append(run_stage(db, "travel_agency_sales", "travel_agency_sales.csv", agency, lambda batch_id: load_agency_facts(db, agency.records, batch_id)))

        if not args.without_demo:
            updates = clean_passengers(DEMO / "passenger_updates.csv")
            reports.append(run_stage(db, "passenger_updates", "passenger_updates.csv", updates, lambda _: load_passenger_dimensions(db, updates.records, datetime(2024, 1, 15))))

            events = clean_flight_events(DEMO / "flight_status_events.csv", current_flights(db).keys())
            reports.append(run_stage(db, "flight_status_events", "flight_status_events.csv", events, lambda batch_id: load_flight_status_events(db, events.records, batch_id, "DEMO")))

        mart_tickets, mart_summaries = refresh_marts(db)
        db.commit()
        print(json.dumps({"batches": reports, "mart_tickets": mart_tickets, "mart_summaries": mart_summaries}, indent=2))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
