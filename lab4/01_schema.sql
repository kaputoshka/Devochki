-- Аналитическая база розничной сети: схема «звезда» (факт продаж + справочники)
CREATE TABLE IF NOT EXISTS dim_store (
    store_id  SMALLINT PRIMARY KEY,
    city      TEXT NOT NULL,
    region    TEXT NOT NULL,
    lat       REAL NOT NULL,
    lon       REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_id   SMALLINT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category     TEXT NOT NULL,
    base_price   NUMERIC(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_sales (
    order_id    INTEGER PRIMARY KEY,
    order_date  DATE NOT NULL,
    store_id    SMALLINT NOT NULL REFERENCES dim_store (store_id),
    product_id  SMALLINT NOT NULL REFERENCES dim_product (product_id),
    quantity    SMALLINT NOT NULL CHECK (quantity > 0),
    unit_price  NUMERIC(10, 2) NOT NULL,
    discount    NUMERIC(4, 2) NOT NULL DEFAULT 0,
    revenue     NUMERIC(12, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_fact_sales_date ON fact_sales (order_date);

-- Витрина для BI: факт, обогащённый атрибутами справочников
CREATE OR REPLACE VIEW v_sales AS
SELECT f.order_id, f.order_date, f.quantity, f.unit_price, f.discount, f.revenue,
       s.store_id, s.city, s.region, p.product_id, p.product_name, p.category
FROM fact_sales f
JOIN dim_store s USING (store_id)
JOIN dim_product p USING (product_id);
