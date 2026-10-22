"""REST API прогноза оттока клиентов (FastAPI). Документация OpenAPI/Swagger: /docs."""
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

log = logging.getLogger("churn_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

HERE = Path(__file__).resolve().parent
MODEL_PATH = Path(os.environ.get("MODEL_PATH", HERE / "model.pkl"))
META_PATH = Path(os.environ.get("MODEL_META_PATH", HERE / "model_meta.json"))

YesNo = Literal["Yes", "No"]
InternetDependent = Literal["Yes", "No", "No internet service"]


class Customer(BaseModel):
    """Признаки клиента в формате исходного датасета Telco Customer Churn."""
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {
        "tenure": 2, "MonthlyCharges": 70.7, "TotalCharges": 151.65, "gender": "Female", "SeniorCitizen": "No",
        "Partner": "No", "Dependents": "No", "PhoneService": "Yes", "MultipleLines": "No",
        "InternetService": "Fiber optic", "OnlineSecurity": "No", "OnlineBackup": "No", "DeviceProtection": "No",
        "TechSupport": "No", "StreamingTV": "No", "StreamingMovies": "No", "Contract": "Month-to-month",
        "PaperlessBilling": "Yes", "PaymentMethod": "Electronic check"}})

    tenure: int = Field(ge=0, le=120, description="Срок обслуживания, мес.")
    MonthlyCharges: float = Field(ge=0, le=1000, description="Ежемесячный платёж")
    TotalCharges: float | None = Field(default=None, ge=0, description="Сумма платежей (может отсутствовать у новых клиентов)")
    gender: Literal["Male", "Female"]
    SeniorCitizen: YesNo
    Partner: YesNo
    Dependents: YesNo
    PhoneService: YesNo
    MultipleLines: Literal["Yes", "No", "No phone service"]
    InternetService: Literal["DSL", "Fiber optic", "No"]
    OnlineSecurity: InternetDependent
    OnlineBackup: InternetDependent
    DeviceProtection: InternetDependent
    TechSupport: InternetDependent
    StreamingTV: InternetDependent
    StreamingMovies: InternetDependent
    Contract: Literal["Month-to-month", "One year", "Two year"]
    PaperlessBilling: YesNo
    PaymentMethod: Literal["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"]


class Prediction(BaseModel):
    churn: int = Field(description="1 — клиент, вероятно, уйдёт")
    probability: float = Field(description="Вероятность оттока")
    model_version: str


class BatchRequest(BaseModel):
    customers: list[Customer] = Field(min_length=1, max_length=1000)


class BatchPrediction(BaseModel):
    predictions: list[Prediction]


state: dict = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    state["model"] = joblib.load(MODEL_PATH)
    state["meta"] = json.loads(META_PATH.read_text(encoding="utf-8"))
    log.info("Модель загружена: %s v%s", state["meta"]["model"], state["meta"]["version"])
    yield
    state.clear()


app = FastAPI(title="Churn Prediction API", version="1.0.0", lifespan=lifespan,
              description="Прогноз оттока клиентов телеком-оператора (ЛР5, MLOps).")


def _predict(customers: list[Customer]) -> list[Prediction]:
    meta = state["meta"]
    df = pd.DataFrame([c.model_dump() for c in customers])[meta["features"]]
    try:
        proba = state["model"].predict_proba(df)[:, 1]
    except ValueError as e:  # несовместимые данные — ошибка клиента, а не сервера
        log.warning("Ошибка предсказания: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    return [Prediction(churn=int(p >= meta["threshold"]), probability=round(float(p), 4), model_version=meta["version"])
            for p in proba]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_loaded": "model" in state}


@app.get("/model")
def model_info() -> dict:
    meta = state["meta"]
    return {k: meta[k] for k in ("model", "version", "trained_at", "sklearn", "threshold", "test")}


@app.post("/predict", response_model=Prediction)
def predict(customer: Customer) -> Prediction:
    result = _predict([customer])[0]
    log.info("predict: churn=%d p=%.4f", result.churn, result.probability)
    return result


@app.post("/predict/batch", response_model=BatchPrediction)
def predict_batch(req: BatchRequest) -> BatchPrediction:
    return BatchPrediction(predictions=_predict(req.customers))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
