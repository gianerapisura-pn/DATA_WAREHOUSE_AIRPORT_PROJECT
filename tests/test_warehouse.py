from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import SessionLocal
from app.main import app
from app.models import (
    DimPassenger,
    FactAgencySale,
    FactCorporateSale,
    MartPassengerTicket,
)
from app.services.pipeline import search_tickets


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
