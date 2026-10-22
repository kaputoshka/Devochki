"""Подготовка данных Telco Customer Churn и кандидаты моделей (используется ноутбуком train.ipynb)."""
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 42
TARGET = "Churn"
NUMERIC = ["tenure", "MonthlyCharges", "TotalCharges"]
CATEGORICAL = [
    "gender", "SeniorCitizen", "Partner", "Dependents", "PhoneService", "MultipleLines", "InternetService",
    "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies",
    "Contract", "PaperlessBilling", "PaymentMethod",
]
FEATURES = NUMERIC + CATEGORICAL


def load_data(path: Path) -> tuple[pd.DataFrame, pd.Series]:
    """Читает CSV, приводит типы; возвращает признаки X и целевую переменную y (1 — отток)."""
    df = pd.read_csv(path)
    # у новых клиентов (tenure = 0) TotalCharges — пробел; превращаем в NaN, дальше заполнит импьютер
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"].str.strip(), errors="coerce")
    df["SeniorCitizen"] = df["SeniorCitizen"].map({0: "No", 1: "Yes"})
    y = (df[TARGET] == "Yes").astype(int)
    return df[FEATURES], y


def make_preprocessor() -> ColumnTransformer:
    numeric = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    categorical = OneHotEncoder(handle_unknown="ignore")
    return ColumnTransformer([("num", numeric, NUMERIC), ("cat", categorical, CATEGORICAL)])


def make_candidates() -> dict[str, Pipeline]:
    """Три модели из задания; предобработка входит в пайплайн и сохраняется вместе с моделью."""
    models = {
        "LogisticRegression": LogisticRegression(max_iter=1000, C=1.0),
        "RandomForest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, random_state=SEED, n_jobs=-1),
        "GradientBoosting": GradientBoostingClassifier(n_estimators=200, learning_rate=0.05, max_depth=3, random_state=SEED),
    }
    return {name: Pipeline([("prep", make_preprocessor()), ("model", m)]) for name, m in models.items()}
