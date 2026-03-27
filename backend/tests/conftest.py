from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import ExecutionMode, Settings
from app.main import create_app


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    return Settings(
        project_name="AlphaView Test",
        app_version="test",
        app_env="test",
        execution_mode=ExecutionMode.PAPER,
        enable_live_trading=False,
        auth_secret_key="test-secret-key",
        database_url="sqlite+pysqlite:///:memory:",
        backend_cors_origins=["http://testserver"],
        artifact_root=str(tmp_path / "reports"),
        model_registry_dir=str(tmp_path / "reports" / "model_runs"),
        backtest_report_dir=str(tmp_path / "reports" / "backtests"),
        demo_seed_path=str(tmp_path / "demo_seed.json"),
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    with TestClient(create_app(test_settings)) as test_client:
        yield test_client


@pytest.fixture
def db_session(client: TestClient) -> Session:
    session = client.app.state.session_manager.session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def authenticated_client(client: TestClient) -> TestClient:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "trader@example.com",
            "password": "Password123!",
            "full_name": "Trader Test",
        },
    )
    assert response.status_code == 201
    return client
