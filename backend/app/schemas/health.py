from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    execution_mode: str
    live_trading_enabled: bool
    database: str

