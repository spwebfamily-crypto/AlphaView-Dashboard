from pydantic import BaseModel


class RuntimeSettingsResponse(BaseModel):
    project_name: str
    environment: str
    execution_mode: str
    live_trading_enabled: bool
    broker_adapter: str
    market_region_label: str
    market_status_exchange: str
    default_symbols: list[str]
    default_timeframe: str
    available_market_data_sources: list[str]
    market_status_provider: str | None = None
