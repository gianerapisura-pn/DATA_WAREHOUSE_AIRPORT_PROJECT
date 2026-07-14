from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    batch_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_name: Mapped[str] = mapped_column(String(60), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    rows_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_loaded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_repaired: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="RUNNING", nullable=False)


class RejectedRecord(Base):
    __tablename__ = "rejected_records"

    rejection_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("ingestion_batches.batch_id"), nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(60), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_data: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class StgAirline(Base):
    __tablename__ = "stg_airlines"

    staging_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("ingestion_batches.batch_id"), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    airline_key: Mapped[str | None] = mapped_column(Text)
    airline_name: Mapped[str | None] = mapped_column(Text)
    alliance: Mapped[str | None] = mapped_column(Text)


class StgAirport(Base):
    __tablename__ = "stg_airports"

    staging_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("ingestion_batches.batch_id"), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    airport_key: Mapped[str | None] = mapped_column(Text)
    airport_name: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)


class StgFlight(Base):
    __tablename__ = "stg_flights"

    staging_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("ingestion_batches.batch_id"), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    flight_key: Mapped[str | None] = mapped_column(Text)
    origin_airport_key: Mapped[str | None] = mapped_column(Text)
    destination_airport_key: Mapped[str | None] = mapped_column(Text)
    aircraft_type: Mapped[str | None] = mapped_column(Text)


class StgPassenger(Base):
    __tablename__ = "stg_passengers"

    staging_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("ingestion_batches.batch_id"), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    passenger_id: Mapped[str | None] = mapped_column(Text)
    full_name: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    loyalty_status: Mapped[str | None] = mapped_column(Text)


class StgCorporateSale(Base):
    __tablename__ = "stg_corporate_sales"

    staging_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("ingestion_batches.batch_id"), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(Text)
    date_key: Mapped[str | None] = mapped_column(Text)
    passenger_id: Mapped[str | None] = mapped_column(Text)
    flight_key: Mapped[str | None] = mapped_column(Text)
    ticket_price: Mapped[str | None] = mapped_column(Text)
    taxes: Mapped[str | None] = mapped_column(Text)
    baggage_fees: Mapped[str | None] = mapped_column(Text)
    total_amount: Mapped[str | None] = mapped_column(Text)


class StgAgencySale(Base):
    __tablename__ = "stg_agency_sales"

    staging_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("ingestion_batches.batch_id"), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(Text)
    transaction_date: Mapped[str | None] = mapped_column(Text)
    passenger_id: Mapped[str | None] = mapped_column(Text)
    flight_key: Mapped[str | None] = mapped_column(Text)
    ticket_price: Mapped[str | None] = mapped_column(Text)
    taxes: Mapped[str | None] = mapped_column(Text)
    baggage_fees: Mapped[str | None] = mapped_column(Text)
    total_amount: Mapped[str | None] = mapped_column(Text)


class StgFlightEvent(Base):
    __tablename__ = "stg_flight_events"

    staging_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("ingestion_batches.batch_id"), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    flight_key: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    delay_minutes: Mapped[str | None] = mapped_column(Text)
    event_time: Mapped[str | None] = mapped_column(Text)


class DimDate(Base):
    __tablename__ = "dim_date"

    date_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    full_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    day_of_month: Mapped[int] = mapped_column(Integer, nullable=False)
    day_name: Mapped[str] = mapped_column(String(12), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    month_name: Mapped[str] = mapped_column(String(12), nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    half_year: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    is_weekend: Mapped[bool] = mapped_column(Boolean, nullable=False)


class DimAirline(Base):
    __tablename__ = "dim_airline"
    __table_args__ = (UniqueConstraint("airline_key", "effective_from", name="uq_airline_version"),)

    airline_sk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    airline_key: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    airline_name: Mapped[str] = mapped_column(String(150), nullable=False)
    alliance: Mapped[str] = mapped_column(String(80), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class DimAirport(Base):
    __tablename__ = "dim_airport"
    __table_args__ = (UniqueConstraint("airport_key", "effective_from", name="uq_airport_version"),)

    airport_sk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    airport_key: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    airport_name: Mapped[str] = mapped_column(String(180), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class DimPassenger(Base):
    __tablename__ = "dim_passenger"
    __table_args__ = (UniqueConstraint("passenger_id", "effective_from", name="uq_passenger_version"),)

    passenger_sk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    passenger_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    loyalty_status: Mapped[str] = mapped_column(String(30), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class DimFlight(Base):
    __tablename__ = "dim_flight"

    flight_sk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flight_key: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    airline_sk: Mapped[int] = mapped_column(ForeignKey("dim_airline.airline_sk"), nullable=False)
    origin_airport_sk: Mapped[int] = mapped_column(ForeignKey("dim_airport.airport_sk"), nullable=False)
    destination_airport_sk: Mapped[int] = mapped_column(ForeignKey("dim_airport.airport_sk"), nullable=False)
    aircraft_type: Mapped[str] = mapped_column(String(80), nullable=False)


class FactCorporateSale(Base):
    __tablename__ = "fact_corporate_sales"

    corporate_sale_sk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    date_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"), nullable=False)
    passenger_sk: Mapped[int] = mapped_column(ForeignKey("dim_passenger.passenger_sk"), nullable=False)
    flight_sk: Mapped[int] = mapped_column(ForeignKey("dim_flight.flight_sk"), nullable=False)
    ticket_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    taxes: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    baggage_fees: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    batch_id: Mapped[int] = mapped_column(ForeignKey("ingestion_batches.batch_id"), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)


class FactAgencySale(Base):
    __tablename__ = "fact_agency_sales"

    agency_sale_sk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    date_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"), nullable=False)
    passenger_sk: Mapped[int] = mapped_column(ForeignKey("dim_passenger.passenger_sk"), nullable=False)
    flight_sk: Mapped[int] = mapped_column(ForeignKey("dim_flight.flight_sk"), nullable=False)
    ticket_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    taxes: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    baggage_fees: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    batch_id: Mapped[int] = mapped_column(ForeignKey("ingestion_batches.batch_id"), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)


class FlightStatusEvent(Base):
    __tablename__ = "flight_status_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flight_key: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    delay_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(40), default="API", nullable=False)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_batches.batch_id"))


class MartPassengerTicket(Base):
    __tablename__ = "mart_passenger_ticket"

    ticket_mart_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    transaction_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    date_key: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    passenger_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    passenger_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    passenger_email: Mapped[str] = mapped_column(String(255), nullable=False)
    loyalty_status: Mapped[str] = mapped_column(String(30), nullable=False)
    flight_key: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    airline_key: Mapped[str] = mapped_column(String(10), nullable=False)
    airline_name: Mapped[str] = mapped_column(String(150), nullable=False)
    origin_airport_code: Mapped[str] = mapped_column(String(10), nullable=False)
    origin_airport_name: Mapped[str] = mapped_column(String(180), nullable=False)
    origin_city: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_airport_code: Mapped[str] = mapped_column(String(10), nullable=False)
    destination_airport_name: Mapped[str] = mapped_column(String(180), nullable=False)
    destination_city: Mapped[str] = mapped_column(String(100), nullable=False)
    aircraft_type: Mapped[str] = mapped_column(String(80), nullable=False)
    ticket_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    taxes: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    baggage_fees: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    flight_status: Mapped[str] = mapped_column(String(20), nullable=False)
    delay_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    eligibility_reason: Mapped[str] = mapped_column(String(250), nullable=False)


class MartSalesSummary(Base):
    __tablename__ = "mart_sales_summary"
    __table_args__ = (
        UniqueConstraint("year", "quarter", "half_year", "month", "source_type", name="uq_sales_summary_period"),
    )

    summary_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    half_year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    month_name: Mapped[str] = mapped_column(String(12), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_sales: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    average_ticket_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    delayed_count: Mapped[int] = mapped_column(Integer, nullable=False)
    cancelled_count: Mapped[int] = mapped_column(Integer, nullable=False)
