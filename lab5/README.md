# ЛР5. MLOps: от обучения модели до REST API

Telco Customer Churn → три модели с 5-fold кросс-валидацией (`train.ipynb`) → `model.pkl` → REST API на FastAPI → Docker-контейнер.
Выполнили: Картавенко И.С., Сабирова П.Д., Исламова Э.И.

Инструкция рассчитана на компьютер, где ещё ничего не установлено. Команды даны для **Windows (PowerShell)** и **macOS / Linux (Terminal)**.

## 1. Установить программы (один раз)

Нужны **Python 3.12** и **Docker Desktop**. Версия Python важна: модель обучена на Python 3.12 и scikit-learn 1.9.1, образ Docker тоже собирается на 3.12.

**Windows** (PowerShell от имени администратора):

```powershell
wsl --install                                  # подсистема Linux для Docker; после неё перезагрузить компьютер
winget install -e --id Python.Python.3.12
winget install -e --id Docker.DockerDesktop
```

Если `winget` нет, скачайте установщики с https://www.python.org/downloads/ (отметьте галочку **Add python.exe to PATH**) и https://www.docker.com/products/docker-desktop/.

**macOS** (через [Homebrew](https://brew.sh)):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"   # если Homebrew ещё нет
brew install python@3.12
brew install --cask docker
```

**Linux (Ubuntu/Debian):** `sudo apt install python3.12 python3.12-venv`, Docker — по инструкции https://docs.docker.com/engine/install/.

После установки **запустите Docker Desktop** и дождитесь статуса «Engine running». Проверка:

```bash
python --version        # Windows: Python 3.12.x  (на macOS/Linux: python3.12 --version)
docker --version
```

## 2. Подготовить окружение Python

Все команды выполняются из папки `lab5`.

**Windows:**

```powershell
cd путь\к\DevochkiLabs\lab5
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # один раз, если PowerShell не даёт запустить Activate.ps1
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

**macOS / Linux:**

```bash
cd путь/к/DevochkiLabs/lab5
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

Дальше команды одинаковы для всех систем (в активированном окружении `.venv`), если не указано иное.

## 3. Обучить модель (шаги 1–3)

Датасет уже лежит в `data/Telco-Customer-Churn.csv`, готовая модель — в `model.pkl`. Переобучать необязательно. Чтобы пройти шаги заново:

```bash
jupyter notebook train.ipynb                                           # интерактивно: Run → Run All Cells
# или без браузера:
jupyter nbconvert --to notebook --execute --inplace train.ipynb
```

Ноутбук перезапишет `model.pkl`, `model_meta.json` и `screenshots/roc.png`.

Если датасета нет, скачайте его:

```bash
curl -L -o data/Telco-Customer-Churn.csv https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv
```

На Windows вместо `curl` используйте `curl.exe`.

## 4. Проверить API автотестами

```bash
python -m pytest -v tests
```

Ожидается `7 passed`. Запускайте именно через `python -m pytest` из папки `lab5`: так тесты находят `app.py`.

## 5. Собрать и запустить Docker-контейнер (шаги 6–7)

```bash
docker build -t ml-service .
docker run -d --name ml-service -p 5000:5000 ml-service
```

**macOS:** порт 5000 занят системной службой AirPlay Receiver, и `localhost:5000` отвечает `403`. Запускайте контейнер на порту 5001 и во всех адресах ниже пишите `5001` вместо `5000`:

```bash
docker run -d --name ml-service -p 5001:5000 ml-service
```

Документация Swagger: http://localhost:5000/docs. Там можно открыть `POST /predict` → **Try it out** → **Execute**.

Тестовые запросы, **macOS / Linux:**

```bash
curl http://localhost:5000/health
curl http://localhost:5000/model
curl -X POST http://localhost:5000/predict -H "Content-Type: application/json" -d @sample_request.json
```

Тестовые запросы, **Windows (PowerShell):** в PowerShell `curl` — это другая команда, поэтому используйте `curl.exe` или `Invoke-RestMethod`:

```powershell
curl.exe http://localhost:5000/health
curl.exe -X POST http://localhost:5000/predict -H "Content-Type: application/json" -d "@sample_request.json"
# или
Invoke-RestMethod -Uri http://localhost:5000/predict -Method Post -ContentType "application/json" -InFile sample_request.json
```

Ожидаемый ответ: `{"churn":1,"probability":0.6436,"model_version":"..."}`.

Журнал контейнера: `docker logs ml-service`.

**Без Docker** (для отладки): `uvicorn app:app --port 5000`.

## 6. (Необязательно) Скриншоты и отчёт

```bash
python -m playwright install chromium     # один раз, браузер для скриншотов (~150 МБ)
python screenshots.py                     # Swagger UI; контейнер из шага 5 должен быть запущен
python build_report.py                    # ../reports/Лабораторная работа №5 - отчет.docx
```

- Для `build_report.py` рядом с папкой `lab5` должны лежать `report_common.py` и папка `reports`.
- Перед запуском **закройте отчёт в Word**.
- Журналы `docker_build.log`, `run.log`, `requests.log`, `container.log`, `pytest.log` уже лежат в папке и попадают в отчёт как рисунки.

## 7. Остановить

```bash
docker rm -f ml-service
deactivate
```

## Если что-то не работает

| Симптом | Что сделать |
|---|---|
| `Cannot connect to the Docker daemon` | Запустить Docker Desktop и дождаться «Engine running» |
| `port is already allocated` (5000) или ответ `403` на macOS | Порт 5000 на macOS занимает AirPlay Receiver: запустить с `-p 5001:5000` и обращаться к `http://localhost:5001` (для `screenshots.py` поменять `URL` в начале файла) |
| `ModuleNotFoundError: No module named 'app'` в тестах | Запускать `python -m pytest tests` из папки `lab5` |
| `InconsistentVersionWarning` / ошибка загрузки `model.pkl` | Версия scikit-learn отличается от 1.9.1: переустановить `pip install -r requirements.txt` или переобучить модель (шаг 3) |
| Пустая страница `/docs` | Swagger UI загружается с CDN: нужен интернет |
| `PermissionError` при сборке отчёта | Закрыть `.docx` в Word |
