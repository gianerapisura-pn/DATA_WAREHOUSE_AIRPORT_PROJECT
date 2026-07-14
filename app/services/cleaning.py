import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


COUNTRY_ALIASES = {
    "USA": "United States",
    "US": "United States",
    "U.S.A.": "United States",
    "UNITED STATES": "United States",
    "UK": "United Kingdom",
    "SCOTLAND": "United Kingdom",
}

AIRPORT_DEFAULTS = {
    "EZE": ("Ezeiza", "Argentina"),
    "MIA": ("Miami", "United States"),
    "CAN": ("Guangzhou", "China"),
    "PHX": ("Phoenix", "United States"),
    "SMF": ("Sacramento", "United States"),
}

MISSING_AIRPORTS = [
    {
        "airport_key": "ANC",
        "airport_name": "Ted Stevens Anchorage International Airport",
        "city": "Anchorage",
        "country": "United States",
        "repair_note": "Added because ANC is referenced by flights.csv.",
    },
    {
        "airport_key": "DOH",
        "airport_name": "Hamad International Airport",
        "city": "Doha",
        "country": "Qatar",
        "repair_note": "Added because DOH is referenced by flights.csv.",
    },
    {
        "airport_key": "KIX",
        "airport_name": "Kansai International Airport",
        "city": "Osaka",
        "country": "Japan",
        "repair_note": "Added because KIX is referenced by flights.csv.",
    },
    {
        "airport_key": "PHL",
        "airport_name": "Philadelphia International Airport",
        "city": "Philadelphia",
        "country": "United States",
        "repair_note": "Added because PHL is referenced by flights.csv.",
    },
    {
        "airport_key": "OGG",
        "airport_name": "Kahului Airport",
        "city": "Kahului",
        "country": "United States",
        "repair_note": "Added because OGG is referenced by flights.csv.",
    },
    {
        "airport_key": "KOA",
        "airport_name": "Ellison Onizuka Kona International Airport at Keahole",
        "city": "Kailua-Kona",
        "country": "United States",
        "repair_note": "Added because KOA is referenced by flights.csv.",
    },
    {
        "airport_key": "LIH",
        "airport_name": "Lihue Airport",
        "city": "Lihue",
        "country": "United States",
        "repair_note": "Added because LIH is referenced by flights.csv.",
    },
]

PASSENGER_KEY_REPAIRS = {
    "P1L1592": "P1592",
    "P1VII-1798": "P1798",
    "P1P1937": "P1937",
    "P2Note: 2758": "P2758",
}

TRANSACTION_ID_REPAIRS = {
    "4AN": "40021",
    "4GW": "40164",
    "4G4": "40288",
}

SPECIAL_PASSENGER_MAPPINGS = {
    "P90001": "P1001",
    "P90002": "P1002",
}

VALID_LOYALTY = {"Bronze", "Silver", "Gold", "Platinum"}
VALID_FLIGHT_STATUS = {"ON_TIME", "DELAYED", "CANCELLED"}


@dataclass
class Issue:
    source_row: int
    reason: str
    raw_data: dict[str, Any]


@dataclass
class Repair:
    source_row: int
    field: str
    old_value: Any
    new_value: Any
    reason: str


@dataclass
class CleanResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[Issue] = field(default_factory=list)
    repairs: list[Repair] = field(default_factory=list)
    staged: list[dict[str, Any]] = field(default_factory=list)


def text(value: Any) -> str:
    return "" if value is None else re.sub(r"\s+", " ", str(value)).strip()


def sha256_record(*values: Any) -> str:
    body = "|".join(text(value) for value in values)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def parse_money(value: Any) -> Decimal:
    cleaned = text(value).replace("$", "").replace(",", "")
    if not cleaned:
        raise ValueError("Missing numeric value")
    try:
        amount = Decimal(cleaned).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric value: {value}") from exc
    if amount < 0:
        raise ValueError("Negative amounts are not allowed")
    return amount


def parse_date_flexible(value: Any) -> date:
    cleaned = text(value)
    formats = (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d-%b-%y",
        "%d-%b-%Y",
        "%Y%m%d",
    )
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value}")


def parse_datetime_flexible(value: Any) -> datetime:
    cleaned = text(value)
    formats = (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
    )
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported datetime format: {value}")


def read_standard_csv(path_or_bytes: str | Path | bytes) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
    if isinstance(path_or_bytes, bytes):
        content = path_or_bytes.decode("utf-8-sig")
    else:
        content = Path(path_or_bytes).read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    rows = [(index, dict(row)) for index, row in enumerate(reader, start=2)]
    return list(reader.fieldnames or []), rows


def read_airports_csv(path_or_bytes: str | Path | bytes) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
    if isinstance(path_or_bytes, bytes):
        content = path_or_bytes.decode("utf-8-sig")
    else:
        content = Path(path_or_bytes).read_text(encoding="utf-8-sig")
    lines = content.splitlines()
    header = next(csv.reader([lines[0]]))
    rows: list[tuple[int, dict[str, str]]] = []
    for line_number, line in enumerate(lines[1:], start=2):
        values = next(csv.reader([line]))
        if len(values) == 5 and values[0].strip() == "OSL":
            values = [values[0], f"{values[1]},{values[2]}", values[3], values[4]]
        if len(values) != 4:
            rows.append((line_number, {"_raw": line, "_field_count": str(len(values))}))
            continue
        rows.append((line_number, dict(zip(header, values))))
    return header, rows


def read_passengers_csv(path_or_bytes: str | Path | bytes) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
    if isinstance(path_or_bytes, bytes):
        content = path_or_bytes.decode("utf-8-sig")
    else:
        content = Path(path_or_bytes).read_text(encoding="utf-8-sig")
    lines = content.splitlines()
    parsed: list[tuple[int, list[str], str]] = []
    for line_number, original in enumerate(lines, start=1):
        line = original
        if len(line) >= 2 and line.startswith('"') and line.endswith('"'):
            line = line[1:-1].replace('""', '"')
        values = next(csv.reader([line]))
        parsed.append((line_number, values, original))
    header = [value.lstrip("\ufeff") for value in parsed[0][1]]
    rows: list[tuple[int, dict[str, str]]] = []
    for line_number, values, original in parsed[1:]:
        if len(values) != 4:
            rows.append((line_number, {"_raw": original, "_field_count": str(len(values))}))
            continue
        row = dict(zip(header, values))
        rows.append((line_number, row))
    return header, rows


def normalize_country(value: Any) -> str:
    cleaned = text(value)
    return COUNTRY_ALIASES.get(cleaned.upper(), cleaned)


def normalize_passenger_key(value: Any) -> tuple[str, str | None]:
    original = text(value)
    repaired = PASSENGER_KEY_REPAIRS.get(original, original)
    match = re.fullmatch(r"P0+(\d+)", repaired)
    if match:
        repaired = f"P{int(match.group(1))}"
    if not re.fullmatch(r"P\d{4}", repaired):
        raise ValueError(f"Invalid passenger key: {original}")
    note = None if repaired == original else "Standardized corrupted or zero-padded passenger key"
    return repaired, note


def map_sales_passenger_id(value: Any) -> tuple[str, str | None]:
    original = text(value)
    if not original:
        raise ValueError("Missing passenger ID")
    if original in SPECIAL_PASSENGER_MAPPINGS:
        return SPECIAL_PASSENGER_MAPPINGS[original], "Mapped known test passenger ID to existing dimension key"
    match = re.fullmatch(r"P(\d{5})", original)
    if not match:
        raise ValueError(f"Invalid sales passenger ID: {original}")
    mapped = f"P{1000 + int(match.group(1))}"
    return mapped, "Mapped source sales passenger ID to passenger dimension business key"


def infer_airline_key(flight_key: str, airline_keys: Iterable[str]) -> str:
    options = sorted(airline_keys, key=len, reverse=True)
    for airline_key in options:
        if flight_key.startswith(airline_key):
            return airline_key
    raise ValueError(f"Unable to infer airline for flight {flight_key}")


def clean_airlines(path_or_bytes: str | Path | bytes) -> CleanResult:
    _, rows = read_standard_csv(path_or_bytes)
    result = CleanResult()
    seen: set[str] = set()
    for source_row, raw in rows:
        result.staged.append({"source_row": source_row, **raw})
        try:
            airline_key = text(raw.get("AirlineKey")).upper()
            airline_name = text(raw.get("AirlineName"))
            alliance = text(raw.get("Alliance")) or "Independent"
            if not re.fullmatch(r"[A-Z0-9]{2,3}", airline_key):
                raise ValueError("Airline key must contain two or three letters or numbers")
            if not airline_name:
                raise ValueError("Missing airline name")
            if airline_key in seen:
                raise ValueError(f"Duplicate airline key: {airline_key}")
            seen.add(airline_key)
            if not text(raw.get("Alliance")):
                result.repairs.append(Repair(source_row, "alliance", raw.get("Alliance"), alliance, "Blank alliance classified as Independent"))
            result.records.append(
                {
                    "airline_key": airline_key,
                    "airline_name": airline_name,
                    "alliance": alliance,
                    "record_hash": sha256_record(airline_name, alliance),
                    "source_row": source_row,
                }
            )
        except ValueError as exc:
            result.rejected.append(Issue(source_row, str(exc), raw))
    return result


def clean_airports(path_or_bytes: str | Path | bytes, add_missing: bool = True) -> CleanResult:
    _, rows = read_airports_csv(path_or_bytes)
    result = CleanResult()
    canonical: dict[str, dict[str, Any]] = {}
    preferred_names = {
        "KEF": "Keflavík International Airport",
        "MDW": "Chicago Midway International Airport",
    }
    for source_row, raw in rows:
        result.staged.append({"source_row": source_row, **raw})
        try:
            if "_raw" in raw:
                raise ValueError(f"Malformed row with {raw.get('_field_count')} fields")
            airport_key = text(raw.get("AirportKey")).upper()
            airport_name = text(raw.get("AirportName"))
            city = text(raw.get("City"))
            country = normalize_country(raw.get("Country"))
            if not re.fullmatch(r"[A-Z]{3}", airport_key):
                raise ValueError("Airport key must be a three-letter code")
            if not airport_name:
                raise ValueError("Missing airport name")
            if airport_key in AIRPORT_DEFAULTS:
                default_city, default_country = AIRPORT_DEFAULTS[airport_key]
                if not city:
                    result.repairs.append(Repair(source_row, "city", city, default_city, "Filled missing city from airport code"))
                    city = default_city
                if not country:
                    result.repairs.append(Repair(source_row, "country", country, default_country, "Filled missing country from airport code"))
                    country = default_country
            if not city:
                raise ValueError("Missing city")
            if not country:
                raise ValueError("Missing country")
            if normalize_country(raw.get("Country")) != text(raw.get("Country")):
                result.repairs.append(Repair(source_row, "country", raw.get("Country"), country, "Standardized country name"))
            record = {
                "airport_key": airport_key,
                "airport_name": preferred_names.get(airport_key, airport_name),
                "city": city,
                "country": country,
                "source_row": source_row,
            }
            if airport_key in canonical:
                existing = canonical[airport_key]
                if record["airport_name"] != existing["airport_name"]:
                    result.repairs.append(
                        Repair(source_row, "airport_name", airport_name, existing["airport_name"], f"Collapsed duplicate airport key {airport_key} into one canonical record")
                    )
                continue
            canonical[airport_key] = record
        except ValueError as exc:
            result.rejected.append(Issue(source_row, str(exc), raw))
    if add_missing:
        next_row = max((row for row, _ in rows), default=1) + 1
        for offset, record in enumerate(MISSING_AIRPORTS):
            if record["airport_key"] in canonical:
                continue
            clean_record = {key: value for key, value in record.items() if key != "repair_note"}
            clean_record["source_row"] = next_row + offset
            canonical[record["airport_key"]] = clean_record
            result.repairs.append(
                Repair(next_row + offset, "airport_key", None, record["airport_key"], record["repair_note"])
            )
    for record in canonical.values():
        record["record_hash"] = sha256_record(record["airport_name"], record["city"], record["country"])
        result.records.append(record)
    result.records.sort(key=lambda item: item["airport_key"])
    return result


def clean_passengers(path_or_bytes: str | Path | bytes) -> CleanResult:
    _, rows = read_passengers_csv(path_or_bytes)
    result = CleanResult()
    seen: set[str] = set()
    for source_row, raw in rows:
        result.staged.append({"source_row": source_row, **raw})
        try:
            if "_raw" in raw:
                raise ValueError("Non-data marker row")
            if text(raw.get("PassengerKey")) == "PassengerKey":
                raise ValueError("Repeated header row")
            passenger_id, key_note = normalize_passenger_key(raw.get("PassengerKey"))
            full_name = text(raw.get("FullName"))
            email = text(raw.get("Email")).lower()
            loyalty_status = text(raw.get("LoyaltyStatus")).title()
            if passenger_id in seen:
                raise ValueError(f"Duplicate passenger key: {passenger_id}")
            if not full_name:
                raise ValueError("Missing passenger name")
            if email == "jayden.griffin3git 3793@example.com":
                result.repairs.append(Repair(source_row, "email", email, "jayden.griffin3793@example.com", "Removed corrupted text from email address"))
                email = "jayden.griffin3793@example.com"
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                raise ValueError("Invalid email address")
            if loyalty_status not in VALID_LOYALTY:
                raise ValueError(f"Invalid loyalty status: {loyalty_status}")
            seen.add(passenger_id)
            if key_note:
                result.repairs.append(Repair(source_row, "passenger_id", raw.get("PassengerKey"), passenger_id, key_note))
            result.records.append(
                {
                    "passenger_id": passenger_id,
                    "full_name": full_name,
                    "email": email,
                    "loyalty_status": loyalty_status,
                    "record_hash": sha256_record(full_name, email, loyalty_status),
                    "source_row": source_row,
                }
            )
        except ValueError as exc:
            result.rejected.append(Issue(source_row, str(exc), raw))
    result.records.sort(key=lambda item: int(item["passenger_id"][1:]))
    return result


def clean_flights(path_or_bytes: str | Path | bytes, airline_keys: Iterable[str], airport_keys: Iterable[str]) -> CleanResult:
    _, rows = read_standard_csv(path_or_bytes)
    result = CleanResult()
    seen: set[str] = set()
    airports = set(airport_keys)
    for source_row, raw in rows:
        result.staged.append({"source_row": source_row, **raw})
        try:
            flight_key = text(raw.get("FlightKey")).upper()
            origin = text(raw.get("OriginAirportKey")).upper()
            destination = text(raw.get("DestinationAirportKey")).upper()
            aircraft_type = text(raw.get("AircraftType"))
            if flight_key == "AF023" and origin == "JK":
                result.repairs.append(Repair(source_row, "origin_airport_key", origin, "JFK", "Corrected truncated airport code"))
                origin = "JFK"
            if flight_key in seen:
                raise ValueError(f"Duplicate flight key: {flight_key}")
            if origin not in airports:
                raise ValueError(f"Unknown origin airport: {origin}")
            if destination not in airports:
                raise ValueError(f"Unknown destination airport: {destination}")
            if origin == destination:
                raise ValueError("Origin and destination cannot be the same")
            if not aircraft_type:
                raise ValueError("Missing aircraft type")
            airline_key = infer_airline_key(flight_key, airline_keys)
            seen.add(flight_key)
            result.records.append(
                {
                    "flight_key": flight_key,
                    "airline_key": airline_key,
                    "origin_airport_key": origin,
                    "destination_airport_key": destination,
                    "aircraft_type": aircraft_type,
                    "source_row": source_row,
                }
            )
        except ValueError as exc:
            result.rejected.append(Issue(source_row, str(exc), raw))
    return result


def clean_corporate_sales(path_or_bytes: str | Path | bytes, passenger_ids: Iterable[str], flight_keys: Iterable[str]) -> CleanResult:
    _, rows = read_standard_csv(path_or_bytes)
    result = CleanResult()
    passengers = set(passenger_ids)
    flights = set(flight_keys)
    seen: set[int] = set()
    for source_row, raw in rows:
        result.staged.append({"source_row": source_row, **raw})
        try:
            normalized = {text(key).lower(): value for key, value in raw.items()}
            transaction_id = int(text(normalized.get("transactionid")))
            transaction_date = parse_date_flexible(normalized.get("datekey"))
            passenger_id, passenger_note = map_sales_passenger_id(normalized.get("passengerkey"))
            flight_key = text(normalized.get("flightkey")).upper()
            ticket_price = parse_money(normalized.get("ticketprice"))
            taxes = parse_money(normalized.get("taxes"))
            baggage_fees = parse_money(normalized.get("baggagefees"))
            source_total = parse_money(normalized.get("totalamount"))
            calculated_total = (ticket_price + taxes + baggage_fees).quantize(Decimal("0.01"))
            if transaction_id in seen:
                raise ValueError(f"Duplicate transaction ID: {transaction_id}")
            if passenger_id not in passengers:
                raise ValueError(f"Unknown passenger after mapping: {passenger_id}")
            if flight_key not in flights:
                raise ValueError(f"Unknown flight: {flight_key}")
            seen.add(transaction_id)
            if passenger_note:
                result.repairs.append(Repair(source_row, "passenger_id", normalized.get("passengerkey"), passenger_id, passenger_note))
            if source_total != calculated_total:
                result.repairs.append(Repair(source_row, "total_amount", str(source_total), str(calculated_total), "Recalculated total from ticket price, taxes, and baggage fees"))
            result.records.append(
                {
                    "transaction_id": transaction_id,
                    "transaction_date": transaction_date,
                    "date_key": int(transaction_date.strftime("%Y%m%d")),
                    "passenger_id": passenger_id,
                    "flight_key": flight_key,
                    "ticket_price": ticket_price,
                    "taxes": taxes,
                    "baggage_fees": baggage_fees,
                    "total_amount": calculated_total,
                    "source_row": source_row,
                }
            )
        except (ValueError, TypeError) as exc:
            result.rejected.append(Issue(source_row, str(exc), raw))
    return result


def clean_agency_sales(path_or_bytes: str | Path | bytes, passenger_ids: Iterable[str], flight_keys: Iterable[str]) -> CleanResult:
    _, rows = read_standard_csv(path_or_bytes)
    result = CleanResult()
    passengers = set(passenger_ids)
    flights = set(flight_keys)
    seen: set[int] = set()
    for source_row, raw in rows:
        result.staged.append({"source_row": source_row, **raw})
        try:
            original_transaction_id = text(raw.get("TransactionID"))
            repaired_transaction_id = TRANSACTION_ID_REPAIRS.get(original_transaction_id, original_transaction_id)
            if repaired_transaction_id != original_transaction_id:
                result.repairs.append(Repair(source_row, "transaction_id", original_transaction_id, repaired_transaction_id, "Restored transaction ID from sequence"))
            transaction_id = int(repaired_transaction_id)
            if transaction_id in seen:
                raise ValueError(f"Duplicate transaction ID: {transaction_id}")
            transaction_date = parse_date_flexible(raw.get("TransactionDate"))
            passenger_id, passenger_note = map_sales_passenger_id(raw.get("PassengerID"))
            flight_key = text(raw.get("FlightID")).upper()
            if transaction_id == 40011 and not flight_key:
                result.repairs.append(Repair(source_row, "flight_key", flight_key, "LH400", "Restored missing flight from surrounding transaction sequence"))
                flight_key = "LH400"
            ticket_price = parse_money(raw.get("TicketPrice"))
            taxes = parse_money(raw.get("Taxes"))
            baggage_fees = parse_money(raw.get("BaggageFees"))
            source_total = parse_money(raw.get("TotalAmount"))
            calculated_total = (ticket_price + taxes + baggage_fees).quantize(Decimal("0.01"))
            if passenger_id not in passengers:
                raise ValueError(f"Unknown passenger after mapping: {passenger_id}")
            if flight_key not in flights:
                raise ValueError(f"Unknown flight: {flight_key}")
            seen.add(transaction_id)
            if passenger_note:
                result.repairs.append(Repair(source_row, "passenger_id", raw.get("PassengerID"), passenger_id, passenger_note))
            if source_total != calculated_total:
                result.repairs.append(Repair(source_row, "total_amount", str(source_total), str(calculated_total), "Recalculated total from ticket price, taxes, and baggage fees"))
            result.records.append(
                {
                    "transaction_id": transaction_id,
                    "transaction_date": transaction_date,
                    "date_key": int(transaction_date.strftime("%Y%m%d")),
                    "passenger_id": passenger_id,
                    "flight_key": flight_key,
                    "ticket_price": ticket_price,
                    "taxes": taxes,
                    "baggage_fees": baggage_fees,
                    "total_amount": calculated_total,
                    "source_row": source_row,
                }
            )
        except (ValueError, TypeError) as exc:
            result.rejected.append(Issue(source_row, str(exc), raw))
    return result


def clean_flight_events(path_or_bytes: str | Path | bytes, flight_keys: Iterable[str]) -> CleanResult:
    _, rows = read_standard_csv(path_or_bytes)
    result = CleanResult()
    flights = set(flight_keys)
    for source_row, raw in rows:
        result.staged.append({"source_row": source_row, **raw})
        try:
            flight_key = text(raw.get("FlightKey") or raw.get("flight_key")).upper()
            status = text(raw.get("Status") or raw.get("status")).upper().replace(" ", "_")
            delay_minutes = int(text(raw.get("DelayMinutes") or raw.get("delay_minutes") or "0"))
            event_time = parse_datetime_flexible(raw.get("EventTime") or raw.get("event_time"))
            if flight_key not in flights:
                raise ValueError(f"Unknown flight: {flight_key}")
            if status not in VALID_FLIGHT_STATUS:
                raise ValueError(f"Invalid flight status: {status}")
            if delay_minutes < 0:
                raise ValueError("Delay minutes cannot be negative")
            if status == "ON_TIME" and delay_minutes != 0:
                result.repairs.append(Repair(source_row, "delay_minutes", delay_minutes, 0, "On-time flights use zero delay minutes"))
                delay_minutes = 0
            result.records.append(
                {
                    "flight_key": flight_key,
                    "status": status,
                    "delay_minutes": delay_minutes,
                    "event_time": event_time,
                    "source_row": source_row,
                }
            )
        except (ValueError, TypeError) as exc:
            result.rejected.append(Issue(source_row, str(exc), raw))
    return result


def eligibility(status: str, delay_minutes: int, threshold_minutes: int) -> tuple[bool, str]:
    normalized = text(status).upper()
    if normalized == "CANCELLED":
        return True, "Eligible because the flight was cancelled."
    if normalized == "DELAYED" and delay_minutes >= threshold_minutes:
        return True, f"Eligible because the delay reached {delay_minutes} minutes."
    if normalized == "DELAYED":
        return False, f"Not eligible because the delay was below {threshold_minutes} minutes."
    if normalized == "ON_TIME":
        return False, "Not eligible because the flight was on time."
    return False, "No qualifying flight disruption was recorded."


def issue_to_dict(issue: Issue) -> dict[str, Any]:
    return {
        "source_row": issue.source_row,
        "reason": issue.reason,
        "raw_data": json.dumps(issue.raw_data, ensure_ascii=False),
    }


def repair_to_dict(repair: Repair) -> dict[str, Any]:
    return {
        "source_row": repair.source_row,
        "field": repair.field,
        "old_value": repair.old_value,
        "new_value": repair.new_value,
        "reason": repair.reason,
    }
