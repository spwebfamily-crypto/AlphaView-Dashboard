from __future__ import annotations

import socket

from app.core.config import Settings


class IbkrStatusProbe:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def check_connection(self) -> tuple[bool, str]:
        if not self.settings.ibkr_host:
            return False, "IBKR host not configured; local simulation continues over real market data."
        try:
            with socket.create_connection((self.settings.ibkr_host, self.settings.ibkr_port), timeout=2):
                return True, "IBKR host reachable, but broker routing is not enabled in this build."
        except OSError as exc:
            return False, f"IBKR host unreachable: {exc}"
