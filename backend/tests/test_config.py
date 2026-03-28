from pathlib import Path

from app.core.config import ExecutionMode, Settings, StripeConnectMode


def test_settings_default_to_paper_mode() -> None:
    settings = Settings(_env_file=None, database_url="sqlite+pysqlite:///:memory:")

    assert settings.execution_mode == ExecutionMode.PAPER
    assert settings.enable_live_trading is False
    assert settings.stripe_connect_mode == StripeConnectMode.AUTO
    assert settings.default_symbols == ["SAP.DE", "MC.PA", "AIR.PA"]
    assert settings.market_region_label == "Europe"
    assert settings.market_status_exchange == "EU"
    assert settings.eodhd_base_url == "https://eodhd.com/api"


def test_live_mode_requires_explicit_flag() -> None:
    try:
        Settings(
            _env_file=None,
            database_url="sqlite+pysqlite:///:memory:",
            execution_mode=ExecutionMode.LIVE,
            enable_live_trading=False,
        )
    except ValueError as exc:
        assert "enable_live_trading=true" in str(exc)
    else:
        raise AssertionError("Expected live-mode validation to fail")


def test_settings_use_backend_local_env_file() -> None:
    assert Settings.model_config.get("env_file") == ".env"


def test_docker_compose_backend_loads_backend_env_file() -> None:
    compose_path = Path(__file__).resolve().parents[2] / "docker-compose.yml"
    compose_text = compose_path.read_text(encoding="utf-8")

    assert "backend:" in compose_text
    assert "env_file:" in compose_text
    assert "- backend/.env" in compose_text


def test_render_backend_dockerfile_uses_dynamic_port() -> None:
    dockerfile_path = Path(__file__).resolve().parents[2] / "infra" / "backend.Dockerfile"
    dockerfile_text = dockerfile_path.read_text(encoding="utf-8")

    assert "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}" in dockerfile_text


def test_root_dockerfile_exists_for_render_default_deploys() -> None:
    dockerfile_path = Path(__file__).resolve().parents[2] / "Dockerfile"
    dockerfile_text = dockerfile_path.read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in dockerfile_text
    assert "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}" in dockerfile_text


def test_render_blueprint_wires_backend_service_and_database() -> None:
    render_path = Path(__file__).resolve().parents[2] / "render.yaml"
    render_text = render_path.read_text(encoding="utf-8")

    assert "name: alphaview-backend" in render_text
    assert "runtime: docker" in render_text
    assert "- Dockerfile" in render_text
    assert "dockerfilePath: ./infra/backend.Dockerfile" in render_text
    assert "healthCheckPath: /api/v1/health" in render_text
    assert "property: connectionString" in render_text
    assert "EMAIL_DELIVERY_MODE" in render_text
    assert "value: log" in render_text
    assert "name: alphaview-db" in render_text
    assert "plan: free" in render_text
