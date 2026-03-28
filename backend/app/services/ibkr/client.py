from __future__ import annotations

import socket
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from itertools import count
from typing import Any

from app.core.config import Settings

try:
    from ibapi.client import EClient
    from ibapi.common import BarData
    from ibapi.contract import Contract, ContractDescription, ContractDetails
    from ibapi.ticktype import TickTypeEnum
    from ibapi.wrapper import EWrapper

    IBAPI_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when the package is missing.
    EClient = object  # type: ignore[assignment]
    EWrapper = object  # type: ignore[assignment]
    BarData = Any  # type: ignore[assignment]
    Contract = Any  # type: ignore[assignment]
    ContractDescription = Any  # type: ignore[assignment]
    ContractDetails = Any  # type: ignore[assignment]
    TickTypeEnum = None  # type: ignore[assignment]
    IBAPI_AVAILABLE = False


_NON_FATAL_ERROR_CODES = {
    2104,  # Market data farm connection is OK
    2106,  # HMDS data farm connection is OK
    2107,  # HMDS data farm connection inactive
    2108,  # Market data farm connection inactive
    2158,  # Sec-def data farm connection is OK
}
_LAST_TICK_TYPES = {4, 68}
_CLOSE_TICK_TYPES = {9, 75}
_BID_TICK_TYPES = {1, 66}
_ASK_TICK_TYPES = {2, 67}
_DEFAULT_TIMEOUT_SECONDS = 4
_PRIMARY_EXCHANGE_BY_SUFFIX: dict[str, tuple[str, ...]] = {
    "DE": ("IBIS", "FWB"),
    "PA": ("SBF",),
    "AS": ("AEB",),
    "MI": ("BVME",),
    "BR": ("ENEXT.BE",),
    "LS": ("LSE",),
}
_SUFFIX_BY_PRIMARY_EXCHANGE: dict[str, str] = {
    "IBIS": "DE",
    "FWB": "DE",
    "SBF": "PA",
    "AEB": "AS",
    "BVME": "MI",
    "ENEXT.BE": "BR",
    "LSE": "LS",
}
_DISPLAY_EXCHANGE_BY_PRIMARY: dict[str, str] = {
    "IBIS": "XETR",
    "FWB": "XFRA",
    "SBF": "XPAR",
    "AEB": "XAMS",
    "BVME": "XMIL",
    "ENEXT.BE": "XBRU",
    "LSE": "XLON",
}


def _split_ticker(ticker: str) -> tuple[str, str | None]:
    normalized = ticker.strip().upper()
    if "." not in normalized:
        return normalized, None
    root, suffix = normalized.rsplit(".", 1)
    return root, suffix or None


def infer_ibkr_currency(ticker: str) -> str:
    _, suffix = _split_ticker(ticker)
    if suffix in _PRIMARY_EXCHANGE_BY_SUFFIX:
        return "EUR" if suffix != "LS" else "GBP"
    return "USD"


def infer_ibkr_primary_exchange(ticker: str) -> str | None:
    _, suffix = _split_ticker(ticker)
    exchanges = _PRIMARY_EXCHANGE_BY_SUFFIX.get(suffix or "")
    return exchanges[0] if exchanges else None


def _preferred_primary_exchanges(ticker: str) -> tuple[str, ...]:
    _, suffix = _split_ticker(ticker)
    return _PRIMARY_EXCHANGE_BY_SUFFIX.get(suffix or "", ())


def _ticker_from_contract(contract: Contract) -> str:
    symbol = str(getattr(contract, "symbol", "") or "").upper()
    primary_exchange = str(getattr(contract, "primaryExchange", "") or getattr(contract, "exchange", "") or "").upper()
    suffix = _SUFFIX_BY_PRIMARY_EXCHANGE.get(primary_exchange)
    return f"{symbol}.{suffix}" if suffix else symbol


def _display_exchange(primary_exchange: str | None) -> str | None:
    if not primary_exchange:
        return None
    return _DISPLAY_EXCHANGE_BY_PRIMARY.get(primary_exchange.upper(), primary_exchange.upper())


def _parse_ibkr_timestamp(raw_value: Any) -> datetime:
    if isinstance(raw_value, datetime):
        return raw_value.astimezone(timezone.utc)

    text = str(raw_value).strip()
    if text.isdigit():
        return datetime.fromtimestamp(int(text), tz=timezone.utc)

    for fmt in ("%Y%m%d  %H:%M:%S", "%Y%m%d", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    raise RuntimeError(f"Unable to parse IBKR timestamp: {raw_value}")


def _duration_string(start: datetime, end: datetime) -> str:
    duration_days = max(1, int((end - start).total_seconds() // 86400) + 1)
    return f"{duration_days} D"


def _bar_size_setting(timeframe: str) -> str:
    normalized = timeframe.lower()
    if normalized == "1min":
        return "1 min"
    if normalized == "5min":
        return "5 mins"
    if normalized == "15min":
        return "15 mins"
    if normalized == "1day":
        return "1 day"
    raise RuntimeError(f"Unsupported IBKR timeframe: {timeframe}")


@dataclass(slots=True)
class IbkrContractSummary:
    ticker: str
    name: str | None
    exchange: str | None
    primary_exchange: str | None
    currency: str


@dataclass(slots=True)
class IbkrQuote:
    ticker: str
    last_price: float
    previous_close: float | None
    timestamp: datetime
    source: str
    contract: IbkrContractSummary


@dataclass(slots=True)
class IbkrHistoricalBar:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(slots=True)
class _IbkrRequestState:
    event: threading.Event = field(default_factory=threading.Event)
    error: RuntimeError | None = None
    contract_details: list[ContractDetails] = field(default_factory=list)
    symbol_samples: list[ContractDescription] = field(default_factory=list)
    bars: list[BarData] = field(default_factory=list)
    ticks: dict[int, float] = field(default_factory=dict)


if IBAPI_AVAILABLE:

    class _IbkrSyncApp(EWrapper, EClient):
        def __init__(self) -> None:
            EWrapper.__init__(self)
            EClient.__init__(self, wrapper=self)
            self.ready_event = threading.Event()
            self.connection_error: RuntimeError | None = None
            self._states: dict[int, _IbkrRequestState] = {}
            self._states_lock = threading.Lock()
            self._thread: threading.Thread | None = None

        def start(self, host: str, port: int, client_id: int, timeout_seconds: int) -> None:
            self.connect(host, port, client_id)
            self._thread = threading.Thread(target=self.run, daemon=True)
            self._thread.start()
            if not self.ready_event.wait(timeout=timeout_seconds):
                self.disconnect()
                raise RuntimeError("Timed out while waiting for the IBKR API handshake.")
            if self.connection_error is not None:
                self.disconnect()
                raise self.connection_error

        def close(self) -> None:
            if self.isConnected():
                self.disconnect()
            if self._thread is not None:
                self._thread.join(timeout=1)

        def nextValidId(self, orderId: int) -> None:  # noqa: N802
            self.ready_event.set()

        def error(self, reqId: int, errorCode: int, errorString: str, advancedOrderRejectJson: str = "") -> None:  # noqa: N803
            if errorCode in _NON_FATAL_ERROR_CODES:
                return

            error = RuntimeError(f"IBKR error {errorCode}: {errorString}")
            if reqId < 0:
                self.connection_error = error
                self.ready_event.set()
                return

            state = self._states.get(reqId)
            if state is None:
                return
            state.error = error
            state.event.set()

        def register_state(self, req_id: int) -> _IbkrRequestState:
            state = _IbkrRequestState()
            with self._states_lock:
                self._states[req_id] = state
            return state

        def pop_state(self, req_id: int) -> _IbkrRequestState | None:
            with self._states_lock:
                return self._states.pop(req_id, None)

        def contractDetails(self, reqId: int, contractDetails: ContractDetails) -> None:  # noqa: N802
            state = self._states.get(reqId)
            if state is not None:
                state.contract_details.append(contractDetails)

        def contractDetailsEnd(self, reqId: int) -> None:  # noqa: N802
            state = self._states.get(reqId)
            if state is not None:
                state.event.set()

        def symbolSamples(self, reqId: int, contractDescriptions: list[ContractDescription]) -> None:  # noqa: N802
            state = self._states.get(reqId)
            if state is not None:
                state.symbol_samples.extend(contractDescriptions)
                state.event.set()

        def historicalData(self, reqId: int, bar: BarData) -> None:  # noqa: N802
            state = self._states.get(reqId)
            if state is not None:
                state.bars.append(bar)

        def historicalDataEnd(self, reqId: int, start: str, end: str) -> None:  # noqa: N802
            state = self._states.get(reqId)
            if state is not None:
                state.event.set()

        def tickPrice(self, reqId: int, tickType: int, price: float, attrib: Any) -> None:  # noqa: N802
            state = self._states.get(reqId)
            if state is not None and price and price > 0:
                state.ticks[tickType] = price

        def tickSnapshotEnd(self, reqId: int) -> None:  # noqa: N802
            state = self._states.get(reqId)
            if state is not None:
                state.event.set()


else:

    class _IbkrSyncApp:  # pragma: no cover - only used when ibapi is missing.
        def start(self, host: str, port: int, client_id: int, timeout_seconds: int) -> None:
            raise RuntimeError("The ibapi package is not installed.")

        def close(self) -> None:
            return


@dataclass(slots=True)
class _ResolvedContract:
    detail: ContractDetails
    summary: IbkrContractSummary


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


class IbkrMarketDataClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._timeout_seconds = max(4, min(settings.request_timeout_seconds, _DEFAULT_TIMEOUT_SECONDS))
        self._app = _IbkrSyncApp()
        self._request_id_counter = count(settings.ibkr_client_id + 1000)
        self._resolved_contracts: dict[str, _ResolvedContract] = {}

    def __enter__(self) -> IbkrMarketDataClient:
        if not self.settings.ibkr_host:
            raise RuntimeError("IBKR market data is not configured. Set IBKR_HOST first.")
        self._app.start(
            self.settings.ibkr_host,
            self.settings.ibkr_port,
            self.settings.ibkr_client_id,
            self._timeout_seconds,
        )
        if IBAPI_AVAILABLE:
            self._app.reqMarketDataType(1)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._app.close()

    def _next_request_id(self) -> int:
        return next(self._request_id_counter)

    def _await_request(self, req_id: int) -> _IbkrRequestState:
        state = self._app.register_state(req_id)
        return state

    def _finish_request(self, req_id: int, state: _IbkrRequestState, *, timeout_message: str) -> _IbkrRequestState:
        if not state.event.wait(timeout=self._timeout_seconds):
            self._app.pop_state(req_id)
            raise RuntimeError(timeout_message)
        self._app.pop_state(req_id)
        if state.error is not None:
            raise state.error
        return state

    def _resolve_contract_detail(self, ticker: str) -> ContractDetails:
        normalized_ticker = ticker.strip().upper()
        cached = self._resolved_contracts.get(normalized_ticker)
        if cached is not None:
            return cached.detail

        root_symbol, _ = _split_ticker(normalized_ticker)
        contract = Contract()
        contract.symbol = root_symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = infer_ibkr_currency(normalized_ticker)

        req_id = self._next_request_id()
        state = self._await_request(req_id)
        self._app.reqContractDetails(req_id, contract)
        state = self._finish_request(
            req_id,
            state,
            timeout_message=f"Timed out while resolving the IBKR contract for {normalized_ticker}.",
        )
        detail = self._select_contract_detail(normalized_ticker, state.contract_details)
        if detail is None:
            raise RuntimeError(f"IBKR could not resolve a European stock contract for {normalized_ticker}.")

        summary = self._contract_summary_from_detail(detail)
        resolved = _ResolvedContract(detail=detail, summary=summary)
        self._resolved_contracts[normalized_ticker] = resolved
        self._resolved_contracts.setdefault(summary.ticker, resolved)
        return detail

    def _select_contract_detail(self, ticker: str, contract_details: list[ContractDetails]) -> ContractDetails | None:
        preferred_exchanges = set(_preferred_primary_exchanges(ticker))
        preferred_currency = infer_ibkr_currency(ticker)
        filtered = [
            detail
            for detail in contract_details
            if str(getattr(detail.contract, "secType", "") or "").upper() == "STK"
            and str(getattr(detail.contract, "currency", "") or "").upper() == preferred_currency
        ]
        if not filtered:
            return None

        def score(detail: ContractDetails) -> tuple[int, int, str]:
            primary_exchange = str(getattr(detail.contract, "primaryExchange", "") or getattr(detail.contract, "exchange", "") or "").upper()
            return (
                0 if primary_exchange in preferred_exchanges else 1,
                0 if primary_exchange in _SUFFIX_BY_PRIMARY_EXCHANGE else 1,
                primary_exchange,
            )

        return sorted(filtered, key=score)[0]

    def _contract_summary_from_detail(self, detail: ContractDetails) -> IbkrContractSummary:
        primary_exchange = str(
            getattr(detail.contract, "primaryExchange", "") or getattr(detail.contract, "exchange", "") or ""
        ).upper()
        return IbkrContractSummary(
            ticker=_ticker_from_contract(detail.contract),
            name=str(getattr(detail, "longName", "") or getattr(detail, "marketName", "") or detail.contract.symbol).strip(),
            exchange=_display_exchange(primary_exchange),
            primary_exchange=primary_exchange or None,
            currency=str(getattr(detail.contract, "currency", "") or "EUR").upper(),
        )

    def search_stocks(self, query: str, *, currency: str = "EUR", limit: int = 100) -> list[IbkrContractSummary]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        req_id = self._next_request_id()
        state = self._await_request(req_id)
        self._app.reqMatchingSymbols(req_id, normalized_query)
        state = self._finish_request(
            req_id,
            state,
            timeout_message=f"Timed out while searching IBKR symbols for {normalized_query}.",
        )

        discovered_tickers: list[str] = []
        for description in state.symbol_samples:
            contract = getattr(description, "contract", None)
            if contract is None:
                continue
            if str(getattr(contract, "secType", "") or "").upper() != "STK":
                continue
            if str(getattr(contract, "currency", "") or "").upper() != currency.upper():
                continue
            primary_exchange = str(getattr(contract, "primaryExchange", "") or getattr(contract, "exchange", "") or "").upper()
            if primary_exchange not in _SUFFIX_BY_PRIMARY_EXCHANGE:
                continue
            discovered_tickers.append(_ticker_from_contract(contract))

        results: list[IbkrContractSummary] = []
        seen: set[str] = set()
        for ticker in discovered_tickers:
            if ticker in seen:
                continue
            seen.add(ticker)
            try:
                detail = self._resolve_contract_detail(ticker)
            except RuntimeError:
                continue
            results.append(self._contract_summary_from_detail(detail))
            if len(results) >= limit:
                break

        return results

    def fetch_quote(self, ticker: str) -> IbkrQuote:
        detail = self._resolve_contract_detail(ticker)
        summary = self._contract_summary_from_detail(detail)
        req_id = self._next_request_id()
        state = self._await_request(req_id)
        self._app.reqMktData(req_id, detail.contract, "", True, False, [])
        state = self._finish_request(
            req_id,
            state,
            timeout_message=f"Timed out while requesting the IBKR quote for {ticker.upper()}.",
        )
        self._app.cancelMktData(req_id)

        last_price = (
            state.ticks.get(4)
            or state.ticks.get(68)
            or _midpoint(state.ticks.get(1) or state.ticks.get(66), state.ticks.get(2) or state.ticks.get(67))
            or state.ticks.get(9)
            or state.ticks.get(75)
        )
        previous_close = state.ticks.get(9) or state.ticks.get(75)
        if last_price is None:
            raise RuntimeError(f"IBKR did not return a quote for {ticker.upper()}.")

        return IbkrQuote(
            ticker=summary.ticker,
            last_price=float(last_price),
            previous_close=float(previous_close) if previous_close is not None else None,
            timestamp=datetime.now(timezone.utc),
            source="ibkr",
            contract=summary,
        )

    def fetch_historical_bars(
        self,
        ticker: str,
        *,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[IbkrHistoricalBar]:
        detail = self._resolve_contract_detail(ticker)
        req_id = self._next_request_id()
        state = self._await_request(req_id)
        self._app.reqHistoricalData(
            req_id,
            detail.contract,
            end.astimezone(timezone.utc).strftime("%Y%m%d %H:%M:%S UTC"),
            _duration_string(start.astimezone(timezone.utc), end.astimezone(timezone.utc)),
            _bar_size_setting(timeframe),
            "TRADES",
            1,
            1,
            False,
            [],
        )
        state = self._finish_request(
            req_id,
            state,
            timeout_message=f"Timed out while requesting IBKR historical bars for {ticker.upper()} {timeframe}.",
        )
        self._app.cancelHistoricalData(req_id)

        return [
            IbkrHistoricalBar(
                timestamp=_parse_ibkr_timestamp(bar.date),
                open=Decimal(str(bar.open)),
                high=Decimal(str(bar.high)),
                low=Decimal(str(bar.low)),
                close=Decimal(str(bar.close)),
                volume=int(bar.volume or 0),
            )
            for bar in state.bars
        ]


def _midpoint(bid: float | None, ask: float | None) -> float | None:
    if bid is None or ask is None:
        return None
    if bid <= 0 or ask <= 0:
        return None
    return (bid + ask) / 2
