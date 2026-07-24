from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import SessionLocal
from app.main import app
from app.models import (
    DimDate,
    DimPassenger,
    IngestionBatch,
    FactAgencySale,
    FactCorporateSale,
    MartPassengerTicket,
)
from app.services.pipeline import load_date_dimension, process_dataset, search_tickets


def test_warehouse_counts():
    db = SessionLocal()
    try:
        assert db.scalar(select(func.count()).select_from(FactCorporateSale)) == 100
        assert db.scalar(select(func.count()).select_from(FactAgencySale)) == 298
        assert db.scalar(select(func.count()).select_from(MartPassengerTicket)) == 398
        assert db.scalar(select(func.count()).select_from(DimPassenger).where(DimPassenger.is_current.is_(True))) == 2822
    finally:
        db.close()


def test_scd_history_is_preserved():
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(DimPassenger)
            .where(DimPassenger.passenger_id == "P1001")
            .order_by(DimPassenger.effective_from)
        ).all()
        assert len(rows) == 2
        assert rows[0].full_name == "Mary Smith"
        assert rows[0].is_current is False
        assert rows[1].full_name == "Mary A. Smith"
        assert rows[1].is_current is True
    finally:
        db.close()


def test_mart_reconciles():
    db = SessionLocal()
    try:
        total = db.scalar(select(func.sum(MartPassengerTicket.total_amount)))
        corporate = db.scalar(select(func.sum(FactCorporateSale.total_amount)))
        agency = db.scalar(select(func.sum(FactAgencySale.total_amount)))
        assert Decimal(total) == Decimal(corporate) + Decimal(agency)
    finally:
        db.close()


def test_ticket_search():
    db = SessionLocal()
    try:
        rows = search_tickets(db, "AA100")
        assert len(rows) >= 2
        assert all(row.flight_key == "AA100" for row in rows)
        assert all(row.flight_status == "DELAYED" for row in rows)
    finally:
        db.close()


def test_api_health():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["tickets"] == 398


def test_lookup_page():
    with TestClient(app) as client:
        response = client.get("/lookup", params={"q": "P1001"})
        assert response.status_code == 200
        assert "Mary Smith" in response.text
        assert "AA100" in response.text


def test_date_dimension_extends_beyond_current_year():
    db = SessionLocal()
    try:
        load_date_dimension(db)
        max_date = db.scalar(select(func.max(DimDate.full_date)))
        assert max_date >= date(date.today().year + 1, 12, 31)
    finally:
        db.rollback()
        db.close()


def test_upload_rejects_wrong_columns():
    with TestClient(app) as client:
        response = client.post(
            "/api/upload",
            data={"dataset_name": "airlines"},
            files={"file": ("bad.csv", b"Wrong,Columns\nA,B\n", "text/csv")},
        )
        assert response.status_code == 400
        assert "Missing required column" in response.json()["detail"]


def test_failed_upload_keeps_failed_batch_without_loading_rows():
    db = SessionLocal()
    before = db.scalar(select(func.count()).select_from(IngestionBatch)) or 0
    db.close()

    db = SessionLocal()
    try:
        try:
            process_dataset(db, "airlines", "invalid.csv", b"\xff\xfe")
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid upload to fail")
    finally:
        db.close()

    db = SessionLocal()
    try:
        after = db.scalar(select(func.count()).select_from(IngestionBatch)) or 0
        latest = db.scalar(select(IngestionBatch).order_by(IngestionBatch.batch_id.desc()).limit(1))
        assert after == before + 1
        assert latest.status == "FAILED"
        assert latest.dataset_name == "airlines"
        assert latest.rows_loaded == 0
    finally:
        db.close()
