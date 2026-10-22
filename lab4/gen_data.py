"""Генерация синтетических продаж розничной сети (2024–2025) и загрузка в PostgreSQL.

В данные заложены закономерности, которые должен «рассказать» дашборд:
сезонность (пик в декабре), рост 2025 к 2024, акция «Чёрная пятница» в электронике
в ноябре 2025 г., просадка магазинов Сибири со второго полугодия 2025 г.
(открытие конкурента), пик продаж по субботам.
"""
import logging
import os
from datetime import date

import numpy as np
import pandas as pd
import psycopg

log = logging.getLogger("gen_data")

DSN = os.environ.get("PG_DSN", "postgresql://lab4:lab4@127.0.0.1:5434/retail")
SEED = 42
START, END = date(2024, 1, 1), date(2025, 12, 31)

STORES = [  # store_id, город, федеральный округ, широта, долгота, коэффициент трафика
    (1, "Москва", "Центр", 55.76, 37.62, 1.8), (2, "Санкт-Петербург", "Северо-Запад", 59.94, 30.31, 1.5),
    (3, "Казань", "Поволжье", 55.79, 49.12, 1.0), (4, "Уфа", "Поволжье", 54.73, 55.96, 1.0),
    (5, "Самара", "Поволжье", 53.20, 50.15, 0.9), (6, "Нижний Новгород", "Поволжье", 56.33, 44.00, 0.9),
    (7, "Екатеринбург", "Урал", 56.84, 60.61, 1.1), (8, "Челябинск", "Урал", 55.16, 61.40, 0.8),
    (9, "Новосибирск", "Сибирь", 55.03, 82.92, 1.0), (10, "Красноярск", "Сибирь", 56.01, 92.87, 0.8),
    (11, "Краснодар", "Юг", 45.04, 38.98, 1.0), (12, "Ростов-на-Дону", "Юг", 47.23, 39.72, 0.9),
]
CATEGORIES = {  # категория: (базовая интенсивность заказов в день на магазин и товар, товары с ценами)
    "Электроника": (0.22, [("Смартфон", 32990), ("Ноутбук", 64990), ("Наушники", 7990),
                           ("Планшет", 27990), ("Умные часы", 14990)]),
    "Бытовая техника": (0.30, [("Пылесос", 18990), ("Микроволновая печь", 8990), ("Чайник", 2990),
                               ("Кофемашина", 34990), ("Утюг", 4490)]),
    "Одежда": (1.00, [("Куртка", 7990), ("Джинсы", 3990), ("Футболка", 1290),
                      ("Кроссовки", 5990), ("Свитер", 3490)]),
    "Дом и сад": (0.90, [("Набор посуды", 4990), ("Постельное бельё", 3290), ("Садовый инвентарь", 2490),
                         ("Светильник", 2190), ("Органайзер", 890)]),
    "Спорт": (0.55, [("Велосипед", 24990), ("Гантели", 3490), ("Коврик для йоги", 1490),
                     ("Палатка", 8990), ("Самокат", 9990)]),
    "Красота": (1.30, [("Крем для лица", 1190), ("Шампунь", 590), ("Парфюм", 4590),
                       ("Фен", 3990), ("Набор косметики", 2290)]),
}
MONTH_SEASON = np.array([0.85, 0.85, 0.95, 0.95, 1.0, 0.95, 0.95, 1.0, 1.0, 1.05, 1.2, 1.45])
CATEGORY_SEASON = {  # категория: {месяц: множитель}
    "Электроника": {11: 1.3, 12: 1.2}, "Бытовая техника": {11: 1.2},
    "Одежда": {9: 1.15, 10: 1.15, 12: 1.2}, "Дом и сад": {4: 1.4, 5: 1.4, 6: 1.3},
    "Спорт": {5: 1.3, 6: 1.35, 7: 1.35, 8: 1.25},
}
DOW = np.array([0.85, 0.85, 0.9, 0.95, 1.1, 1.3, 1.15])  # пн..вс
SIBERIA_DROP = 0.7       # коэффициент продаж магазинов Сибири с июля 2025
PROMO = ("Электроника", 2025, 11, 2.0, 0.15)  # категория, год, месяц, рост спроса, скидка


def build_dimensions() -> tuple[pd.DataFrame, pd.DataFrame]:
    stores = pd.DataFrame(STORES, columns=["store_id", "city", "region", "lat", "lon", "traffic"])
    rows, pid = [], 1
    for cat, (_, items) in CATEGORIES.items():
        for name, price in items:
            rows.append((pid, name, cat, float(price)))
            pid += 1
    products = pd.DataFrame(rows, columns=["product_id", "product_name", "category", "base_price"])
    return stores, products


def generate_sales(stores: pd.DataFrame, products: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """Возвращает таблицу фактов: одна строка — один заказ (одна товарная позиция)."""
    rng = np.random.default_rng(seed)
    days = pd.date_range(START, END, freq="D")
    month, year, dow = days.month.to_numpy(), days.year.to_numpy(), days.dayofweek.to_numpy()

    # интенсивность заказов: день × магазин × товар
    cat_rate = products["category"].map(lambda c: CATEGORIES[c][0]).to_numpy()
    prod_rate = cat_rate * rng.uniform(0.6, 1.4, len(products))
    day_k = MONTH_SEASON[month - 1] * DOW[dow]
    t = (days - days[0]).days.to_numpy() / len(days)
    day_k = day_k * (1 + 0.12 * 2 * t)  # плавный рост ≈ 12 % в год
    lam = day_k[:, None, None] * stores["traffic"].to_numpy()[None, :, None] * prod_rate[None, None, :]

    cats = products["category"].to_numpy()
    for cat, months in CATEGORY_SEASON.items():
        for m, k in months.items():
            lam[np.ix_(month == m, np.ones(len(stores), bool), cats == cat)] *= k
    promo_cat, promo_y, promo_m, promo_k, promo_disc = PROMO
    promo_days = (year == promo_y) & (month == promo_m)
    lam[np.ix_(promo_days, np.ones(len(stores), bool), cats == promo_cat)] *= promo_k
    siberia = (stores["region"] == "Сибирь").to_numpy()
    drop_days = (year == 2025) & (month >= 7)
    lam[np.ix_(drop_days, siberia, np.ones(len(products), bool))] *= SIBERIA_DROP

    counts = rng.poisson(lam)
    d_idx, s_idx, p_idx = np.nonzero(counts)
    reps = counts[d_idx, s_idx, p_idx]
    d_idx, s_idx, p_idx = (np.repeat(a, reps) for a in (d_idx, s_idx, p_idx))

    base_price = products["base_price"].to_numpy()[p_idx]
    cheap = base_price < 5000
    quantity = 1 + rng.binomial(2, np.where(cheap, 0.35, 0.05))
    unit_price = np.round(base_price * np.where(year[d_idx] == 2025, 1.05, 1.0), 2)  # индексация цен 2025
    discount = np.where(promo_days[d_idx] & (cats[p_idx] == promo_cat), promo_disc, 0.0)
    revenue = np.round(quantity * unit_price * (1 - discount), 2)

    fact = pd.DataFrame({
        "order_date": days[d_idx].date, "store_id": stores["store_id"].to_numpy()[s_idx],
        "product_id": products["product_id"].to_numpy()[p_idx], "quantity": quantity,
        "unit_price": unit_price, "discount": discount, "revenue": revenue,
    }).sort_values(["order_date", "store_id", "product_id"], kind="stable")
    fact.insert(0, "order_id", np.arange(1, len(fact) + 1))
    return fact


def load(stores: pd.DataFrame, products: pd.DataFrame, fact: pd.DataFrame, dsn: str = DSN) -> None:
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE fact_sales, dim_product, dim_store")
        for table, df in [("dim_store", stores.drop(columns="traffic")), ("dim_product", products), ("fact_sales", fact)]:
            with cur.copy(f"COPY {table} ({', '.join(df.columns)}) FROM STDIN") as cp:
                for row in df.itertuples(index=False):
                    cp.write_row(row)
            log.info("%s: загружено %d строк", table, len(df))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stores, products = build_dimensions()
    fact = generate_sales(stores, products)
    log.info("Сгенерировано заказов: %d, выручка: %.0f руб.", len(fact), fact["revenue"].sum())
    load(stores, products, fact)


if __name__ == "__main__":
    main()
