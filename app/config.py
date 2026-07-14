import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Airport Data Warehouse")
    database_url: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{Path(__file__).resolve().parents[1] / 'airport_dw.db'}",
    )
    eligibility_delay_minutes: int = int(os.getenv("ELIGIBILITY_DELAY_MINUTES", "180"))
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
    kafka_topic: str = os.getenv("KAFKA_TOPIC", "flight-status-updates")
    api_base_url: str = os.getenv("API_BASE_URL", "http://localhost:8000")


settings = Settings()
