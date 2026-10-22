import os, sys
sys.path.insert(0, os.path.abspath("../Labs"))
sys.path.insert(0, os.path.abspath(""))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from report_common import Report
from content import *

# ---------------- архитектурная схема ----------------
cols = [
    ("1. Источники", "#dbe7f5", ["POS-кассы", "WMS / ERP\n(остатки)", "API погоды", "CRM и рекламные\nкабинеты", "Справочники,\nExcel/CSV"]),
    ("2. Интеграция", "#e3f1de", ["Debezium (CDC)", "Apache Kafka 3.8\n(потоки событий)", "Airbyte\n(API, файлы)", "Apache Airflow\n(оркестрация)"]),
    ("3. Хранение (Delta)", "#fdf0d5", ["Bronze\nсырые данные", "Silver\nочищенные, «звезда»", "Gold\nвитрины для BI и ML", "S3 (Yandex Object\nStorage)"]),
    ("4. Обработка", "#f3e1f0", ["Spark 3.5 — пакетная\n(Bronze→Silver)", "Spark Structured\nStreaming (продажи)", "dbt (Silver→Gold)"]),
    ("5. Аналитика и ML","#fde1d8", ["ClickHouse\n(быстрые витрины)", "Yandex DataLens\n(BI, self-service)", "ML: прогноз спроса,\nоптимизация цен", "MLflow\n(реестр моделей)"]),
    ("6. Визуализация и\nинтерфейсы", "#e2e2e2", ["Дашборды\nменеджеров", "Self-service\nаналитика", "REST API → ERP\n(FastAPI)", "Оповещения\n(Telegram, почта)"]),
]
fig, ax = plt.subplots(figsize=(17, 8.6))
ax.set_xlim(0, 17); ax.set_ylim(0, 8.6); ax.axis("off")
cw, gap, x0 = 2.45, 0.32, 0.2
tops = []
for i, (title, color, items) in enumerate(cols):
    x = x0 + i * (cw + gap)
    ax.add_patch(FancyBboxPatch((x, 1.55), cw, 6.35, boxstyle="round,pad=0.02,rounding_size=0.1", fc=color, ec="#555", lw=1.2))
    ax.text(x + cw / 2, 7.4, title, ha="center", va="center", fontsize=11, fontweight="bold")
    n = len(items); h = 0.9; space = (5.2 - n * h) / (n + 1)
    for k, t in enumerate(items):
        y = 6.9 - space * (k + 1) - h * (k + 1)
        ax.add_patch(FancyBboxPatch((x + 0.15, y), cw - 0.3, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc="white", ec="#777", lw=0.9))
        ax.text(x + cw / 2, y + h / 2, t, ha="center", va="center", fontsize=9.5)
    if i < len(cols) - 1:
        ax.add_patch(FancyArrowPatch((x + cw + 0.01, 4.7), (x + cw + gap - 0.01, 4.7), arrowstyle="-|>", mutation_scale=18, lw=2, color="#333"))
ax.add_patch(FancyBboxPatch((0.2, 0.2), 16.6, 1.0, boxstyle="round,pad=0.02,rounding_size=0.1", fc="#f5f5dc", ec="#555", lw=1.2))
ax.text(8.5, 0.92, "Сквозные компоненты: безопасность и 152-ФЗ (Keycloak, Vault, шифрование, псевдонимизация) • качество данных (Great Expectations)", ha="center", fontsize=10.5, fontweight="bold")
ax.text(8.5, 0.5, "мониторинг (Prometheus, Grafana) • каталог данных и метрик • CI/CD (Git) • резервное копирование", ha="center", fontsize=10.5, fontweight="bold")
ax.text(8.5, 8.3, "Архитектура ИАС ритейл-аналитики: потоки данных слева направо", ha="center", fontsize=14, fontweight="bold")
os.makedirs("screenshots", exist_ok=True)
fig.savefig("architecture.png", dpi=130, bbox_inches="tight", facecolor="white")
print("diagram ok")

# ---------------- отчёт ----------------
R = Report()
R.title_page(8, "Комплексный архитектурный проект ИАС для сквозного кейса. Кейс В: ритейл-аналитика")
R.p("применить полученные знания для проектирования архитектуры информационно-аналитической системы под бизнес-кейс с обоснованием выбора каждого компонента.", "Цель работы: ")
R.p(f"{CASE}. Работа групповая (Айсин А.Х., Асянов Р.И., Вахапов А.А.). Проект является проектным решением на бумаге: система не разворачивалась, "
    "цифры нагрузки — расчётные допущения. Ряд решений опирается на опыт лабораторных работ 3–7 (ClickHouse, Kafka, Delta Lake).", "Формат: ")

R.h("1 Описание кейса и требований")
R.p("Ритейл-сеть хочет прогнозировать спрос, оптимизировать цены и анализировать покупательское поведение. Исходные данные: продажи (POS), складские остатки, "
    "погода и маркетинговые кампании. Требования из кейса: прогноз на неделю вперёд, дашборды для менеджеров, возможность self-service аналитики.")
R.p(ASSUME)
R.h("1.1 Какие данные нужны")
R.table([["Источник", "Тип данных", "Объём", "Скорость поступления"]] + SOURCES, widths=[4.6, 4.4, 3.2, 3.2])
R.h("1.2 Пользователи и их вопросы")
R.table([["Роль", "Ключевые вопросы"]] + ROLES, widths=[5, 10.4])
R.h("1.3 Требования к производительности")
for t in REQ_PERF: R.item("• " + t)
R.h("1.4 Безопасность и регуляторные требования")
for t in REQ_SEC: R.item("• " + t)

R.h("2 Архитектурная схема")
R.p("Схема построена программно (matplotlib), файл — architecture.png; исходник в формате draw.io не создавался. На рисунке 1 показаны шесть слоёв и направление потоков данных; "
    "ниже — описание каждого слоя.")
R.image("architecture.png", "архитектура ИАС ритейл-аналитики", 15.5)
for name, text in LAYERS:
    R.p(text, f"{name}. ")

R.h("3 Спецификация технологического стека")
R.p("Версии указаны как целевые для проекта, актуальность на момент внедрения нужно перепроверить. Основа — open source (бюджет), облачные сервисы — российские (импортозамещение). "
    "Состав выбран так, чтобы опираться на технологии, уже освоенные командой в предыдущих работах (Spark/Delta, Kafka, ClickHouse).")
R.table([["Слой", "Продукты и версии", "Обоснование"]] + STACK, widths=[3, 6.6, 5.8])

R.h("4 Обоснование ключевых решений")
for i, (t, d) in enumerate(DECISIONS, 1):
    R.p(d, f"4.{i} {t}. ")

R.h("5 Риски и меры по их снижению")
R.table([["Риск", "Проявление", "Меры по снижению"]] + RISKS, widths=[3, 4.2, 8.2])

R.h("6 Ожидаемые результаты")
for t in RESULTS: R.item("• " + t)

R.h("7 Ответы на контрольные вопросы")
for i, (q, a) in enumerate(QA, 1):
    R.p(a, f"{i}. {q} ")

R.h("8 Презентация")
R.p("Презентация из 7 слайдов (титульный; кейс и требования; архитектура; стек; ключевые решения; риски; заключение) — файл Презентация_ЛР8.pptx. "
    "Видеозапись защиты не выполнялась (требуется только по запросу преподавателя).")
R.save("../Лабораторная работа №8 - отчет.docx")
print("report ok")

# ---------------- презентация ----------------
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation(); prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
NAVY, GREY = RGBColor(0x1F, 0x3A, 0x5F), RGBColor(0x44, 0x44, 0x44)
blank = prs.slide_layouts[6]


def add_text(sl, text, x, y, w, h, size=18, bold=False, color=GREY, align=None):
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame; tf.word_wrap = True
    lines = text if isinstance(text, list) else [text]
    for i, l in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = l; p.font.size = Pt(size); p.font.bold = bold; p.font.color.rgb = color; p.font.name = "Calibri"; p.space_after = Pt(6)
        if align: p.alignment = align
    return tb


def slide(title):
    sl = prs.slides.add_slide(blank)
    bar = sl.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(1.0)); bar.fill.solid(); bar.fill.fore_color.rgb = NAVY; bar.line.fill.background()
    add_text(sl, title, 0.5, 0.15, 12.3, 0.7, 30, True, RGBColor(255, 255, 255))
    return sl


def table(sl, rows, x, y, w, colw, size=12):
    t = sl.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(0.4 * len(rows))).table
    for j, cw_ in enumerate(colw): t.columns[j].width = Inches(cw_)
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            c = t.cell(i, j); c.text = v
            for p in c.text_frame.paragraphs:
                p.font.size = Pt(size); p.font.bold = (i == 0); p.font.name = "Calibri"


# 1 титульный
sl = prs.slides.add_slide(blank)
bg = sl.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height); bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
add_text(sl, "Комплексный архитектурный проект ИАС", 0.8, 2.0, 11.7, 1, 40, True, RGBColor(255, 255, 255))
add_text(sl, CASE, 0.8, 3.1, 11.7, 0.8, 28, False, RGBColor(0xD0, 0xE0, 0xF5))
add_text(sl, ["Команда: " + ", ".join(TEAM), "Информационно-аналитические системы, УУНиТ, 2026 г."], 0.8, 5.2, 11.7, 1, 18, False, RGBColor(255, 255, 255))

# 2 кейс
sl = slide("Кейс и требования")
add_text(sl, ["Задачи: прогноз спроса на неделю, оптимизация цен, анализ поведения покупателей.",
              "Данные: продажи (POS), остатки, погода, маркетинг.",
              "Пользователи: категорийные менеджеры, директора магазинов, маркетологи, аналитики (self-service), инженеры.",
              "Производительность: пересчёт прогноза раз в сутки; дашборд до 3 с; свежесть продаж до 1 ч; 15 одновременных пользователей.",
              "Безопасность: 152-ФЗ — хранение в РФ, псевдонимизация клиентов, ролевой доступ.",
              ASSUME], 0.6, 1.3, 12.1, 5.6, 17)

# 3 архитектура
sl = slide("Архитектурная схема")
sl.shapes.add_picture("architecture.png", Inches(0.4), Inches(1.15), width=Inches(12.5))

# 4 стек
sl = slide("Технологический стек")
table(sl, [["Слой", "Продукты"]] + [[r[0], r[1]] for r in STACK], 0.5, 1.2, 12.3, [2.8, 9.5], 12)

# 5 решения
sl = slide("Ключевые решения")
add_text(sl, [f"{i}. {t}" for i, (t, d) in enumerate(DECISIONS[:3], 1)], 0.6, 1.3, 12.1, 1.8, 22, True, NAVY)
add_text(sl, [d for t, d in DECISIONS[:3]], 0.6, 3.0, 12.1, 4.2, 14)

# 6 риски
sl = slide("Риски и меры по их снижению")
table(sl, [["Риск", "Меры"]] + [[r[0], r[2].split(";")[0] + "; " + r[2].split(";")[1].strip()] for r in RISKS[:5]], 0.5, 1.2, 12.3, [2.8, 9.5], 12)

# 7 заключение
sl = slide("Заключение: ожидаемые результаты")
add_text(sl, ["• " + t for t in RESULTS], 0.6, 1.3, 12.1, 5.6, 18)

prs.save("../Презентация_ЛР8.pptx")
print("pptx ok")
