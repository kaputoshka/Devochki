"""Генерация sales_data.csv (синтетические продажи) для лабораторной работы №7."""
import numpy as np, pandas as pd

rng = np.random.default_rng(42)
N = 2_000_000
cats = {"Электроника": 5, "Одежда": 4, "Продукты": 6, "Дом и сад": 3, "Спорт": 2}
cat_names = list(cats)
category = rng.choice(cat_names, N, p=np.array(list(cats.values())) / sum(cats.values()))
qty = rng.integers(1, 10, N)
price = np.round(rng.uniform(50, 5000, N), 2)
df = pd.DataFrame({
    "transaction_id": np.arange(1, N + 1),
    "sale_date": (pd.Timestamp("2026-01-01") + pd.to_timedelta(rng.integers(0, 90, N), unit="D")).strftime("%Y-%m-%d"),
    "store_id": rng.integers(1, 51, N),
    "product_id": rng.integers(1, 2001, N),
    "category": category,
    "quantity": qty,
    "sales_amount": np.round(qty * price, 2),
})
df.to_csv("sales_data.csv", index=False)
print(df.head(), len(df))
