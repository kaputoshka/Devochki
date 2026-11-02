"""Лабораторная работа №7: Delta Lake на PySpark (создание, MERGE, Time Travel, схема, сравнение с Parquet)."""
import os, shutil, time, json
from datetime import date
D = date.fromisoformat
os.environ.setdefault("HADOOP_HOME", r"C:\hadoop")
os.environ["PATH"] = r"C:\hadoop\bin;" + os.environ["PATH"]
os.environ["PYSPARK_PYTHON"] = os.environ["PYSPARK_DRIVER_PYTHON"] = __import__("sys").executable

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from delta import configure_spark_with_delta_pip, DeltaTable

BASE = os.path.abspath("warehouse").replace("\\", "/")
DELTA, PARQ = f"{BASE}/delta/sales_table", f"{BASE}/parquet/sales_table"
shutil.rmtree("warehouse", ignore_errors=True)

builder = (SparkSession.builder.appName("DeltaLake").master("local[*]")
           .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
           .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
           .config("spark.driver.memory", "4g").config("spark.sql.shuffle.partitions", "8")
           .config("spark.ui.showConsoleProgress", "false"))
spark = configure_spark_with_delta_pip(builder).getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
sec = lambda t: print(f"\n===== {t} =====", flush=True)
timings = {}

# ---- Шаг 2. Создание Delta-таблицы ----
sec("Шаг 2. Создание Delta-таблицы")
print("Spark", spark.version)
df = spark.read.csv("sales_data.csv", header=True, inferSchema=True)
df.printSchema()
print("Строк в CSV:", df.count())
t = time.time()
df.write.format("delta").save(DELTA)
print(f"Запись Delta: {time.time()-t:.1f} с")
df.write.format("parquet").save(PARQ)
pf = sorted(f for f in os.listdir(DELTA) if f.endswith(".parquet"))
print(f"Файлов данных (parquet): {len(pf)}, например: {pf[0][:40]}...")
print("Журнал _delta_log:", [f for f in sorted(os.listdir(DELTA + "/_delta_log")) if f.endswith(".json")])
spark.read.format("delta").load(DELTA).groupBy("category").agg(
    F.count("*").alias("cnt"), F.round(F.sum("sales_amount"), 2).alias("revenue")).orderBy("category").show()

# ---- Шаг 3.1. UPSERT (MERGE) ----
sec("Шаг 3.1. UPSERT (MERGE)")
dt = DeltaTable.forPath(spark, DELTA)
probe = [1, 2, 3]
print("До MERGE (id 1,2,3 и будущие новые 2000001..2000003):")
spark.read.format("delta").load(DELTA).filter(F.col("transaction_id").isin(probe + [2000001, 2000002, 2000003])) \
    .select("transaction_id", "category", "quantity", "sales_amount").orderBy("transaction_id").show()
mk = lambda rows: spark.sql("SELECT * FROM VALUES " + ", ".join(
    f"({i}, DATE'{d}', {st}, {p}, '{c}', {q}, {a})" for i, d, st, p, c, q, a in rows)
    + " AS t(transaction_id, sale_date, store_id, product_id, category, quantity, sales_amount)"
).select(*[F.col(f.name).cast(f.dataType) for f in df.schema.fields])
upd = mk([(1, "2026-01-25", 35, 1, "Электроника", 10, 99999.0),
          (2, "2026-03-19", 47, 2, "Одежда", 20, 88888.0),
          (3, "2026-01-07", 47, 3, "Дом и сад", 30, 77777.0)])
new = mk([(2000001, "2026-04-01", 5, 10, "Спорт", 2, 1500.0),
          (2000002, "2026-04-01", 6, 11, "Продукты", 4, 800.0),
          (2000003, "2026-04-02", 7, 12, "Электроника", 1, 25000.0)])
source_df = upd.unionByName(new)
print("Источник MERGE: 3 изменённые записи + 3 новые")
t = time.time()
(dt.alias("target").merge(source_df.alias("source"), "target.transaction_id = source.transaction_id")
   .whenMatchedUpdate(set={"sales_amount": "source.sales_amount", "quantity": "source.quantity"})
   .whenNotMatchedInsertAll().execute())
print(f"MERGE выполнен за {time.time()-t:.1f} с")
print("После MERGE:")
spark.read.format("delta").load(DELTA).filter(F.col("transaction_id").isin(probe + [2000001, 2000002, 2000003])) \
    .select("transaction_id", "category", "quantity", "sales_amount").orderBy("transaction_id").show()
print("Всего строк:", spark.read.format("delta").load(DELTA).count())

# ---- Ещё одна версия: DELETE (для демонстрации журнала) ----
sec("Доп. операция: DELETE")
dt.delete("transaction_id = 2000003")
print("Удалена запись 2000003. Строк:", spark.read.format("delta").load(DELTA).count())

# ---- Шаг 3.3. Управление схемой ----
sec("Шаг 3.3. Эволюция схемы (mergeSchema)")
extra = new.withColumn("transaction_id", F.col("transaction_id") + 10).withColumn("discount", F.lit(0.15))
extra.write.format("delta").mode("append").option("mergeSchema", "true").save(DELTA)
cur = spark.read.format("delta").load(DELTA)
cur.printSchema()
cur.filter(F.col("transaction_id").isin(1, 2000011, 2000012, 2000013)).orderBy("transaction_id").show()
print("Строк с discount IS NULL (старые записи):", cur.filter("discount IS NULL").count())

# ---- История + Шаг 3.2. Time Travel ----
sec("История транзакций таблицы (DESCRIBE HISTORY)")
hist = dt.history().select("version", "timestamp", "operation", "operationMetrics")
dt.history().select("version", "operation", F.col("operationParameters").cast("string").alias("params")).orderBy("version").show(truncate=60)
sec("Шаг 3.2. Time Travel")
for v in range(0, dt.history().count()):
    d = spark.read.format("delta").option("versionAsOf", v).load(DELTA)
    r = d.filter("transaction_id = 1").select("sales_amount").first()
    print(f"versionAsOf={v}: строк={d.count()}, sales_amount(id=1)={r[0] if r else None}, столбцов={len(d.columns)}")
ts = dt.history().filter("version = 1").select("timestamp").first()[0]
print("\ntimestampAsOf =", ts)
d = spark.read.format("delta").option("timestampAsOf", str(ts)).load(DELTA)
print("timestampAsOf: строк =", d.count(), ", sales_amount(id=1) =", d.filter("transaction_id=1").first()["sales_amount"])
print("\nОткат (RESTORE) к версии 0:")
dt.restore(0) if hasattr(dt, "restore") else dt.restoreToVersion(0)
print("Строк после RESTORE:", spark.read.format("delta").load(DELTA).count(), "| столбцов:", len(spark.read.format("delta").load(DELTA).columns))

# ---- Шаг 5. Сравнение производительности ----
sec("Шаг 5. Delta Lake vs Parquet")
# для честного сравнения пересоздаём Delta из тех же данных и делаем OPTIMIZE (compaction + Z-ORDER)
shutil.rmtree(f"{BASE}/delta", ignore_errors=True)
df.write.format("delta").partitionBy().save(DELTA)
queries = {
    "Q1: count(*)": lambda d: d.count(),
    "Q2: SUM по категориям": lambda d: d.groupBy("category").agg(F.sum("sales_amount")).collect(),
    "Q3: фильтр store_id=7 AND дата>=2026-03-01": lambda d: d.filter("store_id = 7 AND sale_date >= '2026-03-01'").agg(F.sum("sales_amount")).collect(),
    "Q4: топ-10 товаров по выручке": lambda d: d.groupBy("product_id").agg(F.sum("sales_amount").alias("s")).orderBy(F.desc("s")).limit(10).collect(),
    "Q5: точечный поиск transaction_id=1500000": lambda d: d.filter("transaction_id = 1500000").collect(),
}
def bench(path, fmt, q, runs=3):
    d = spark.read.format(fmt).load(path)
    q(d)  # прогрев
    res = []
    for _ in range(runs):
        t = time.time(); q(d); res.append(time.time() - t)
    return sum(res) / runs
size = lambda p: sum(os.path.getsize(os.path.join(a, f)) for a, _, fs in os.walk(p) for f in fs if f.endswith(".parquet") and not f.startswith(".")) / 1e6
rows = []
for name, q in queries.items():
    p, dl = bench(PARQ, "parquet", q), bench(DELTA, "delta", q)
    rows.append((name, p, dl)); print(f"{name:55s} parquet={p:6.2f} с   delta={dl:6.2f} с")
sizes = (size(PARQ), size(DELTA))
spark.sql(f"OPTIMIZE delta.`{DELTA}` ZORDER BY (transaction_id)").show(truncate=40)
rows2 = []
for name in ["Q3: фильтр store_id=7 AND дата>=2026-03-01", "Q5: точечный поиск transaction_id=1500000"]:
    dl2 = bench(DELTA, "delta", queries[name]); rows2.append((name, dl2)); print(f"{name:55s} delta после OPTIMIZE ZORDER={dl2:6.2f} с")
print(f"\nРазмер данных (активные .parquet, до OPTIMIZE): parquet={sizes[0]:.1f} МБ, delta={sizes[1]:.1f} МБ")
json.dump({"rows": rows, "optimized": rows2, "parquet_mb": sizes[0], "delta_mb": sizes[1]}, open("bench.json", "w", encoding="utf-8"), ensure_ascii=False)
spark.stop()
