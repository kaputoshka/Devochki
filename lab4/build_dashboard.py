"""Выгружает агрегаты из PostgreSQL и собирает дашборд dashboard.html (+ stats.json для отчёта)."""
import json
import logging
import os
from pathlib import Path

import psycopg

log = logging.getLogger("build_dashboard")

HERE = Path(__file__).resolve().parent
DSN = os.environ.get("PG_DSN", "postgresql://lab4:lab4@127.0.0.1:5434/retail")

Q_STORES = "SELECT store_id, city, region, lat, lon FROM dim_store ORDER BY store_id"
Q_PRODUCTS = "SELECT product_id, product_name, category FROM dim_product ORDER BY product_id"
Q_MONTHS = "SELECT DISTINCT to_char(order_date, 'YYYY-MM') FROM fact_sales ORDER BY 1"
# куб для дашборда: месяц × магазин × товар
Q_CUBE = """
SELECT to_char(order_date, 'YYYY-MM') AS ym, store_id, product_id,
       round(sum(revenue))::bigint AS revenue, sum(quantity)::int AS units, count(*)::int AS orders
FROM fact_sales GROUP BY 1, 2, 3 ORDER BY 1, 2, 3
"""
# куб по дням недели: месяц × магазин × категория × день недели (1 = пн)
Q_DOW = """
SELECT to_char(order_date, 'YYYY-MM') AS ym, store_id, category, extract(isodow FROM order_date)::int AS dow,
       round(sum(revenue))::bigint AS revenue, count(*)::int AS orders
FROM v_sales GROUP BY 1, 2, 3, 4 ORDER BY 1, 2, 3, 4
"""
# показатели для текста отчёта
Q_STATS = {
    "by_year": """SELECT extract(year FROM order_date)::int, round(sum(revenue))::bigint, count(*), sum(quantity)
                  FROM fact_sales GROUP BY 1 ORDER BY 1""",
    "by_region": """SELECT region,
                           round(sum(revenue) FILTER (WHERE order_date <  '2025-01-01'))::bigint,
                           round(sum(revenue) FILTER (WHERE order_date >= '2025-01-01'))::bigint,
                           round(sum(revenue) FILTER (WHERE order_date BETWEEN '2024-07-01' AND '2024-12-31'))::bigint,
                           round(sum(revenue) FILTER (WHERE order_date >= '2025-07-01'))::bigint
                    FROM v_sales GROUP BY 1 ORDER BY 1""",
    "by_category": """SELECT category, round(sum(revenue))::bigint,
                             round(100.0 * sum(revenue) / sum(sum(revenue)) OVER (), 1)
                      FROM v_sales GROUP BY 1 ORDER BY 2 DESC""",
    "nov_electronics": """SELECT extract(year FROM order_date)::int, round(sum(revenue))::bigint, count(*)
                          FROM v_sales WHERE category = 'Электроника' AND extract(month FROM order_date) = 11
                          GROUP BY 1 ORDER BY 1""",
    "by_month": """SELECT to_char(order_date, 'YYYY-MM'), round(sum(revenue))::bigint
                   FROM fact_sales GROUP BY 1 ORDER BY 2 DESC""",
    "by_dow": """SELECT extract(isodow FROM order_date)::int,
                        round(100.0 * sum(revenue) / sum(sum(revenue)) OVER (), 1)
                 FROM fact_sales GROUP BY 1 ORDER BY 1""",
    "rows": "SELECT count(*) FROM fact_sales",
}


def fetch(cur: psycopg.Cursor, sql: str) -> list[tuple]:
    cur.execute(sql)
    return cur.fetchall()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        stores = fetch(cur, Q_STORES)
        products = fetch(cur, Q_PRODUCTS)
        months = [r[0] for r in fetch(cur, Q_MONTHS)]
        cube = fetch(cur, Q_CUBE)
        dow = fetch(cur, Q_DOW)
        stats = {k: [[float(v) if hasattr(v, "is_finite") else v for v in row] for row in fetch(cur, q)]
                 for k, q in Q_STATS.items()}

    categories = list(dict.fromkeys(p[2] for p in products))
    mi, ci = {m: i for i, m in enumerate(months)}, {c: i for i, c in enumerate(categories)}
    data = {
        "months": months,
        "categories": categories,
        "stores": [[s[0], s[1], s[2], s[3], s[4]] for s in stores],
        "products": [[p[0], p[1], ci[p[2]]] for p in products],
        "cube": [[mi[r[0]], r[1], r[2], r[3], r[4], r[5]] for r in cube],
        # формат строк как у cube (месяц, магазин, ключ, выручка, шт., заказы) + день недели; шт. по дням не нужны
        "dow": [[mi[r[0]], r[1], ci[r[2]], r[4], 0, r[5], r[3]] for r in dow],
    }
    template = (HERE / "dashboard_template.html").read_text(encoding="utf-8")
    html = template.replace("/*__DATA__*/", "const DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";")
    (HERE / "dashboard.html").write_text(html, encoding="utf-8")
    (HERE / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("dashboard.html: %d строк куба, %d строк куба по дням недели", len(cube), len(dow))


if __name__ == "__main__":
    main()
