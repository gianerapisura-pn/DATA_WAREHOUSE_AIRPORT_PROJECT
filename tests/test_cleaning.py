from pathlib import Path

from app.services.cleaning import (
    clean_agency_sales,
    clean_airlines,
    clean_airports,
    clean_corporate_sales,
    clean_flights,
    clean_passengers,
    eligibility,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def prepared_results():
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
    return airlines, airports, passengers, flights, corporate, agency


def test_cleaned_row_counts():
    airlines, airports, passengers, flights, corporate, agency = prepared_results()
    assert len(airlines.records) == 39
    assert len(airports.records) == 221
    assert len(passengers.records) == 2822
    assert len(flights.records) == 390
    assert len(corporate.records) == 100
    assert len(agency.records) == 298
    assert len(passengers.rejected) == 9
    assert len(agency.rejected) == 3


def test_reference_integrity_after_cleaning():
    airlines, airports, passengers, flights, corporate, agency = prepared_results()
    airline_keys = {row["airline_key"] for row in airlines.records}
    airport_keys = {row["airport_key"] for row in airports.records}
    passenger_ids = {row["passenger_id"] for row in passengers.records}
    flight_keys = {row["flight_key"] for row in flights.records}
    assert all(row["airline_key"] in airline_keys for row in flights.records)
    assert all(row["origin_airport_key"] in airport_keys for row in flights.records)
    assert all(row["destination_airport_key"] in airport_keys for row in flights.records)
    assert all(row["passenger_id"] in passenger_ids for row in corporate.records + agency.records)
    assert all(row["flight_key"] in flight_keys for row in corporate.records + agency.records)


def test_amounts_reconcile():
    _, _, _, _, corporate, agency = prepared_results()
    for row in corporate.records + agency.records:
        assert row["ticket_price"] + row["taxes"] + row["baggage_fees"] == row["total_amount"]


def test_known_repairs():
    _, airports, passengers, flights, corporate, agency = prepared_results()
    assert any(row["airport_key"] == "DOH" for row in airports.records)
    assert next(row for row in flights.records if row["flight_key"] == "AF023")["origin_airport_key"] == "JFK"
    assert next(row for row in passengers.records if row["passenger_id"] == "P1592")["full_name"] == "Kathleen Rice"
    assert next(row for row in corporate.records if row["transaction_id"] == 10092)["total_amount"] == 1305
    assert next(row for row in agency.records if row["transaction_id"] == 40011)["flight_key"] == "LH400"
    assert next(row for row in agency.records if row["transaction_id"] == 40005)["passenger_id"] == "P1001"


def test_eligibility_rule():
    assert eligibility("CANCELLED", 0, 180)[0] is True
    assert eligibility("DELAYED", 180, 180)[0] is True
    assert eligibility("DELAYED", 179, 180)[0] is False
    assert eligibility("ON_TIME", 0, 180)[0] is False
