FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY model.pkl model_meta.json app.py ./

# сервис не должен работать от root
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health')"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
