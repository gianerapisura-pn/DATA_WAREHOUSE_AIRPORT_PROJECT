import csv
import json
import os
import sys
from pathlib import Path

from kafka import KafkaProducer

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.getenv("EVENT_FILE", ROOT / "data" / "demo" / "flight_status_events.csv"))
BROKERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092").split(",")
TOPIC = os.getenv("KAFKA_TOPIC", "flight-status-updates")


def main():
    producer = KafkaProducer(
        bootstrap_servers=BROKERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        key_serializer=lambda value: value.encode("utf-8"),
    )
    count = 0
    with SOURCE.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            payload = {
                "flight_key": row["FlightKey"],
                "status": row["Status"],
                "delay_minutes": int(row["DelayMinutes"]),
                "event_time": row["EventTime"],
                "source": "KAFKA",
            }
            producer.send(TOPIC, key=payload["flight_key"], value=payload).get(timeout=10)
            count += 1
    producer.flush()
    producer.close()
    print(f"Published {count} events to {TOPIC}")


if __name__ == "__main__":
    main()
