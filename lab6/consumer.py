"""Консьюмер: читает события из Kafka, считает tumbling-окна и сохраняет агрегаты в ClickHouse."""
import json
import os
from collections import defaultdict
from datetime import datetime

import requests
from kafka import KafkaConsumer

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092")
CLICKHOUSE_URL = os.getenv("CLICKHOUSE_URL", "http://127.0.0.1:8123")
WINDOW_SIZE = int(os.getenv("WINDOW_SECONDS", "5"))  # 5 секунд для демонстрации (в реальности - 300 = 5 минут)

consumer = KafkaConsumer(
    "user_events",
    bootstrap_servers=BOOTSTRAP,
    auto_offset_reset="latest",
    group_id="lab6-aggregator",
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)


def save_to_clickhouse(agg: dict) -> None:
    """Вставка одной строки агрегатов через HTTP-интерфейс ClickHouse (JSONEachRow)."""
    row = dict(agg)
    # DateTime в ClickHouse хранится с точностью до секунды
    for k in ("window_start", "window_end"):
        row[k] = datetime.fromisoformat(row[k]).strftime("%Y-%m-%d %H:%M:%S")
    r = requests.post(
        CLICKHOUSE_URL,
        params={"query": "INSERT INTO analytics.stream_aggregates FORMAT JSONEachRow"},
        data=json.dumps(row),
        timeout=10,
    )
    r.raise_for_status()


window_data = defaultdict(list)
window_start = None
print(f"Consumer started, window = {WINDOW_SIZE} s", flush=True)

for message in consumer:
    event = message.value
    current_time = datetime.fromisoformat(event["timestamp"])
    if window_start is None:
        window_start = current_time

    # Если окно истекло - сохраняем агрегаты и открываем новое (tumbling window)
    if (current_time - window_start).total_seconds() >= WINDOW_SIZE:
        aggregated = {
            "window_start": window_start.isoformat(),
            "window_end": current_time.isoformat(),
            "total_clicks": len(window_data.get("click", [])),
            "total_views": len(window_data.get("view", [])),
            "total_purchases": len(window_data.get("purchase", [])),
            "total_revenue": round(sum(window_data.get("purchase", [])), 2),
        }
        save_to_clickhouse(aggregated)
        print(f"Window saved: {aggregated}", flush=True)
        window_data.clear()
        window_start = current_time

    # Добавляем событие в (возможно новое) окно
    window_data[event["event_type"]].append(event["amount"])
