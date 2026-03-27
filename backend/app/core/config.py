from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutionMode(StrEnum):
    DEMO = "DEMO"
    PAPER = "PAPER"
    LIVE = "LIVE"


class Settings(BaseSettings):
    project_name: str = "AlphaView Dashboard"
    app_version: str = "0.1.0"
    app_env: str = "development"
    execution_mode: ExecutionMode = ExecutionMode.PAPER
    enable_live_trading: bool = False
    allow_public_registration: bool = True
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/alphaview"
    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    frontend_base_url: str = "http://localhost:5173"
    auth_secret_key: str = "change-me"
    auth_access_token_ttl_minutes: int = 15
    auth_refresh_token_ttl_days: int = 7
    auth_cookie_secure: bool = False
    polygon_api_key: str | None = None
    polygon_base_url: str = "https://api.massive.com"
    polygon_websocket_url: str = "wss://socket.massive.com/stocks"
    finnhub_api_key: str | None = None
    finnhub_secret_key: str | None = None
    finnhub_base_url: str = "https://finnhub.io/api/v1"
    ibkr_host: str | None = None
    ibkr_port: int = 7497
    sentiment_api_url: str = "https://api.alternative.me/fng/"
    ibkr_client_id: int = 101
    broker_adapter: str = "mock"
    default_symbols: list[str] = Field(default_factory=lambda: ["AAPL", "MSFT", "NVDA"])
    default_timeframe: str = "1min"
    artifact_root: str = "../reports"
    model_registry_dir: str = "../reports/model_runs"
    backtest_report_dir: str = "../reports/backtests"
    demo_seed_path: str = "../examples/sample_demo_seed.json"
    request_timeout_seconds: int = 30
    withdrawals_enabled: bool = False
    withdrawals_currency: str = "usd"
    stripe_publishable_key: str | None = None
    stripe_secret_key: str | None = None
    stripe_api_base: str = "https://api.stripe.com"
    stripe_api_version: str = "2026-02-25.clover"
    stripe_connect_api_version: str = "2026-01-28.clover"
    stripe_account_links_api_version: str = "2025-08-27.preview"
    stripe_connect_return_url: str | None = None
    stripe_connect_refresh_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        enable_decoding=False,
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("default_symbols", mode="before")
    @classmethod
    def split_default_symbols(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip().upper() for item in value.split(",") if item.strip()]
        return [item.upper() for item in value]

    @field_validator("enable_live_trading")
    @classmethod
    def block_live_by_default(cls, value: bool, info) -> bool:
        execution_mode = info.data.get("execution_mode", ExecutionMode.PAPER)
        if execution_mode == ExecutionMode.LIVE and not value:
            raise ValueError("LIVE execution mode requires enable_live_trading=true.")
        return value

    @field_validator("withdrawals_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.lower()

    @property
    def artifact_root_path(self) -> Path:
        return Path(self.artifact_root).resolve()

    @property
    def model_registry_path(self) -> Path:
        return Path(self.model_registry_dir).resolve()

    @property
    def backtest_report_path(self) -> Path:
        return Path(self.backtest_report_dir).resolve()

    @property
    def demo_seed_file(self) -> Path:
        return Path(self.demo_seed_path).resolve()

    @property
    def stripe_connect_return_url_resolved(self) -> str:
        return self.stripe_connect_return_url or f"{self.frontend_base_url.rstrip('/')}/?stripe=return"

    @property
    def stripe_connect_refresh_url_resolved(self) -> str:
        return self.stripe_connect_refresh_url or f"{self.frontend_base_url.rstrip('/')}/?stripe=refresh"


@lru_cache
def get_settings() -> Settings:
    return Settings()
