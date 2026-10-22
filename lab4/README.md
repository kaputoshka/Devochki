# ЛР4. Дашборд со storytelling

PostgreSQL (Docker) → SQL-агрегаты → интерактивный HTML-дашборд на Plotly.js → отчёт `.docx`.
Выполнили: Картавенко И.С., Сабирова П.Д., Исламова Э.И.

Инструкция рассчитана на компьютер, где ещё ничего не установлено. Команды даны для **Windows (PowerShell)** и **macOS / Linux (Terminal)**.

## 1. Установить программы (один раз)

Нужны **Python 3.12** и **Docker Desktop**. Python 3.13+ не берите: под новые версии могут ещё не выйти готовые сборки numpy/pandas.

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

После установки **запустите Docker Desktop** и дождитесь статуса «Engine running». Проверка (в новом окне терминала):

```bash
python --version        # Windows: Python 3.12.x  (на macOS/Linux: python3.12 --version)
docker --version
docker compose version
```

## 2. Подготовить окружение Python

Все команды выполняются из папки `lab4`. Рядом с ней должны лежать `report_common.py` и папка `reports` — они нужны только для сборки отчёта.

**Windows:**

```powershell
cd путь\к\DevochkiLabs\lab4
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # один раз, если PowerShell не даёт запустить Activate.ps1
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium                 # браузер для автоскриншотов (~150 МБ)
```

**macOS / Linux:**

```bash
cd путь/к/DevochkiLabs/lab4
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
```

Дальше все команды одинаковы для всех систем (в активированном окружении `.venv`).

## 3. Запустить базу данных

```bash
docker compose up -d                                        # PostgreSQL 16 на 127.0.0.1:5434, база retail
docker exec lab4-postgres pg_isready -U lab4 -d retail      # повторять, пока не ответит "accepting connections"
```

Таблицы создаются автоматически из `01_schema.sql` при первом запуске контейнера.

## 4. Загрузить данные и собрать дашборд

```bash
python gen_data.py           # генерирует ~240 тыс. заказов (seed = 42) и загружает их в PostgreSQL
python build_dashboard.py    # SQL-запросы → dashboard.html и stats.json
```

Открыть дашборд в браузере:

```bash
start dashboard.html         # Windows
open dashboard.html          # macOS
xdg-open dashboard.html      # Linux
```

Нужен интернет: библиотека Plotly.js и подложка карты загружаются с CDN.

## 5. (Необязательно) Макет, скриншоты, отчёт

```bash
python mockup.py             # screenshots/mockup.png
python screenshots.py        # скриншоты дашборда в разных состояниях (headless Chromium)
python build_report.py       # ../reports/Лабораторная работа №4 - отчет.docx
```

- Перед `build_report.py` **закройте отчёт в Word**, иначе файл не перезапишется.
- `gen_data.log` уже лежит в папке и попадает в отчёт как рисунок. Данные детерминированы, так что перезаписывать его не обязательно. На macOS / Linux журнал можно обновить так: `python gen_data.py 2>&1 | tee gen_data.log`.

## 6. Остановить

```bash
docker compose down          # останавливает и удаляет контейнер; данные пропадут, их снова загрузит gen_data.py
deactivate                   # выйти из окружения Python
```

## Если что-то не работает

| Симптом | Что сделать |
|---|---|
| `docker: command not found` / `Cannot connect to the Docker daemon` | Запустить Docker Desktop и дождаться «Engine running» |
| `port is already allocated` (5434) | Порт занят другим PostgreSQL: в `docker-compose.yml` заменить `5434` на свободный порт и задать `PG_DSN=postgresql://lab4:lab4@127.0.0.1:<порт>/retail` |
| `connection refused` в `gen_data.py` | База ещё стартует: повторить `pg_isready` из шага 3 |
| Пустая карта на дашборде | Нет доступа к `cdn.plot.ly` (подложка карты) |
| `PermissionError` при сборке отчёта | Закрыть `.docx` в Word |

Пароль базы по умолчанию `lab4` (локальный учебный контейнер). Другой пароль задаётся переменной `PG_PASSWORD` перед `docker compose up` и через `PG_DSN` для скриптов.
