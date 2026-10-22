"""Снимает скриншоты дашборда в разных состояниях (headless Chromium через Playwright)."""
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "screenshots"
URL = (HERE / "dashboard.html").as_uri()


def apply(page: Page, js: str) -> None:
    page.evaluate(js)
    page.wait_for_timeout(700)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL, wait_until="networkidle")
        page.wait_for_function("document.querySelector('#c-map .geo') !== null")
        page.wait_for_timeout(1500)

        page.screenshot(path=OUT / "dash_full.png", full_page=True)
        page.locator(".grid > .card").nth(4).screenshot(path=OUT / "dash_story.png")

        # всплывающая подсказка на графике динамики (ноябрь 2025)
        page.evaluate("Plotly.Fx.hover('c-trend', [{curveNumber: 1, pointNumber: 10}])")
        page.wait_for_timeout(500)
        page.locator("#c-trend").screenshot(path=OUT / "dash_tooltip.png")
        page.evaluate("Plotly.Fx.unhover('c-trend')")

        # drill-down: 2025 → Q4
        apply(page, "dashboard.set({year: '2025'})")
        page.locator("#c-drill").locator("xpath=..").screenshot(path=OUT / "drill_quarter.png")
        apply(page, "dashboard.set({q: 4})")
        page.locator("#c-drill").locator("xpath=..").screenshot(path=OUT / "drill_month.png")
        apply(page, "dashboard.set({year: null, q: null})")

        # cross-filter: клик по категории «Электроника»
        page.evaluate("""() => {
            const gd = document.getElementById('c-cat');
            const i = gd.data[0].y.indexOf('Электроника');
            gd.emit('plotly_click', {points: [{y: gd.data[0].y[i], pointNumber: i}]});
        }""")
        page.wait_for_timeout(800)
        page.screenshot(path=OUT / "dash_electronics.png", full_page=True)

        # фильтр по региону «Сибирь» (через выпадающий список) + период 2025 г.
        apply(page, "dashboard.set({cat: null})")
        page.select_option("#f-region", "Сибирь")
        page.select_option("#f-from", "12")
        page.wait_for_timeout(800)
        page.screenshot(path=OUT / "dash_siberia.png", full_page=True)
        browser.close()
    if errors:
        raise RuntimeError(f"Ошибки JavaScript на странице: {errors}")


if __name__ == "__main__":
    main()
