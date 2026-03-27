from fastapi.testclient import TestClient


def test_health_endpoint_returns_expected_payload(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "AlphaView Test"
    assert payload["execution_mode"] == "PAPER"
    assert payload["live_trading_enabled"] is False
    assert payload["database"] == "ok"

