-- Лабораторная работа №6. Таблица оконных агрегатов потока (ClickHouse)
CREATE TABLE IF NOT EXISTS analytics.stream_aggregates
(
    window_start    DateTime,
    window_end      DateTime,
    total_clicks    UInt32,
    total_views     UInt32,
    total_purchases UInt32,
    total_revenue   Decimal(10,2)
)
ENGINE = MergeTree()
ORDER BY window_start;
