import os, subprocess, sys
sys.path.insert(0, os.path.abspath("../Labs"))
from report_common import Report, term_image

S = "screenshots"
os.makedirs(S, exist_ok=True)
env = dict(os.environ, MSYS_NO_PATHCONV="1")
sh = lambda cmd: subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", env=env).stdout.strip()
cut = lambda ls, n=150: "\n".join(l if len(l) <= n else l[:n - 3] + "..." for l in ls)

# ---- «скриншоты» вывода терминала (реальный вывод) ----
ps = sh('docker ps --filter name=lab6-kafka --format "{{.Names}}  {{.Image}}  {{.Status}}  {{.Ports}}"')
tp = sh("docker exec lab6-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic user_events")
term_image("$ docker compose up -d\n$ docker ps\n" + ps + "\n\n$ kafka-topics.sh --describe --topic user_events\n" + tp,
           f"{S}/kafka.png", "Kafka (KRaft) и топик user_events", width_chars=120, font_size=16)

pl = open("producer.log", encoding="utf-8").read().strip().split("\n")
term_image(cut(pl[:6] + ["..."] + pl[-4:], 140), f"{S}/producer.png", "python producer.py", font_size=15)
cl = open("consumer.log", encoding="utf-8").read().strip().split("\n")
term_image(cut(cl[:5] + ["..."] + cl[-3:], 175).replace("{'window_start'", "\n    {'window_start'"),
           f"{S}/consumer.png", "python consumer.py (окно 5 с)", font_size=14)

q1 = sh('docker exec lab3-clickhouse clickhouse-client -q "SELECT window_start, window_end, total_clicks, total_views, total_purchases, total_revenue '
        'FROM analytics.stream_aggregates ORDER BY window_start LIMIT 6" --format PrettyCompact')
q2 = sh('docker exec lab3-clickhouse clickhouse-client -q "SELECT count() AS windows, sum(total_clicks) AS clicks, sum(total_views) AS views, '
        'sum(total_purchases) AS purchases, sum(total_revenue) AS revenue FROM analytics.stream_aggregates" --format PrettyCompact')
term_image("SELECT * FROM analytics.stream_aggregates ORDER BY window_start LIMIT 6;\n" + q1 +
           "\n\nSELECT count(), sum(total_clicks), sum(total_views), sum(total_purchases), sum(total_revenue) ...;\n" + q2,
           f"{S}/clickhouse.png", "ClickHouse: содержимое stream_aggregates", font_size=15)
stats = sh('docker exec lab3-clickhouse clickhouse-client -q "SELECT count(), sum(total_clicks)+sum(total_views)+sum(total_purchases), '
           'round(sum(total_revenue),2) FROM analytics.stream_aggregates" --format TSV').split("\t")
print("stats", stats)

# ---- документ ----
R = Report()
R.title_page(6, "Анализ потоковых данных в реальном времени")
R.p("получить практические навыки построения конвейера обработки потоковых данных с оконными агрегациями и визуализацией в реальном времени.", "Цель работы: ")
R.p("Задачи работы:")
for t in ["1) развернуть брокер сообщений Apache Kafka и создать топик событий;",
          "2) разработать продюсера, имитирующего поток пользовательских событий;",
          "3) разработать консьюмера с оконной агрегацией (tumbling window) и записью результатов в ClickHouse;",
          "4) создать таблицу агрегатов в ClickHouse;",
          "5) построить автообновляемый дашборд: события по типам, динамика выручки, интенсивность потока."]:
    R.item(t)

R.h("1 Архитектура конвейера")
R.p("Источник событий (producer.py) → брокер Apache Kafka (топик user_events) → консьюмер с оконной агрегацией (consumer.py) → "
    "таблица analytics.stream_aggregates в ClickHouse → веб-дашборд (dashboard.py), читающий ClickHouse и обновляющийся каждые 3 секунды. "
    "ClickHouse использован тот же, что в лабораторной работе №3 (контейнер lab3-clickhouse, база analytics).")

R.h("2 Установка и настройка Kafka (шаг 1)")
R.p("Kafka запущена в Docker-контейнере (образ apache/kafka:3.8.0) в режиме KRaft: начиная с версии 3.3 брокер может выполнять роль контроллера сам, "
    "без отдельного ZooKeeper, поэтому отдельный процесс ZooKeeper из методички не нужен. Конфигурация — docker-compose.yml (приложение А). "
    "Адрес брокера указан как 127.0.0.1:9092 (а не localhost): на Windows localhost может разрешаться в IPv6 (::1), что приводило к таймауту подключения клиента. "
    "Топик user_events создан с одной партицией (рисунок 1).")
R.code(open("docker-compose.yml", encoding="utf-8").read())
R.image(f"{S}/kafka.png", "брокер Kafka и топик user_events", 15.5)

R.h("3 Продюсер (шаг 2)")
R.p("Продюсер генерирует события трёх типов — click, view, purchase (с весами 5:10:1, как в реальном потоке, где покупок меньше, чем просмотров), "
    "со случайными user_id, product_id и суммой, и отправляет их в формате JSON с интервалом 0,1–0,5 с. Параметр DURATION_SECONDS ограничивает время работы "
    "(для демонстрации — 150 с, поток из 499 событий).")
R.code(open("producer.py", encoding="utf-8").read())
R.image(f"{S}/producer.png", "работа продюсера (начало и конец журнала)", 15.5)

R.h("4 Таблица ClickHouse (шаг 4)")
R.code(open("01_create_table.sql", encoding="utf-8").read())
R.p("Таблица создана в базе analytics, движок MergeTree, сортировка по window_start (запросы дашборда читают последние окна по времени).")

R.h("5 Консьюмер с оконной агрегацией (шаг 3)")
R.p("Консьюмер читает топик в группе lab6-aggregator и реализует tumbling window — непересекающиеся окна фиксированной длины. Для демонстрации "
    "длина окна 5 секунд (параметр WINDOW_SECONDS; в реальной системе — 300 с = 5 минут). Время события берётся из поля timestamp (event time), "
    "а не из часов консьюмера. Когда приходит событие, выходящее за границу окна, накопленные агрегаты (число кликов, просмотров, покупок и выручка по покупкам) "
    "записываются в ClickHouse, а окно начинается заново с этого события. Запись выполняет функция save_to_clickhouse() через HTTP-интерфейс ClickHouse "
    "(INSERT ... FORMAT JSONEachRow).")
R.code(open("consumer.py", encoding="utf-8").read())
R.p("Особенность реализации по методичке: окно закрывается только при поступлении следующего события, поэтому последнее незавершённое окно при остановке "
    "потока не сохраняется, а при паузе в потоке запись задерживается. Для production используют watermark и таймер закрытия окон (см. ответ на вопрос 2).")
R.image(f"{S}/consumer.png", "работа консьюмера: сохранение оконных агрегатов", 15.5)
R.p(f"За время демонстрационного запуска продюсер отправил 499 событий; в ClickHouse сохранено окон: {stats[0]}, суммарно событий в окнах: {stats[1]}, "
    f"выручка по покупкам: {stats[2]} (рисунок 5). Часть событий (последнее незакрытое окно и события до подключения консьюмера) в агрегаты не попала — "
    "это следствие описанного выше поведения.")
R.image(f"{S}/clickhouse.png", "данные в таблице analytics.stream_aggregates", 15.5)

R.h("6 Визуализация (шаг 5)")
R.p("В лабораторной работе №4 BI-макет проектировался под Power BI/DataLens, которые на машине недоступны, поэтому для потоковой визуализации создан "
    "собственный веб-дашборд (FastAPI + Chart.js): сервер dashboard.py выполняет SQL-запросы к ClickHouse (эндпоинт /api/data), страница обновляется "
    "автоматически каждые 3 секунды и по кнопке «Обновить». Запуск: uvicorn dashboard:app --port 8050, адрес http://localhost:8050. Дашборд показывает (рисунок 6):")
for t in ["1) KPI: число окон агрегации, суммарные клики, просмотры, покупки и выручка;",
          "2) столбчатая диаграмма с накоплением — количество событий по типам в последних 30 окнах;",
          "3) линейный график динамики выручки по окнам;",
          "4) график интенсивности потока — число событий в секунду в каждом окне (сумма событий окна, делённая на его длительность). "
          "В демонстрации интенсивность держится около 3–4 событий/с, что соответствует средней паузе продюсера 0,3 с."]:
    R.item(t)
R.image(f"{S}/dashboard.png", "дашборд потоковых данных", 15.5)
R.p("Колебания выручки между окнами объясняются малой долей покупок в потоке (около 6 % событий): в окне их 0–3 штуки, поэтому график «пилообразный».")

R.h("7 Ответы на контрольные вопросы")
R.p("1) В чём отличие потоковой обработки от пакетной?")
R.p("Пакетная обработка работает с ограниченным набором накопленных данных, запускается по расписанию и даёт результат с задержкой (минуты — часы), "
    "но проста и эффективна для больших объёмов. Потоковая обрабатывает неограниченный поток событий по мере поступления, задержка — миллисекунды–секунды, "
    "результаты инкрементально обновляются; она сложнее из-за состояния, порядка событий, опозданий и отказоустойчивости (семантика exactly-once).")
R.p("2) Что такое watermark в потоковых системах и зачем он нужен?")
R.p("Watermark — отметка прогресса event time: утверждение системы, что события с временем меньше этой отметки уже (почти) все получены. "
    "Он нужен, чтобы решить, когда окно можно закрыть и выдать результат, несмотря на опаздывающие и неупорядоченные события: обычно watermark = максимальное увиденное время события "
    "минус допустимая задержка. События позже watermark отбрасываются или обрабатываются отдельно (allowed lateness). В нашем консьюмере watermark нет — окно закрывается по первому событию за границей.")
R.p("3) Чем tumbling window отличается от sliding window?")
R.p("Tumbling-окна имеют фиксированную длину и не пересекаются: каждое событие попадает ровно в одно окно (как в лабораторной — 5-секундные окна подряд). "
    "Sliding (hopping) окна имеют длину и шаг сдвига меньше длины, поэтому перекрываются, и событие входит в несколько окон — это даёт сглаженные скользящие метрики "
    "(например, «за последние 5 минут, обновление каждую минуту»), но требует больше вычислений. Есть ещё session window — окно по периоду активности пользователя.")
R.p("4) Какие ещё брокеры сообщений, кроме Kafka, вы знаете?")
R.p("RabbitMQ (AMQP, гибкая маршрутизация), Apache Pulsar (многоарендность, раздельное хранение и обслуживание), NATS / NATS JetStream, Redis Streams, "
    "ActiveMQ, Amazon Kinesis, Google Pub/Sub, Azure Event Hubs, Yandex Data Streams / Managed Service for Kafka (облачные аналоги).")

R.h("Выводы")
R.p("Построен работающий конвейер потоковой обработки: продюсер → Kafka → консьюмер с tumbling-окнами → ClickHouse → автообновляемый дашборд. "
    "Конвейер обработал поток из 499 событий в режиме реального времени с интенсивностью 3–4 события/с. Практические наблюдения: Kafka в режиме KRaft "
    "запускается без ZooKeeper; на Windows адрес брокера лучше задавать через 127.0.0.1; простая реализация окон по методичке требует доработки "
    "(watermark и таймер закрытия окон) для устойчивой работы при паузах и опоздавших событиях.")
R.h("Приложения")
R.p("Приложение А — docker-compose.yml, 01_create_table.sql, producer.py, consumer.py, dashboard.py, requirements.txt; "
    "Приложение Б — producer.log, consumer.log (журналы запуска). Все файлы — в папке «Лаба_6».")
R.save("../Лабораторная работа №6 - отчет.docx")
print("saved")
