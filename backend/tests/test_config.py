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
