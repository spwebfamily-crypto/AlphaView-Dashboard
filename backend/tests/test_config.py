from app.core.config import ExecutionMode, Settings


def test_settings_default_to_paper_mode() -> None:
    settings = Settings(database_url="sqlite+pysqlite:///:memory:")

    assert settings.execution_mode == ExecutionMode.PAPER
    assert settings.enable_live_trading is False


def test_live_mode_requires_explicit_flag() -> None:
    try:
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            execution_mode=ExecutionMode.LIVE,
            enable_live_trading=False,
        )
    except ValueError as exc:
        assert "enable_live_trading=true" in str(exc)
    else:
        raise AssertionError("Expected live-mode validation to fail")
