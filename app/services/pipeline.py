import csv
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    DimAirline,
    DimAirport,
    DimDate,
    DimFlight,
    DimPassenger,
    FactAgencySale,
    FactCorporateSale,
    FlightStatusEvent,
    IngestionBatch,
    MartPassengerTicket,
    MartSalesSummary,
    RejectedRecord,
    StgAgencySale,
    StgAirline,
    StgAirport,
    StgCorporateSale,
    StgFlight,
    StgFlightEvent,
    StgPassenger,
)
from app.services.cleaning import (
    CleanResult,
    clean_agency_sales,
    clean_airlines,
    clean_airports,
    clean_corporate_sales,
    clean_flight_events,
    clean_flights,
    clean_passengers,
    eligibility,
    sha256_record,
)


STAGING_MODELS = {
    "airlines": StgAirline,
    "airports": StgAirport,
    "flights": StgFlight,
    "passengers": StgPassenger,
    "corporate_sales": StgCorporateSale,
    "travel_agency_sales": StgAgencySale,
    "flight_status_events": StgFlightEvent,
    "passenger_updates": StgPassenger,
}


def create_batch(db: Session, dataset_name: str, source_filename: str) -> IngestionBatch:
    batch = IngestionBatch(dataset_name=dataset_name, source_filename=source_filename)
    db.add(batch)
    db.flush()
    return batch


def complete_batch(db: Session, batch: IngestionBatch, result: CleanResult, loaded: int, status: str = "COMPLETED") -> None:
    batch.completed_at = datetime.utcnow()
    batch.rows_received = len(result.staged)
    batch.rows_loaded = loaded
    batch.rows_rejected = len(result.rejected)
    batch.rows_repaired = len(result.repairs)
    batch.status = status
    db.flush()


def record_staging(db: Session, dataset_name: str, batch_id: int, result: CleanResult) -> None:
    model = STAGING_MODELS[dataset_name]
    mappings: list[dict[str, Any]] = []
    for row in result.staged:
        source_row = int(row.get("source_row", 0))
        if dataset_name in {"passengers", "passenger_updates"}:
            mappings.append(
                {
                    "batch_id": batch_id,
                    "source_row": source_row,
                    "passenger_id": row.get("PassengerKey") or row.get("passenger_id") or row.get("_raw"),
                    "full_name": row.get("FullName") or row.get("full_name"),
                    "email": row.get("Email") or row.get("email"),
                    "loyalty_status": row.get("LoyaltyStatus") or row.get("loyalty_status"),
                }
            )
        elif dataset_name == "airlines":
            mappings.append(
                {
                    "batch_id": batch_id,
                    "source_row": source_row,
                    "airline_key": row.get("AirlineKey"),
                    "airline_name": row.get("AirlineName"),
                    "alliance": row.get("Alliance"),
                }
            )
        elif dataset_name == "airports":
            mappings.append(
                {
                    "batch_id": batch_id,
                    "source_row": source_row,
                    "airport_key": row.get("AirportKey") or row.get("_raw"),
                    "airport_name": row.get("AirportName"),
                    "city": row.get("City"),
                    "country": row.get("Country"),
                }
            )
        elif dataset_name == "flights":
            mappings.append(
                {
                    "batch_id": batch_id,
                    "source_row": source_row,
                    "flight_key": row.get("FlightKey"),
                    "origin_airport_key": row.get("OriginAirportKey"),
                    "destination_airport_key": row.get("DestinationAirportKey"),
                    "aircraft_type": row.get("AircraftType"),
                }
            )
        elif dataset_name == "corporate_sales":
            lower = {str(k).lower(): v for k, v in row.items()}
            mappings.append(
                {
                    "batch_id": batch_id,
                    "source_row": source_row,
                    "transaction_id": lower.get("transactionid"),
                    "date_key": lower.get("datekey"),
                    "passenger_id": lower.get("passengerkey"),
                    "flight_key": lower.get("flightkey"),
                    "ticket_price": lower.get("ticketprice"),
                    "taxes": lower.get("taxes"),
                    "baggage_fees": lower.get("baggagefees"),
                    "total_amount": lower.get("totalamount"),
                }
            )
        elif dataset_name == "travel_agency_sales":
            mappings.append(
                {
                    "batch_id": batch_id,
                    "source_row": source_row,
                    "transaction_id": row.get("TransactionID"),
                    "transaction_date": row.get("TransactionDate"),
                    "passenger_id": row.get("PassengerID"),
                    "flight_key": row.get("FlightID"),
                    "ticket_price": row.get("TicketPrice"),
                    "taxes": row.get("Taxes"),
                    "baggage_fees": row.get("BaggageFees"),
                    "total_amount": row.get("TotalAmount"),
                }
            )
        elif dataset_name == "flight_status_events":
            mappings.append(
                {
                    "batch_id": batch_id,
                    "source_row": source_row,
                    "flight_key": row.get("FlightKey") or row.get("flight_key"),
                    "status": row.get("Status") or row.get("status"),
                    "delay_minutes": row.get("DelayMinutes") or row.get("delay_minutes"),
                    "event_time": row.get("EventTime") or row.get("event_time"),
                }
            )
    if mappings:
        db.bulk_insert_mappings(model, mappings)


def record_rejections(db: Session, dataset_name: str, batch_id: int, result: CleanResult) -> None:
    for issue in result.rejected:
        db.add(
            RejectedRecord(
                batch_id=batch_id,
                dataset_name=dataset_name,
                source_row=issue.source_row,
                reason=issue.reason,
                raw_data=json.dumps(issue.raw_data, ensure_ascii=False),
            )
        )


def load_date_dimension(db: Session, start_date: date = date(2023, 1, 1), end_date: date = date(2024, 12, 31)) -> int:
    existing = db.scalar(select(func.count()).select_from(DimDate)) or 0
    if existing:
        return int(existing)
    rows = []
    current = start_date
    while current <= end_date:
        rows.append(
            DimDate(
                date_key=int(current.strftime("%Y%m%d")),
                full_date=current,
                day_of_month=current.day,
                day_name=current.strftime("%A"),
                day_of_week=current.isoweekday(),
                month=current.month,
                month_name=current.strftime("%B"),
                quarter=((current.month - 1) // 3) + 1,
                half_year=1 if current.month <= 6 else 2,
                year=current.year,
                is_weekend=current.weekday() >= 5,
            )
        )
        current += timedelta(days=1)
    db.add_all(rows)
    db.flush()
    return len(rows)


def _scd2_upsert(db: Session, model, business_field: str, business_value: str, attrs: dict[str, Any], event_time: datetime) -> tuple[Any, bool]:
    current = db.scalar(
        select(model).where(
            getattr(model, business_field) == business_value,
            model.is_current.is_(True),
        )
    )
    record_hash = sha256_record(*attrs.values())
    if current and current.record_hash == record_hash:
        return current, False
    if current:
        current.is_current = False
        current.effective_to = event_time
    payload = {
        business_field: business_value,
        **attrs,
        "effective_from": event_time,
        "effective_to": None,
        "is_current": True,
        "record_hash": record_hash,
    }
    new_record = model(**payload)
    db.add(new_record)
    db.flush()
    return new_record, True


def load_airline_dimensions(db: Session, records: list[dict[str, Any]], event_time: datetime | None = None) -> int:
    event_time = event_time or datetime.utcnow()
    changed = 0
    for record in records:
        _, inserted = _scd2_upsert(
            db,
            DimAirline,
            "airline_key",
            record["airline_key"],
            {"airline_name": record["airline_name"], "alliance": record["alliance"]},
            event_time,
        )
        changed += int(inserted)
    return changed


def load_airport_dimensions(db: Session, records: list[dict[str, Any]], event_time: datetime | None = None) -> int:
    event_time = event_time or datetime.utcnow()
    changed = 0
    for record in records:
        _, inserted = _scd2_upsert(
            db,
            DimAirport,
            "airport_key",
            record["airport_key"],
            {
                "airport_name": record["airport_name"],
                "city": record["city"],
                "country": record["country"],
            },
            event_time,
        )
        changed += int(inserted)
    return changed


def load_passenger_dimensions(db: Session, records: list[dict[str, Any]], event_time: datetime | None = None) -> int:
    event_time = event_time or datetime.utcnow()
    changed = 0
    for record in records:
        _, inserted = _scd2_upsert(
            db,
            DimPassenger,
            "passenger_id",
            record["passenger_id"],
            {
                "full_name": record["full_name"],
                "email": record["email"],
                "loyalty_status": record["loyalty_status"],
            },
            event_time,
        )
        changed += int(inserted)
    return changed


def current_airlines(db: Session) -> dict[str, DimAirline]:
    return {row.airline_key: row for row in db.scalars(select(DimAirline).where(DimAirline.is_current.is_(True))).all()}


def current_airports(db: Session) -> dict[str, DimAirport]:
    return {row.airport_key: row for row in db.scalars(select(DimAirport).where(DimAirport.is_current.is_(True))).all()}


def current_passengers(db: Session) -> dict[str, DimPassenger]:
    return {row.passenger_id: row for row in db.scalars(select(DimPassenger).where(DimPassenger.is_current.is_(True))).all()}


def current_flights(db: Session) -> dict[str, DimFlight]:
    return {row.flight_key: row for row in db.scalars(select(DimFlight)).all()}


def load_flight_dimensions(db: Session, records: list[dict[str, Any]]) -> int:
    airlines = current_airlines(db)
    airports = current_airports(db)
    loaded = 0
    for record in records:
        existing = db.scalar(select(DimFlight).where(DimFlight.flight_key == record["flight_key"]))
        payload = {
            "airline_sk": airlines[record["airline_key"]].airline_sk,
            "origin_airport_sk": airports[record["origin_airport_key"]].airport_sk,
            "destination_airport_sk": airports[record["destination_airport_key"]].airport_sk,
            "aircraft_type": record["aircraft_type"],
        }
        if existing:
            for field, value in payload.items():
                setattr(existing, field, value)
        else:
            db.add(DimFlight(flight_key=record["flight_key"], **payload))
            loaded += 1
    db.flush()
    return loaded


def load_corporate_facts(db: Session, records: list[dict[str, Any]], batch_id: int) -> int:
    passengers = current_passengers(db)
    flights = current_flights(db)
    loaded = 0
    for record in records:
        existing = db.scalar(select(FactCorporateSale).where(FactCorporateSale.transaction_id == record["transaction_id"]))
        payload = {
            "date_key": record["date_key"],
            "passenger_sk": passengers[record["passenger_id"]].passenger_sk,
            "flight_sk": flights[record["flight_key"]].flight_sk,
            "ticket_price": record["ticket_price"],
            "taxes": record["taxes"],
            "baggage_fees": record["baggage_fees"],
            "total_amount": record["total_amount"],
            "batch_id": batch_id,
            "source_row": record["source_row"],
        }
        if existing:
            for field, value in payload.items():
                setattr(existing, field, value)
        else:
            db.add(FactCorporateSale(transaction_id=record["transaction_id"], **payload))
            loaded += 1
    db.flush()
    return loaded


def load_agency_facts(db: Session, records: list[dict[str, Any]], batch_id: int) -> int:
    passengers = current_passengers(db)
    flights = current_flights(db)
    loaded = 0
    for record in records:
        existing = db.scalar(select(FactAgencySale).where(FactAgencySale.transaction_id == record["transaction_id"]))
        payload = {
            "date_key": record["date_key"],
            "passenger_sk": passengers[record["passenger_id"]].passenger_sk,
            "flight_sk": flights[record["flight_key"]].flight_sk,
            "ticket_price": record["ticket_price"],
            "taxes": record["taxes"],
            "baggage_fees": record["baggage_fees"],
            "total_amount": record["total_amount"],
            "batch_id": batch_id,
            "source_row": record["source_row"],
        }
        if existing:
            for field, value in payload.items():
                setattr(existing, field, value)
        else:
            db.add(FactAgencySale(transaction_id=record["transaction_id"], **payload))
            loaded += 1
    db.flush()
    return loaded


def load_flight_status_events(db: Session, records: list[dict[str, Any]], batch_id: int | None, source: str) -> int:
    loaded = 0
    for record in records:
        duplicate = db.scalar(
            select(FlightStatusEvent).where(
                FlightStatusEvent.flight_key == record["flight_key"],
                FlightStatusEvent.event_time == record["event_time"],
                FlightStatusEvent.status == record["status"],
            )
        )
        if duplicate:
            continue
        db.add(
            FlightStatusEvent(
                flight_key=record["flight_key"],
                status=record["status"],
                delay_minutes=record["delay_minutes"],
                event_time=record["event_time"],
                source=source,
                batch_id=batch_id,
            )
        )
        loaded += 1
    db.flush()
    return loaded


def latest_flight_events(db: Session) -> dict[str, FlightStatusEvent]:
    events = db.scalars(select(FlightStatusEvent).order_by(FlightStatusEvent.event_time.desc(), FlightStatusEvent.event_id.desc())).all()
    latest: dict[str, FlightStatusEvent] = {}
    for event in events:
        latest.setdefault(event.flight_key, event)
    return latest


def refresh_marts(db: Session) -> tuple[int, int]:
    db.execute(delete(MartPassengerTicket))
    db.execute(delete(MartSalesSummary))
    db.flush()

    dates = {row.date_key: row for row in db.scalars(select(DimDate)).all()}
    passengers = {row.passenger_sk: row for row in db.scalars(select(DimPassenger)).all()}
    flights = {row.flight_sk: row for row in db.scalars(select(DimFlight)).all()}
    airlines = {row.airline_sk: row for row in db.scalars(select(DimAirline)).all()}
    airports = {row.airport_sk: row for row in db.scalars(select(DimAirport)).all()}
    events = latest_flight_events(db)

    ticket_rows: list[MartPassengerTicket] = []
    summary_groups: dict[tuple[int, int, int, int, str], dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "total": Decimal("0.00"), "delayed": 0, "cancelled": 0, "month_name": ""}
    )

    sources = [
        ("CORPORATE", db.scalars(select(FactCorporateSale)).all()),
        ("AGENCY", db.scalars(select(FactAgencySale)).all()),
    ]
    for source_type, facts in sources:
        for fact in facts:
            date_dim = dates[fact.date_key]
            passenger = passengers[fact.passenger_sk]
            flight = flights[fact.flight_sk]
            airline = airlines[flight.airline_sk]
            origin = airports[flight.origin_airport_sk]
            destination = airports[flight.destination_airport_sk]
            event = events.get(flight.flight_key)
            status = event.status if event else "UNKNOWN"
            delay_minutes = event.delay_minutes if event else 0
            eligible, reason = eligibility(status, delay_minutes, settings.eligibility_delay_minutes)
            ticket_rows.append(
                MartPassengerTicket(
                    source_type=source_type,
                    transaction_id=fact.transaction_id,
                    date_key=fact.date_key,
                    transaction_date=date_dim.full_date,
                    passenger_id=passenger.passenger_id,
                    passenger_name=passenger.full_name,
                    passenger_email=passenger.email,
                    loyalty_status=passenger.loyalty_status,
                    flight_key=flight.flight_key,
                    airline_key=airline.airline_key,
                    airline_name=airline.airline_name,
                    origin_airport_code=origin.airport_key,
                    origin_airport_name=origin.airport_name,
                    origin_city=origin.city,
                    destination_airport_code=destination.airport_key,
                    destination_airport_name=destination.airport_name,
                    destination_city=destination.city,
                    aircraft_type=flight.aircraft_type,
                    ticket_price=fact.ticket_price,
                    taxes=fact.taxes,
                    baggage_fees=fact.baggage_fees,
                    total_amount=fact.total_amount,
                    flight_status=status,
                    delay_minutes=delay_minutes,
                    is_eligible=eligible,
                    eligibility_reason=reason,
                )
            )
            key = (date_dim.year, date_dim.quarter, date_dim.half_year, date_dim.month, source_type)
            group = summary_groups[key]
            group["count"] += 1
            group["total"] += Decimal(fact.total_amount)
            group["month_name"] = date_dim.month_name
            group["delayed"] += int(status == "DELAYED")
            group["cancelled"] += int(status == "CANCELLED")

    db.add_all(ticket_rows)
    db.flush()
    summaries: list[MartSalesSummary] = []
    for (year, quarter, half_year, month, source_type), values in sorted(summary_groups.items()):
        average = (values["total"] / values["count"]).quantize(Decimal("0.01")) if values["count"] else Decimal("0.00")
        summaries.append(
            MartSalesSummary(
                year=year,
                quarter=quarter,
                half_year=half_year,
                month=month,
                month_name=values["month_name"],
                source_type=source_type,
                transaction_count=values["count"],
                total_sales=values["total"].quantize(Decimal("0.01")),
                average_ticket_value=average,
                delayed_count=values["delayed"],
                cancelled_count=values["cancelled"],
            )
        )
    db.add_all(summaries)
    db.flush()
    return len(ticket_rows), len(summaries)


def process_dataset(db: Session, dataset_name: str, source_filename: str, content: bytes) -> dict[str, Any]:
    batch = create_batch(db, dataset_name, source_filename)
    try:
        if dataset_name == "airlines":
            result = clean_airlines(content)
            record_staging(db, dataset_name, batch.batch_id, result)
            loaded = load_airline_dimensions(db, result.records)
        elif dataset_name == "airports":
            result = clean_airports(content, add_missing=True)
            record_staging(db, dataset_name, batch.batch_id, result)
            loaded = load_airport_dimensions(db, result.records)
        elif dataset_name in {"passengers", "passenger_updates"}:
            result = clean_passengers(content)
            record_staging(db, dataset_name, batch.batch_id, result)
            loaded = load_passenger_dimensions(db, result.records)
        elif dataset_name == "flights":
            airlines = current_airlines(db)
            airports = current_airports(db)
            result = clean_flights(content, airlines.keys(), airports.keys())
            record_staging(db, dataset_name, batch.batch_id, result)
            loaded = load_flight_dimensions(db, result.records)
        elif dataset_name == "corporate_sales":
            passengers = current_passengers(db)
            flights = current_flights(db)
            result = clean_corporate_sales(content, passengers.keys(), flights.keys())
            record_staging(db, dataset_name, batch.batch_id, result)
            loaded = load_corporate_facts(db, result.records, batch.batch_id)
        elif dataset_name == "travel_agency_sales":
            passengers = current_passengers(db)
            flights = current_flights(db)
            result = clean_agency_sales(content, passengers.keys(), flights.keys())
            record_staging(db, dataset_name, batch.batch_id, result)
            loaded = load_agency_facts(db, result.records, batch.batch_id)
        elif dataset_name == "flight_status_events":
            flights = current_flights(db)
            result = clean_flight_events(content, flights.keys())
            record_staging(db, dataset_name, batch.batch_id, result)
            loaded = load_flight_status_events(db, result.records, batch.batch_id, "UPLOAD")
        else:
            raise ValueError(f"Unsupported dataset type: {dataset_name}")
        record_rejections(db, dataset_name, batch.batch_id, result)
        complete_batch(db, batch, result, loaded)
        refresh_marts(db)
        db.commit()
        return {
            "batch_id": batch.batch_id,
            "dataset_name": dataset_name,
            "rows_received": len(result.staged),
            "rows_loaded": loaded,
            "rows_rejected": len(result.rejected),
            "rows_repaired": len(result.repairs),
            "repairs": [
                {
                    "source_row": repair.source_row,
                    "field": repair.field,
                    "old_value": repair.old_value,
                    "new_value": repair.new_value,
                    "reason": repair.reason,
                }
                for repair in result.repairs[:25]
            ],
        }
    except Exception:
        batch.completed_at = datetime.utcnow()
        batch.status = "FAILED"
        db.commit()
        raise


def search_tickets(db: Session, query: str, limit: int = 20) -> list[MartPassengerTicket]:
    cleaned = query.strip()
    if not cleaned:
        return []
    like = f"%{cleaned}%"
    statement = (
        select(MartPassengerTicket)
        .where(
            or_(
                MartPassengerTicket.passenger_id.ilike(like),
                MartPassengerTicket.passenger_name.ilike(like),
                MartPassengerTicket.flight_key.ilike(like),
                MartPassengerTicket.airline_name.ilike(like),
                MartPassengerTicket.origin_airport_code.ilike(like),
                MartPassengerTicket.destination_airport_code.ilike(like),
                MartPassengerTicket.transaction_id == int(cleaned) if cleaned.isdigit() else False,
            )
        )
        .order_by(MartPassengerTicket.transaction_date.desc(), MartPassengerTicket.transaction_id.desc())
        .limit(limit)
    )
    return db.scalars(statement).all()


def dashboard_metrics(db: Session) -> dict[str, Any]:
    total_sales = db.scalar(select(func.coalesce(func.sum(MartPassengerTicket.total_amount), 0))) or Decimal("0.00")
    total_tickets = db.scalar(select(func.count()).select_from(MartPassengerTicket)) or 0
    delayed = db.scalar(select(func.count()).select_from(MartPassengerTicket).where(MartPassengerTicket.flight_status == "DELAYED")) or 0
    cancelled = db.scalar(select(func.count()).select_from(MartPassengerTicket).where(MartPassengerTicket.flight_status == "CANCELLED")) or 0
    eligible = db.scalar(select(func.count()).select_from(MartPassengerTicket).where(MartPassengerTicket.is_eligible.is_(True))) or 0
    return {
        "total_sales": Decimal(total_sales),
        "total_tickets": int(total_tickets),
        "delayed": int(delayed),
        "cancelled": int(cancelled),
        "eligible": int(eligible),
        "delay_threshold": settings.eligibility_delay_minutes,
    }


def export_table_to_csv(db: Session, model, destination: Path, columns: list[str]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = db.scalars(select(model)).all()
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: getattr(row, column) for column in columns})
