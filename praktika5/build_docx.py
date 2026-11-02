#!/usr/bin/env python3
"""Build practical work 5 from the supplied Word template and EDA JSON data."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = Path(__file__).resolve().parent
TEMPLATE = ROOT / "Отчет_ПЗ2_Экспертная_система.docx"
RESULTS = WORK_DIR / "analysis_results.json"
OUTPUT = WORK_DIR / "Отчет_ПЗ5_Разведочный_анализ_данных_исправленный.docx"
FIGURES = WORK_DIR / "figures"

VARIABLES = (
    ("Longitude", "долгота района", "градусы"),
    ("Latitude", "широта района", "градусы"),
    ("HouseAge", "медианный возраст домов в районе", "лет"),
    ("AveRooms", "среднее число комнат в домохозяйстве", "комнат"),
    ("AveBedrms", "среднее число спален в домохозяйстве", "спален"),
    ("Population", "население района", "человек"),
    ("AveOccup", "среднее число жителей в домохозяйстве", "человек"),
    ("MedInc", "медианный доход домохозяйства", "10 тыс. USD"),
    ("MedHouseVal", "медианная стоимость дома", "100 тыс. USD"),
)


def fmt(value: Any, digits: int = 3) -> str:
    """Format supplied numeric results using a Russian decimal separator."""
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
        return str(int(value))
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}".replace(".", ",")
    return str(value)


def add_text(doc: Document, text: str) -> None:
    """Add a body paragraph by inheriting the template's Normal style."""
    paragraph = doc.add_paragraph(style="Normal")
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.first_line_indent = Cm(1.25)
    paragraph.add_run(text)


def add_heading(doc: Document, text: str) -> None:
    """Use the template's existing Heading 1 style, without overriding it."""
    doc.add_paragraph(text, style="Heading 1")


def add_caption(doc: Document, text: str) -> None:
    """Use the template caption style exactly once for an object."""
    paragraph = doc.add_paragraph(text, style="Caption")
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = False


def set_cell_text(cell: Any, value: str, *, bold: bool) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(value)
    run.bold = bold
    # Use the template Normal font rather than an independently selected typeface.
    run.style = "Default Paragraph Font"
    run.font.size = Pt(10)
    paragraph.paragraph_format.keep_with_next = True


def add_table(
    doc: Document,
    headers: Sequence[str],
    rows: Iterable[Sequence[str]],
) -> None:
    """Add a Word table, retaining Word's table grid and table dimensions."""
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Normal Table"
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = OxmlElement("w:" + edge)
        for key, value in {"val": "single", "sz": "4", "color": "808080"}.items():
            border.set(qn("w:" + key), value)
        borders.append(border)
    table._tbl.tblPr.append(borders)
    table.autofit = True
    for cell, value in zip(table.rows[0].cells, headers):
        set_cell_text(cell, value, bold=True)
    for values in rows:
        row = table.add_row()
        for cell, value in zip(row.cells, values):
            set_cell_text(cell, value, bold=False)
    header_properties = table.rows[0]._tr.get_or_add_trPr()
    header_properties.append(OxmlElement("w:tblHeader"))
    for row in table.rows:
        properties = row._tr.get_or_add_trPr()
        properties.append(OxmlElement("w:cantSplit"))


def add_figure(doc: Document, name: str, caption: str) -> None:
    """Add an existing PNG inline with its one corresponding caption."""
    path = FIGURES / name
    if not path.is_file():
        raise FileNotFoundError(path)
    paragraph = doc.add_paragraph(style="Normal")
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    paragraph.add_run().add_picture(str(path), width=Cm(15.5))
    add_caption(doc, caption)


def update_title_and_clear_body(doc: Document) -> None:
    """Preserve title-page XML and section properties; replace only old body XML."""
    title_end = None
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text == "по практической работе №2":
            paragraph.runs[0].text = "по практической работе №5"
            for run in paragraph.runs[1:]:
                run.text = ""
        elif text == "Построение системы правил для экспертной системы":
            paragraph.runs[0].text = "Разведочный анализ данных (EDA) на Python"
            for run in paragraph.runs[1:]:
                run.text = ""
        elif text == "Уфа 2026":
            title_end = paragraph
    if title_end is None:
        raise RuntimeError("В шаблоне не найден конец титульного листа («Уфа 2026»).")

    body = doc._element.body
    remove = False
    for child in list(body):
        if child is title_end._p:
            remove = True
            continue
        if remove and child.tag != qn("w:sectPr"):
            body.remove(child)


def stat_rows(data: dict[str, Any], keys: Sequence[str]) -> list[tuple[str, ...]]:
    stats = data["stats"]
    return [
        (name, *(fmt(stats[name][key]) for key in keys))
        for name, _, _ in VARIABLES
    ]


def anomaly_rows(data: dict[str, Any]) -> list[tuple[str, ...]]:
    return [
        (
            fmt(item["index"]),
            fmt(item["AveRooms"]),
            fmt(item["AveOccup"]),
            fmt(item["Latitude"]),
            fmt(item["Longitude"]),
            fmt(item["MedHouseVal"]),
        )
        for item in data["anomalies"]
    ]


def transformation_rows(data: dict[str, Any]) -> list[tuple[str, ...]]:
    return [
        (
            str(item["name"]),
            fmt(item["min"]),
            fmt(item["max"]),
            fmt(item["mean"]),
            fmt(item["std"]),
            fmt(item["skewness"]),
        )
        for item in data["transformations"]
    ]


def build(data: dict[str, Any]) -> Document:
    """Build a corrected report using current JSON fields and existing PNG charts."""
    doc = Document(TEMPLATE)
    update_title_and_clear_body(doc)

    dataset = data["dataset"]
    correlations = data["correlations"]
    iqr = data["ave_rooms_iqr"]
    z_score = data["ave_rooms_z"]
    winsorization = data["winsorization"]

    add_text(
        doc,
        "Цель работы: освоить приёмы разведочного анализа данных в Python на "
        "наборе California Housing: описать состав данных, оценить распределения "
        "и пропуски, изучить связи признаков, выявить аномальные наблюдения и "
        "сравнить способы их обработки.",
    )
    add_heading(doc, "Ход работы")
    add_heading(doc, "1. Исходные данные и подготовка")
    add_text(
        doc,
        f"Для анализа использован набор California Housing из scikit-learn. Он "
        f"содержит {fmt(dataset['rows'])} наблюдений и {fmt(dataset['columns'])} "
        "числовых переменных. Единица наблюдения — район (block group).",
    )
    add_table(doc, ("Переменная", "Смысл", "Единица измерения"), VARIABLES)
    add_caption(doc, "Таблица 1. Переменные набора California Housing")
    add_text(
        doc,
        f"Проверка качества данных показала {fmt(dataset['missing_values'])} "
        "пропусков. Поэтому статистики и корреляции рассчитаны по всем строкам "
        "без исключения наблюдений из-за отсутствующих значений.",
    )

    add_heading(doc, "2. Описательная статистика и распределения")
    add_text(doc, "Стандартное отклонение рассчитано с ddof=1. Квартили используют линейную интерполяцию pandas, асимметрия и эксцесс — поправки на объём выборки pandas.skew и pandas.kurt. На гистограммах используется логарифмическая шкала частот, а на части ящиков с усами — логарифмическая шкала значений, указанная на оси; исходные наблюдения сохраняются.")
    add_table(
        doc,
        ("Признак", "Среднее", "Медиана", "s", "min / max"),
        [
            (name, mean, median, std, f"{minimum} / {maximum}")
            for name, mean, median, std, minimum, maximum in stat_rows(
                data, ("mean", "median", "std_sample", "min", "max")
            )
        ],
    )
    add_caption(doc, "Таблица 2. Центральные характеристики и диапазон признаков")
    add_table(
        doc,
        ("Признак", "Q1", "Q3", "Асимметрия", "Эксцесс"),
        stat_rows(data, ("q1", "q3", "skewness", "excess_kurtosis")),
    )
    add_caption(doc, "Таблица 3. Квартильные характеристики формы распределений")
    add_text(
        doc,
        "Среднее и медиана заметно расходятся у Population, AveOccup, AveRooms "
        "и AveBedrms; это согласуется с их правосторонней асимметрией. Для "
        "AveRooms и AveBedrms особенно велики коэффициенты асимметрии и эксцесса, "
        "что указывает на редкие, но очень большие значения. HouseAge — медианный "
        "возраст домов в районе, а не возраст отдельного дома; его максимум 52 "
        "отражает верхнее ограничение исходного набора.",
    )
    add_figure(doc, "01_distributions.png", "Рисунок 1. Распределения числовых признаков")
    add_figure(doc, "02_boxplots.png", "Рисунок 2. Ящики с усами для признаков")
    add_figure(doc, "03_qq_medhouseval.png", "Рисунок 3. Q–Q-график MedHouseVal")
    add_text(
        doc,
        "На Q–Q-графике MedHouseVal точки в центральной части ближе к опорной "
        "прямой, а в хвостах отклоняются от неё. Следовательно, нормальное "
        "распределение не является точной моделью целевой переменной; заметно "
        "также накопление значений у верхней границы 5,00001.",
    )

    add_heading(doc, "3. Корреляционный и пространственный анализ")
    lat_lon = correlations["Latitude"]["Longitude"]
    income_target = correlations["MedInc"]["MedHouseVal"]
    rooms_bedrooms = correlations["AveRooms"]["AveBedrms"]
    add_text(
        doc,
        f"Наиболее сильная линейная связь между координатами: r(Latitude, "
        f"Longitude) = {fmt(lat_lon, 4)}. Для MedHouseVal наиболее заметна "
        f"положительная связь с MedInc: r = {fmt(income_target, 4)}. Также "
        f"AveRooms и AveBedrms сильно коррелируют (r = {fmt(rooms_bedrooms, 4)}), "
        "поэтому при дальнейшем моделировании эти признаки следует проверять на "
        "избыточность.",
    )
    add_figure(doc, "04_correlation_heatmap.png", "Рисунок 4. Матрица коэффициентов корреляции Пирсона")
    add_figure(doc, "05_pairplot.png", "Рисунок 5. Парные зависимости ключевых признаков")
    add_figure(doc, "06_medinc_price.png", "Рисунок 6. Связь MedInc и MedHouseVal")
    add_figure(doc, "08_spatial.png", "Рисунок 7. Пространственное распределение MedHouseVal")
    add_text(
        doc,
        "Пространственная визуализация носит разведочный характер. Связь цены "
        "жилья с координатами может отражать расположение относительно побережья, "
        "городов и локальных рынков, а также нелинейные эффекты. Она не доказывает "
        "причинного влияния широты или долготы на стоимость жилья.",
    )

    add_heading(doc, "4. Аномальные значения и преобразования")
    add_text(
        doc,
        f"Для AveRooms методом межквартильного размаха получены границы "
        f"[{fmt(iqr['lower'])}; {fmt(iqr['upper'])}] и выявлено "
        f"{fmt(iqr['count'])} наблюдений за их пределами. По правилу |z| > "
        f"{fmt(z_score['threshold'])} выявлено {fmt(z_score['count'])} "
        "наблюдений. Это не обязательно ошибки: экстремальные отношения числа "
        "комнат к числу домохозяйств требуют проверки контекста, а не "
        "автоматического удаления.",
    )
    add_table(
        doc,
        ("Индекс", "AveRooms", "AveOccup", "Latitude", "Longitude", "MedHouseVal"),
        anomaly_rows(data),
    )
    add_caption(doc, "Таблица 4. Наблюдения, отмеченные как аномальные")
    add_text(
        doc,
        f"Для AveRooms выполнена винсоризация SciPy по 1 % наблюдений с каждого края. Использованы порядковые пороги, а не интерполированные процентили: "
        f"[{fmt(winsorization['lower_1pct'])}; {fmt(winsorization['upper_99pct'])}]. "
        f"Изменено значений: {fmt(winsorization['changed_count'])}. Также для "
        "AveRooms рассмотрено преобразование log1p. Winsorization ограничивает "
        "влияние хвостов, сохраняя число строк; log1p сжимает правый хвост. "
        "Выбор метода должен определяться целью дальнейшего анализа.",
    )
    add_table(
        doc,
        ("Преобразование", "min", "max", "Среднее", "s", "Асимметрия"),
        transformation_rows(data),
    )
    add_caption(doc, "Таблица 5. Сравнение исходного и преобразованных AveRooms")
    add_figure(doc, "07_ave_rooms_treatment.png", "Рисунок 8. Сравнение исходного AveRooms и обработки выбросов")

    add_heading(doc, "Вывод")
    add_text(
        doc,
        f"В практической работе выполнен EDA набора California Housing "
        f"({fmt(dataset['rows'])} строк, {fmt(dataset['columns'])} признаков). "
        f"Пропуски не обнаружены. Распределения AveRooms, AveBedrms, Population "
        "и AveOccup имеют тяжёлые правые хвосты, поэтому средние значения следует "
        "интерпретировать совместно с медианами и квартилями. Выявлены аномальные "
        "наблюдения AveRooms; для их анализа сопоставлены IQR, z-оценка, "
        "winsorization и log1p-преобразование. Наиболее выраженная связь с "
        "MedHouseVal наблюдается у MedInc, а сильная отрицательная корреляция "
        "Latitude–Longitude описывает пространственную конфигурацию выборки, но "
        "не причинный эффект.",
    )
    add_heading(doc, "Приложение. Воспроизводимость")
    add_text(doc, "Выполненный код, выводы ячеек и встроенные графики находятся в файле Отчет_ПЗ5_Разведочный_анализ_данных.ipynb. HTML экспортирован из выполненного ноутбука. Полные таблицы сохранены в descriptive_statistics.csv и outliers_ave_rooms.csv; результаты — в analysis_results.json. Пакеты и их версии указаны в requirements.txt. Все исходные столбцы сохранены без замены преобразованными значениями.")
    return doc


def main() -> None:
    with RESULTS.open(encoding="utf-8") as source:
        data = json.load(source)
    build(data).save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
