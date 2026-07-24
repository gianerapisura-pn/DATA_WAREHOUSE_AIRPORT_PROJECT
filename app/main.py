from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.models import (
    DimFlight,
    DimPassenger,
    FlightStatusEvent,
    IngestionBatch,
    MartPassengerTicket,
    MartSalesSummary,
    RejectedRecord,
)
from app.services.cleaning import read_standard_csv, eligibility
from app.services.pipeline import (
    dashboard_metrics,
    load_flight_status_events,
    process_dataset,
    refresh_marts,
    search_tickets,
)


ROOT = Path(__file__).resolve().parent
@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "templates")


class FlightEventPayload(BaseModel):
    flight_key: str = Field(min_length=2, max_length=20)
    status: str
    delay_minutes: int = Field(default=0, ge=0)
    event_time: datetime
    source: str = "API"


def money(value: Decimal | float | int) -> str:
    return f"${Decimal(value):,.2f}"


templates.env.filters["money"] = money

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
EXPECTED_COLUMNS = {
    "airlines": {"AirlineKey", "AirlineName", "Alliance"},
    "airports": {"AirportKey", "AirportName", "City", "Country"},
    "passengers": {"PassengerKey", "FullName", "Email", "LoyaltyStatus"},
    "passenger_updates": {"PassengerKey", "FullName", "Email", "LoyaltyStatus"},
    "flights": {"FlightKey", "OriginAirportKey", "DestinationAirportKey", "AircraftType"},
    "corporate_sales": {"TransactionID", "DateKey", "PassengerKey", "FlightKey", "TicketPrice", "Taxes", "BaggageFees", "TotalAmount"},
    "travel_agency_sales": {"TransactionID", "TransactionDate", "PassengerID", "FlightID", "TicketPrice", "Taxes", "BaggageFees", "TotalAmount"},
    "flight_status_events": {"FlightKey", "Status", "DelayMinutes", "EventTime"},
}


def validate_upload(dataset_name: str, filename: str, content: bytes) -> None:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in {".csv", ".txt"}:
        raise HTTPException(status_code=400, detail="Upload a CSV or TXT file")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Uploaded file is larger than 2 MB")
    try:
        columns, _ = read_standard_csv(content)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File must use UTF-8 text encoding") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="File could not be read as CSV") from exc
    missing = EXPECTED_COLUMNS[dataset_name] - set(columns)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise HTTPException(status_code=400, detail=f"Missing required column(s): {missing_list}")


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    metrics = dashboard_metrics(db)
    summaries = db.scalars(
        select(MartSalesSummary).order_by(MartSalesSummary.year, MartSalesSummary.month, MartSalesSummary.source_type)
    ).all()
    recent_batches = db.scalars(select(IngestionBatch).order_by(IngestionBatch.batch_id.desc()).limit(8)).all()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"metrics": metrics, "summaries": summaries, "recent_batches": recent_batches},
    )


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse(request=request, name="upload.html", context={})


@app.post("/api/upload")
async def upload_dataset(
    dataset_name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    allowed = {
        "airlines",
        "airports",
        "passengers",
        "passenger_updates",
        "flights",
        "corporate_sales",
        "travel_agency_sales",
        "flight_status_events",
    }
    if dataset_name not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported dataset type")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")
    filename = file.filename or "upload.csv"
    validate_upload(dataset_name, filename, content)
    try:
        return JSONResponse(process_dataset(db, dataset_name, filename, content))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="The file could not be processed") from exc


@app.get("/lookup", response_class=HTMLResponse)
def lookup_page(request: Request, q: str = "", db: Session = Depends(get_db)):
    tickets = search_tickets(db, q, limit=30) if q.strip() else []
    return templates.TemplateResponse(
        request=request,
        name="lookup.html",
        context={"query": q, "tickets": tickets, "delay_threshold": settings.eligibility_delay_minutes},
    )


@app.get("/api/tickets/search")
def ticket_search(q: str, db: Session = Depends(get_db)):
    tickets = search_tickets(db, q, limit=30)
    return [
        {
            "source_type": ticket.source_type,
            "transaction_id": ticket.transaction_id,
            "transaction_date": ticket.transaction_date.isoformat(),
            "passenger_id": ticket.passenger_id,
            "passenger_name": ticket.passenger_name,
            "passenger_email": ticket.passenger_email,
            "loyalty_status": ticket.loyalty_status,
            "flight_key": ticket.flight_key,
            "airline_name": ticket.airline_name,
            "origin_airport_code": ticket.origin_airport_code,
            "origin_airport_name": ticket.origin_airport_name,
            "origin_city": ticket.origin_city,
            "destination_airport_code": ticket.destination_airport_code,
            "destination_airport_name": ticket.destination_airport_name,
            "destination_city": ticket.destination_city,
            "aircraft_type": ticket.aircraft_type,
            "ticket_price": float(ticket.ticket_price),
            "taxes": float(ticket.taxes),
            "baggage_fees": float(ticket.baggage_fees),
            "total_amount": float(ticket.total_amount),
            "flight_status": ticket.flight_status,
            "delay_minutes": ticket.delay_minutes,
            "is_eligible": ticket.is_eligible,
            "eligibility_reason": ticket.eligibility_reason,
        }
        for ticket in tickets
    ]


@app.get("/quality", response_class=HTMLResponse)
def quality_page(request: Request, db: Session = Depends(get_db)):
    batches = db.scalars(select(IngestionBatch).order_by(IngestionBatch.batch_id.desc()).limit(50)).all()
    rejections = db.scalars(select(RejectedRecord).order_by(RejectedRecord.rejection_id.desc()).limit(100)).all()
    return templates.TemplateResponse(
        request=request,
        name="quality.html",
        context={"batches": batches, "rejections": rejections},
    )


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request, passenger_id: str = "P1001", db: Session = Depends(get_db)):
    history = db.scalars(
        select(DimPassenger)
        .where(DimPassenger.passenger_id == passenger_id.strip().upper())
        .order_by(DimPassenger.effective_from.desc())
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={"passenger_id": passenger_id, "history": history},
    )


@app.post("/api/events/flight-status")
def receive_flight_event(payload: FlightEventPayload, db: Session = Depends(get_db)):
    normalized_status = payload.status.upper().replace(" ", "_")
    eligible, reason = eligibility(normalized_status, payload.delay_minutes, settings.eligibility_delay_minutes)
    existing_flight = db.scalar(select(DimFlight).where(DimFlight.flight_key == payload.flight_key.upper()).limit(1))
    if not existing_flight:
        raise HTTPException(status_code=404, detail="Flight key is not present in the warehouse")
    record = {
        "flight_key": payload.flight_key.upper(),
        "status": normalized_status,
        "delay_minutes": payload.delay_minutes,
        "event_time": payload.event_time,
    }
    loaded = load_flight_status_events(db, [record], None, payload.source)
    refresh_marts(db)
    db.commit()
    return {"loaded": loaded, "is_eligible": eligible, "reason": reason}


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    ticket_count = db.scalar(select(func.count()).select_from(MartPassengerTicket)) or 0
    return {"status": "ok", "tickets": int(ticket_count), "delay_threshold": settings.eligibility_delay_minutes}
