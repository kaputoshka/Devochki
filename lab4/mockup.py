"""Рисует макет (wireframe) дашборда — шаг 2 лабораторной работы."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent / "screenshots" / "mockup.png"

# (x, y, ширина, высота, заголовок, тип визуализации) в условной сетке 12 × 20
BLOCKS = [
    (0, 18.6, 12, 1.0, "Фильтры: период с/по · регион · категория · «Сбросить»", "срезы (глобальные)"),
    (0, 16.4, 3, 1.8, "KPI: Выручка", "карточка + Δ г/г"), (3, 16.4, 3, 1.8, "KPI: Заказы", "карточка + Δ г/г"),
    (6, 16.4, 3, 1.8, "KPI: Средний чек", "карточка + Δ г/г"), (9, 16.4, 3, 1.8, "KPI: Продано, шт.", "карточка + Δ г/г"),
    (0, 14.4, 12, 1.6, "«Главное»: 4–5 автоматических выводов", "текстовый блок (storytelling)"),
    (0, 9.9, 8, 4.1, "Динамика выручки по месяцам, 2025 vs 2024", "линейный график, аннотации рекорда и роста"),
    (8, 9.9, 4, 4.1, "Год → квартал → месяц", "столбцы, drill-down по клику"),
    (0, 5.6, 4, 4.0, "Выручка по категориям", "горизонтальные столбцы, клик = фильтр"),
    (4, 5.6, 4, 4.0, "Регионы: изменение г/г", "расходящиеся столбцы (красный < 0)"),
    (8, 5.6, 4, 4.0, "Дни недели", "столбцы, пик выделен"),
    (0, 1.6, 6, 3.7, "Карта магазинов", "пузырьковая карта: размер = выручка, цвет = г/г"),
    (6, 1.6, 6, 3.7, "Детализация по товарам", "таблица: выручка, заказы, доля, г/г"),
    (0, 0.0, 12, 1.3, "«Выводы и рекомендации»", "текстовый блок"),
]
STEPS = [(15.4, "1 Обзор"), (12.0, "2 Тренд"), (5.0, "3 Детали"), (0.6, "4 Выводы")]


def main() -> None:
    fig, ax = plt.subplots(figsize=(12, 10.5), dpi=130)
    ax.set_xlim(-1.6, 12.1)
    ax.set_ylim(-0.2, 19.8)
    ax.axis("off")
    for x, y, w, h, title, kind in BLOCKS:
        ax.add_patch(FancyBboxPatch((x + 0.06, y + 0.06), w - 0.12, h - 0.12, boxstyle="round,pad=0.02,rounding_size=0.15",
                                    fc="#f8fafc", ec="#64748b", lw=1.2))
        ax.text(x + w / 2, y + h / 2 + 0.18, title, ha="center", va="center", fontsize=10, fontweight="bold", wrap=True)
        ax.text(x + w / 2, y + h / 2 - 0.32, kind, ha="center", va="center", fontsize=8.5, color="#475569", style="italic")
    for y, label in STEPS:
        ax.text(-0.25, y, label, ha="right", va="center", fontsize=10, color="#b45309", fontweight="bold", rotation=90)
    ax.annotate("", xy=(-1.2, 0.2), xytext=(-1.2, 17.8), arrowprops=dict(arrowstyle="->", color="#b45309", lw=1.5))
    ax.set_title("Макет дашборда «Продажи сети» (сценарий чтения: обзор → тренд → детали → выводы)", fontsize=12)
    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight")


if __name__ == "__main__":
    main()
