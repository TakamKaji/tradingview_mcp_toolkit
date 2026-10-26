"""Request contracts from TradingView MCP Tool Discovery snapshots."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import ClassVar, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    TypeAdapter,
    field_validator,
    model_validator,
)

ScreenerFilterPreset = Literal[
    "pullback_with_reversal", "breakout_with_volume", "oversold_healthy", "earnings_runup",
    "relative_strength", "new_highs",
]


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_json_values(self) -> ToolRequest:
        try:
            json.dumps(self.model_dump(mode="python", exclude_unset=True), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("Request must contain finite JSON values") from exc
        return self


class _PatternExtraRequest(ToolRequest):
    """Preserve the two provider schemas that permit named pattern properties."""

    model_config = ConfigDict(extra="allow", strict=True, allow_inf_nan=False)
    allowed_extra_pattern: ClassVar[str]

    @model_validator(mode="after")
    def validate_pattern_properties(self) -> _PatternExtraRequest:
        for name, value in (self.model_extra or {}).items():
            if re.fullmatch(self.allowed_extra_pattern, name) is None:
                raise ValueError("Unexpected request property")
            TypeAdapter(JsonValue).validate_python(value)
        return self


class ListWatchlistsRequest(ToolRequest):
    pass


class GetWatchlistRequest(ToolRequest):
    watchlist_id: str


class GetActiveWatchlistRequest(ToolRequest):
    pass


class CreateWatchlistRequest(ToolRequest):
    name: str = Field(default=None, max_length=500)
    symbols: list[str] | None = None


class DeleteWatchlistRequest(ToolRequest):
    watchlist_id: str


class AddToWatchlistRequest(ToolRequest):
    watchlist_id: str
    symbols: list[str] | None


class RemoveFromWatchlistRequest(ToolRequest):
    watchlist_id: str
    symbols: list[str] | None


class UpdateWatchlistRequest(ToolRequest):
    watchlist_id: str
    name: str = Field(default=None, max_length=500)
    description: str | None = None


class GetOhlcvRequest(ToolRequest):
    symbol: str
    interval: Literal["1m", "5m", "15m", "30m", "1h", "4h", "1D", "1W", "M", "1mo", "month"] = None
    count: int = Field(default=None, le=8000)
    date_from: str = None
    date_to: str = None
    format: Literal["rows", "columns"] = None
    summary: bool = None

    @model_validator(mode="after")
    def validate_count_for_format(self) -> GetOhlcvRequest:
        if self.count is not None and self.count > 5000 and self.format != "columns":
            raise ValueError("OHLCV count above 5000 requires columns format")
        return self

    @field_validator("date_from", "date_to")
    @classmethod
    def validate_date_bound(cls, value: str) -> str:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            date.fromisoformat(value)
            return value
        match = re.fullmatch(
            r"\d{4}-\d{2}-\d{2}[Tt](?P<hour>\d{2}):(?P<minute>\d{2}):"
            r"(?P<second>\d{2})(?:\.\d+)?(?:[Zz]|[+-](?P<offset_hour>\d{2}):"
            r"(?P<offset_minute>\d{2}))",
            value,
        )
        if match is not None:
            if (
                int(match["hour"]) > 23 or int(match["minute"]) > 59
                or int(match["second"]) > 59
                or (match["offset_hour"] is not None and int(match["offset_hour"]) > 23)
                or (match["offset_minute"] is not None and int(match["offset_minute"]) > 59)
            ):
                raise ValueError("Date bound contains an out-of-range time component")
            normalized = value.replace("t", "T")
            if normalized.endswith(("Z", "z")):
                normalized = normalized[:-1] + "+00:00"
            datetime.fromisoformat(normalized)
            return value
        raise ValueError("Date bound must be YYYY-MM-DD or RFC3339")


class GetEconomicDataRequest(ToolRequest):
    symbol: str
    date_from: str = None
    date_to: str = None


class GetEconomicSymbolsRequest(ToolRequest):
    country: str = None
    category: Literal["gdp", "lbr", "prce", "hlth", "mny", "trd", "gov", "bsnss", "cnsm", "hse", "txs", "enrg", "clmt"] = None
    search: str = None


class SearchSymbolsRequest(ToolRequest):
    query: str
    type_filter: Literal["stock", "etf", "bond", "forex", "index", "futures", "crypto", "all"] = None


class GetSymbolDataRequest(ToolRequest):
    symbol: str
    columns: list[str] | None = None


class RunScreenerRequest(ToolRequest):
    market: str = None
    filters: dict[str, JsonValue] = None
    sort_by: str = None
    sort_order: Literal["asc", "desc"] = None
    limit: int = Field(default=None, le=1000)
    columns: list[str] | None = None
    symbol_types: list[str] | None = None
    filter_preset: ScreenerFilterPreset = None
    symbolset: list[str] | None = None


class GetSymbolDataBatchRequest(ToolRequest):
    symbols: list[str] | None = Field(max_length=50)
    columns: list[str] | None = None


class GetScreenerColumnsRequest(ToolRequest):
    market: Literal["stock", "etf", "crypto", "bond", "all"] = None
    group: str = None
    search: str = None


class GetTechnicalsRatingRequest(ToolRequest):
    symbol: str
    interval: Literal["1m", "5m", "15m", "30m", "1h", "2h", "4h", "1D", "1W", "1M"] = None


class GetNewsRequest(ToolRequest):
    symbol: str
    lang: Literal[
        "en", "ru", "de", "fr", "es", "pt", "it", "pl", "tr", "ar", "he", "ko", "ja", "vi", "th", "ms", "id",
        "zh-Hans", "zh-Hant", "ro", "en_IN",
    ] = None
    limit: int = Field(default=None, le=200)
    offset: int = None


class GetNewsStoryRequest(ToolRequest):
    id: str
    lang: str = None
    user_prostatus: Literal["pro", "non_pro"] = None
    user_country: str = None


class GetForecastsRequest(ToolRequest):
    symbol: str


class GetFinancialsRequest(ToolRequest):
    symbol: str
    metric: list[str] | None = None
    period: Literal["fy", "fq", "ttm", "fh", "current"] = None


class GetFinancialHistoryRequest(ToolRequest):
    symbol: str
    period: Literal["fq", "fy"] = None
    date_from: str = None
    date_to: str = None


class GetDocumentsRequest(ToolRequest):
    symbol: str
    category: Literal[
        "all", "annual_reports", "quarterly_reports", "interim_reports", "company_events",
        "insider_transactions", "transcripts", "presentations", "press_releases", "other",
        "10-K", "10-Q", "8-K",
    ] = None
    event: Literal["earning", "corporate_event"] = None
    start_date: str = None
    end_date: str = None
    limit: int = None


class GetDocumentViewRequest(ToolRequest):
    view_id: str


class GetEarningsCalendarRequest(ToolRequest):
    symbols: list[str] | None
    date_from: str = None
    date_to: str = None


class GetEconomicCalendarRequest(ToolRequest):
    countries: str = None
    currencies: str = None
    category: Literal[
        "gdp", "bonds", "business", "consumer", "goverment", "health", "housing", "labor", "money",
        "prices", "trade", "taxes", "all",
    ] = None
    date_from: str = None
    date_to: str = None
    min_importance: int | None = Field(default=None, ge=-1, le=1, strict=True)


class GetDividendsCalendarRequest(ToolRequest):
    symbols: list[str] | None = None
    market: str = None
    date_from: str = None
    date_to: str = None
    limit: int = Field(default=None, le=200)


class CreateAlertRequest(_PatternExtraRequest):
    """Create an alert; TradingView currently rejects webhook alerts over MCP."""

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={"patternProperties": {"^(webhook|monitor)$": True}, "additionalProperties": False},
    )
    allowed_extra_pattern = r"^(webhook|monitor)$"

    symbol: str
    price: float = None
    condition: Literal["cross", "cross_up", "cross_down", "greater", "less"] = None
    message: str = Field(default=None, max_length=4000)
    name: str = Field(default=None, max_length=300)
    resolution: str = None
    expiration: str = None
    auto_deactivate: bool = None
    email: bool = None
    mobile_push: bool | None = None
    popup: bool | None = None
    conditions: list[dict[str, JsonValue]] | None = None


class UpdateAlertRequest(_PatternExtraRequest):
    """Update supported fields; TradingView rejects condition, symbol, timeframe, and webhook changes."""

    model_config = ConfigDict(
        extra="allow", json_schema_extra={"patternProperties": {"^(webhook)$": True}, "additionalProperties": False},
    )
    allowed_extra_pattern = r"^(webhook)$"

    alert_id: int
    message: str | None = None
    name: str | None = None
    expiration: str | None = None
    auto_deactivate: bool | None = None
    email: bool | None = None
    mobile_push: bool | None = None
    popup: bool | None = None


class DeleteAlertRequest(ToolRequest):
    alert_ids: list[int] | None


class StopAlertsRequest(ToolRequest):
    alert_ids: list[int] | None


class RestartAlertsRequest(ToolRequest):
    alert_ids: list[int] | None


class ListAlertsRequest(ToolRequest):
    symbol: str = None
    active: bool | None = None


class GetAlertsRequest(ToolRequest):
    alert_ids: list[int] | None


class GetAlertsLogRequest(ToolRequest):
    days: int = None
    symbol: str = None
    limit: int = Field(default=None, le=2000)


REQUEST_MODELS: dict[str, type[ToolRequest]] = {
    "list_watchlists": ListWatchlistsRequest,
    "get_watchlist": GetWatchlistRequest,
    "get_active_watchlist": GetActiveWatchlistRequest,
    "create_watchlist": CreateWatchlistRequest,
    "delete_watchlist": DeleteWatchlistRequest,
    "add_to_watchlist": AddToWatchlistRequest,
    "remove_from_watchlist": RemoveFromWatchlistRequest,
    "update_watchlist": UpdateWatchlistRequest,
    "get_ohlcv": GetOhlcvRequest,
    "get_economic_data": GetEconomicDataRequest,
    "get_economic_symbols": GetEconomicSymbolsRequest,
    "search_symbols": SearchSymbolsRequest,
    "get_symbol_data": GetSymbolDataRequest,
    "run_screener": RunScreenerRequest,
    "get_symbol_data_batch": GetSymbolDataBatchRequest,
    "get_screener_columns": GetScreenerColumnsRequest,
    "get_technicals_rating": GetTechnicalsRatingRequest,
    "get_news": GetNewsRequest,
    "get_news_story": GetNewsStoryRequest,
    "get_forecasts": GetForecastsRequest,
    "get_financials": GetFinancialsRequest,
    "get_financial_history": GetFinancialHistoryRequest,
    "get_documents": GetDocumentsRequest,
    "get_document_view": GetDocumentViewRequest,
    "get_earnings_calendar": GetEarningsCalendarRequest,
    "get_economic_calendar": GetEconomicCalendarRequest,
    "get_dividends_calendar": GetDividendsCalendarRequest,
    "create_alert": CreateAlertRequest,
    "update_alert": UpdateAlertRequest,
    "delete_alert": DeleteAlertRequest,
    "stop_alerts": StopAlertsRequest,
    "restart_alerts": RestartAlertsRequest,
    "list_alerts": ListAlertsRequest,
    "get_alerts": GetAlertsRequest,
    "get_alerts_log": GetAlertsLogRequest,
}


class ContentBlock(BaseModel):
    """MCP content block with typed text and forward-compatible other content types."""

    model_config = ConfigDict(extra="allow", strict=True, allow_inf_nan=False)
    type: str
    text: str | None = None

    @model_validator(mode="after")
    def validate_content(self) -> ContentBlock:
        if self.type == "text" and self.text is None:
            raise ValueError("Text content requires text")
        for value in (self.model_extra or {}).values():
            TypeAdapter(JsonValue).validate_python(value)
        return self


class TypedToolResponse(BaseModel):
    """Response envelope; structured data remains separate from model-facing content."""

    model_config = ConfigDict(extra="allow", strict=True, allow_inf_nan=False)
    structured_content: JsonValue | None
    content: list[ContentBlock]

    @model_validator(mode="after")
    def validate_json_values(self) -> TypedToolResponse:
        for value in (self.model_extra or {}).values():
            TypeAdapter(JsonValue).validate_python(value)
        try:
            json.dumps(self.model_dump(mode="python"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("Response must contain finite JSON values") from exc
        return self


class ObservedReadData(BaseModel):
    """Fields observed across eight live Read responses on 2026-09-26."""

    model_config = ConfigDict(extra="allow", strict=True, allow_inf_nan=False)
    success: bool
    error: str | None = None
    count: int | None = None
    missing_count: int | None = None


class ObservedReadResponse(TypedToolResponse):
    """Read response with observed provider fields and open future data."""

    structured_content: ObservedReadData | None
