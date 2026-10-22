"""Скриншоты Swagger UI запущенного сервиса (контейнер ml-service на localhost:5000)."""
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "screenshots"
URL = "http://127.0.0.1:5000/docs"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=1.5)
        page.goto(URL, wait_until="networkidle")
        page.wait_for_selector(".opblock")
        page.screenshot(path=OUT / "swagger.png")

        # POST /predict → Try it out → Execute (тело запроса — пример из схемы Pydantic)
        block = page.locator(".opblock-post").filter(has_text="/predict").first
        block.locator(".opblock-summary").click()
        block.get_by_role("button", name="Try it out").click()
        block.get_by_role("button", name="Execute").click()
        block.locator(".live-responses-table .response-col_status").first.wait_for()
        page.wait_for_timeout(500)
        # от начала блока ответов до конца фактического ответа сервера (без примеров схем)
        top = block.locator(".responses-wrapper").bounding_box()
        live = block.locator(".live-responses-table").first.bounding_box()
        page.screenshot(path=OUT / "swagger_predict.png", full_page=True,
                        clip={"x": top["x"], "y": top["y"], "width": top["width"], "height": live["y"] + live["height"] - top["y"]})
        browser.close()


if __name__ == "__main__":
    main()
