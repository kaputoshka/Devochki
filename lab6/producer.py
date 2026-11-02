"""Продюсер: имитирует поток пользовательских событий и отправляет их в Kafka."""
import json
import os
import random
import time
from datetime import datetime

from kafka import KafkaProducer

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092")
TOPIC = "user_events"
DURATION = float(os.getenv("DURATION_SECONDS", "0"))  # 0 = бесконечно

producer = KafkaProducer(
    bootstrap_servers=BOOTSTRAP,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

started = time.time()
sent = 0
try:
    while DURATION == 0 or time.time() - started < DURATION:
        event = {
            "user_id": random.randint(1, 1000),
            "event_type": random.choices(["click", "view", "purchase"], weights=[5, 10, 1])[0],
            "product_id": random.randint(1, 100),
            "amount": round(random.uniform(10, 500), 2),
            "timestamp": datetime.now().isoformat(),
        }
        producer.send(TOPIC, value=event)
        sent += 1
        print(f"Sent: {event}", flush=True)
        time.sleep(random.uniform(0.1, 0.5))
finally:
    producer.flush()
    print(f"Producer stopped, events sent: {sent}", flush=True)
