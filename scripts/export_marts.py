import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal
from app.models import MartPassengerTicket, MartSalesSummary
from app.services.pipeline import export_table_to_csv


def main():
    output = ROOT / "data" / "exports"
    db = SessionLocal()
    try:
        export_table_to_csv(
            db,
            MartPassengerTicket,
            output / "mart_passenger_ticket.csv",
            [
                "source_type", "transaction_id", "transaction_date", "passenger_id", "passenger_name",
                "passenger_email", "loyalty_status", "flight_key", "airline_name", "origin_airport_code",
                "origin_airport_name", "origin_city", "destination_airport_code", "destination_airport_name",
                "destination_city", "aircraft_type", "ticket_price", "taxes", "baggage_fees", "total_amount",
                "flight_status", "delay_minutes", "is_eligible", "eligibility_reason",
            ],
        )
        export_table_to_csv(
            db,
            MartSalesSummary,
            output / "mart_sales_summary.csv",
            [
                "year", "quarter", "half_year", "month", "month_name", "source_type",
                "transaction_count", "total_sales", "average_ticket_value", "delayed_count", "cancelled_count",
            ],
        )
        print(f"Exported data marts to {output}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
