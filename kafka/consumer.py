import json
import os

import httpx
from kafka import KafkaConsumer

BROKERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092").split(",")
TOPIC = os.getenv("KAFKA_TOPIC", "flight-status-updates")
API_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/") + "/api/events/flight-status"


def main():
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BROKERS,
        group_id="airport-dw-consumer",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    with httpx.Client(timeout=20) as client:
        for message in consumer:
            response = client.post(API_URL, json=message.value)
            response.raise_for_status()
            print(json.dumps({"offset": message.offset, "result": response.json()}))


if __name__ == "__main__":
    main()
