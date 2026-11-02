from fastapi.testclient import TestClient

from app import Customer, app

VALID = Customer.model_config["json_schema_extra"]["example"]
LOYAL = {**VALID, "tenure": 70, "TotalCharges": 5000.0, "Contract": "Two year", "InternetService": "DSL",
         "MonthlyCharges": 60.0, "PaymentMethod": "Credit card (automatic)", "TechSupport": "Yes", "OnlineSecurity": "Yes"}


def client() -> TestClient:
    return TestClient(app)


def test_health() -> None:
    with client() as c:
        assert c.get("/health").json() == {"status": "ok", "model_loaded": True}


def test_predict_valid() -> None:
    with client() as c:
        r = c.post("/predict", json=VALID)
    assert r.status_code == 200
    body = r.json()
    assert body["churn"] in (0, 1) and 0 <= body["probability"] <= 1 and body["model_version"]


def test_risky_customer_scores_higher_than_loyal() -> None:
    with client() as c:
        risky = c.post("/predict", json=VALID).json()["probability"]
        loyal = c.post("/predict", json=LOYAL).json()["probability"]
    assert risky > 0.5 > loyal


def test_missing_total_charges_is_allowed() -> None:
    with client() as c:
        r = c.post("/predict", json={**VALID, "tenure": 0, "TotalCharges": None})
    assert r.status_code == 200


def test_invalid_category_rejected() -> None:
    with client() as c:
        r = c.post("/predict", json={**VALID, "Contract": "Lifetime"})
    assert r.status_code == 422


def test_negative_and_missing_fields_rejected() -> None:
    with client() as c:
        assert c.post("/predict", json={**VALID, "tenure": -1}).status_code == 422
        incomplete = {k: v for k, v in VALID.items() if k != "gender"}
        assert c.post("/predict", json=incomplete).status_code == 422
        assert c.post("/predict", json={**VALID, "extra": 1}).status_code == 422


def test_batch() -> None:
    with client() as c:
        r = c.post("/predict/batch", json={"customers": [VALID, LOYAL]})
        assert r.status_code == 200 and len(r.json()["predictions"]) == 2
        assert c.post("/predict/batch", json={"customers": []}).status_code == 422
