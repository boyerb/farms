import os
import re
import time
from collections.abc import Iterable, Mapping
from numbers import Real
from typing import Literal

import pandas as pd
import requests

from .Ken_French_library import load_ken_french_data

_ADJUSTED_FIELDS = {
    "1. open": "Open",
    "2. high": "High",
    "3. low": "Low",
    "4. close": "Close",
    "5. adjusted close": "Adjusted Close",
    "6. volume": "Volume",
    "7. dividend amount": "Dividend Amount",
}
_DAILY_ADJUSTED_FIELDS = {
    **_ADJUSTED_FIELDS,
    "8. split coefficient": "Split Coefficient",
}
_ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
_FREQUENCY_CONFIG = {
    "monthly": {
        "function": "TIME_SERIES_MONTHLY_ADJUSTED",
        "response_key": "Monthly Adjusted Time Series",
        "fields": _ADJUSTED_FIELDS,
        "index_frequency": "M",
        "date_format": "YYYY-MM",
        "index_type": "period",
    },
    "weekly": {
        "function": "TIME_SERIES_WEEKLY_ADJUSTED",
        "response_key": "Weekly Adjusted Time Series",
        "fields": _ADJUSTED_FIELDS,
        "index_frequency": "W-FRI",
        "date_format": "YYYY-MM-DD",
        "index_type": "period",
    },
    "daily": {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "response_key": "Time Series (Daily)",
        "fields": _DAILY_ADJUSTED_FIELDS,
        "index_frequency": "D",
        "date_format": "YYYY-MM-DD",
        "index_type": "datetime",
    },
}


class AlphaVantageError(ValueError):
    """Base class for invalid or unusable Alpha Vantage responses."""


class AlphaVantageRateLimitError(AlphaVantageError):
    """Raised when Alpha Vantage reports that the request rate was exceeded."""


class AlphaVantageResponseError(AlphaVantageError):
    """Raised when an Alpha Vantage response is malformed or reports an error."""


def get_alpha_vantage_api_key() -> str:
    """Return the Alpha Vantage key from Colab Secrets or the local environment."""

    try:
        # In Colab, retrieve the key from the Secrets panel.
        from google.colab import userdata

        api_key = userdata.get("ALPHAVANTAGE_API_KEY")
    except ImportError:
        # Local Jupyter and other environments use the operating-system variable.
        api_key = os.environ.get("ALPHAVANTAGE_API_KEY")

    if not api_key:
        raise RuntimeError(
            "ALPHAVANTAGE_API_KEY is not available. Add it to Colab Secrets "
            "or set it in Windows, then restart Jupyter."
        )

    print("Alpha Vantage API key loaded.")
    return api_key


Frequency = Literal["monthly", "weekly"]
Field = Literal["open", "high", "low", "close", "returns"]
FactorSelection = Literal["none", "market", "ff3", "ff5"]

_FIELD_COLUMNS = {
    "open": "Open",
    "high": "High",
    "low": "Low",
    "close": "Close",
    "returns": "Return",
}

_FACTOR_COLUMNS = {
    "Mkt-RF": "ff_mkt_rf",
    "SMB": "ff_smb",
    "HML": "ff_hml",
    "RMW": "ff_rmw",
    "CMA": "ff_cma",
    "RF": "ff_rf",
}


def _parse_bound(value: str | None, name: str, frequency: Frequency):
    if value is None:
        return None
    date_format = _FREQUENCY_CONFIG[frequency]["date_format"]
    pattern = r"\d{4}-\d{2}" if frequency == "monthly" else r"\d{4}-\d{2}-\d{2}"
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError(f"{name} must use the '{date_format}' format.")
    try:
        if frequency == "monthly":
            return pd.Period(value, freq="M")
        if frequency == "weekly":
            return pd.Period(value, freq="W-FRI")
        return pd.Timestamp(value)
    except ValueError as error:
        raise ValueError(f"{name} must use the '{date_format}' format.") from error


def _validate_date_range(
    start_date: str | None, end_date: str | None, frequency: Frequency
):
    start_bound = _parse_bound(start_date, "start_date", frequency)
    end_bound = _parse_bound(end_date, "end_date", frequency)
    if start_bound is not None and end_bound is not None and start_bound > end_bound:
        raise ValueError("start_date must not be after end_date.")
    return start_bound, end_bound


def _validate_frequency(frequency: str) -> Frequency:
    if frequency not in {"monthly", "weekly"}:
        raise ValueError(
            "frequency must be 'monthly' or 'weekly'; daily Alpha Vantage "
            "data is not supported for free-account compatibility."
        )
    return frequency  # type: ignore[return-value]


def _validate_field(field: str | None) -> Field | None:
    if field is None:
        return None
    if not isinstance(field, str) or field.casefold() not in _FIELD_COLUMNS:
        raise ValueError("field must be one of 'open', 'high', 'low', 'close', or 'returns'.")
    return field.casefold()  # type: ignore[return-value]


def _normalize_symbols(symbol: str | Iterable[str]) -> list[str]:
    if isinstance(symbol, str):
        symbols = [symbol]
    else:
        try:
            symbols = list(symbol)
        except TypeError as error:
            raise ValueError(
                "symbol must be a ticker string or an iterable of ticker strings."
            ) from error

    if not symbols:
        raise ValueError("symbol must contain at least one ticker string.")
    if any(not isinstance(item, str) or not item.strip() for item in symbols):
        raise ValueError("symbol must contain only nonempty ticker strings.")
    if len(set(symbols)) != len(symbols):
        raise ValueError("symbol must not contain duplicate ticker strings.")
    return symbols


def _validate_include_factors(include_factors: str) -> FactorSelection:
    if not isinstance(include_factors, str):
        raise ValueError(
            "include_factors must be 'none', 'market', 'ff3', or 'ff5'."
        )
    selection = include_factors.casefold()
    if selection not in {"none", "market", "ff3", "ff5"}:
        raise ValueError(
            "include_factors must be 'none', 'market', 'ff3', or 'ff5'."
        )
    return selection  # type: ignore[return-value]


def _load_alpha_vantage_factors(
    frequency: Frequency,
    start_date: str | None,
    end_date: str | None,
    include_factors: FactorSelection,
) -> pd.DataFrame | None:
    """Load and select Ken French factors for an Alpha Vantage result."""
    if include_factors == "none":
        return None

    model = "ff3" if include_factors == "market" else include_factors
    factor_data = load_ken_french_data(
        model,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
    )

    factor_columns = {
        "market": ["Mkt-RF", "RF"],
        "ff3": ["Mkt-RF", "SMB", "HML", "RF"],
        "ff5": ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"],
    }[include_factors]
    missing_columns = [
        column for column in factor_columns if column not in factor_data.columns
    ]
    if missing_columns:
        raise ValueError(
            "Ken French factor data is missing required columns: "
            + ", ".join(missing_columns)
        )
    return factor_data[factor_columns].rename(columns=_FACTOR_COLUMNS)


def _validate_request_options(
    symbol: str,
    api_key: str,
    start_date: str | None,
    end_date: str | None,
    frequency: Frequency,
    field: str | None,
    outputsize: str | None,
    max_retries: int,
    backoff_factor: float,
    timeout: float | tuple[float, float],
) -> None:
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol must be a nonempty string.")
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("api_key must be a nonempty string.")
    _validate_date_range(start_date, end_date, frequency)
    _validate_field(field)

    if outputsize is not None:
        raise ValueError("outputsize is only supported for daily data.")

    if (
        isinstance(max_retries, bool)
        or not isinstance(max_retries, int)
        or max_retries < 0
    ):
        raise ValueError("max_retries must be a nonnegative integer.")
    if (
        not isinstance(backoff_factor, Real)
        or isinstance(backoff_factor, bool)
        or backoff_factor < 0
    ):
        raise ValueError("backoff_factor must be nonnegative.")
    if isinstance(timeout, tuple):
        if len(timeout) != 2 or any(
            not isinstance(value, Real) or isinstance(value, bool) or value <= 0
            for value in timeout
        ):
            raise ValueError("timeout must be a positive number or a timeout tuple.")
    elif not isinstance(timeout, Real) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError("timeout must be a positive number or a timeout tuple.")


def _load_alpha_vantage(
    symbol: str,
    api_key: str,
    frequency: Frequency,
    start_date: str | None,
    end_date: str | None,
    *,
    field: Field | None = None,
    outputsize: str | None = None,
    timeout: float | tuple[float, float] = 30,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    frequency = _validate_frequency(frequency)
    config = _FREQUENCY_CONFIG[frequency]
    _validate_request_options(
        symbol,
        api_key,
        start_date,
        end_date,
        frequency,
        field,
        outputsize,
        max_retries,
        backoff_factor,
        timeout,
    )

    params = {
        "function": config["function"],
        "symbol": symbol,
        "apikey": api_key,
    }
    if outputsize is not None:
        params["outputsize"] = outputsize
    get = session.get if session is not None else requests.get

    for attempt in range(max_retries + 1):
        try:
            response = get(_ALPHA_VANTAGE_URL, params=params, timeout=timeout)
        except requests.RequestException:
            if attempt >= max_retries:
                raise
            if backoff_factor:
                time.sleep(backoff_factor * (2**attempt))
            continue

        status_code = getattr(response, "status_code", None)
        retryable_status = status_code == 429 or (
            status_code is not None and 500 <= status_code <= 599
        )
        if retryable_status and attempt < max_retries:
            if backoff_factor:
                time.sleep(backoff_factor * (2**attempt))
            continue

        try:
            return format_alpha_vantage_time_series(
                response, frequency, start_date, end_date, field=field
            )
        except AlphaVantageRateLimitError:
            if attempt >= max_retries:
                raise
            if backoff_factor:
                time.sleep(backoff_factor * (2**attempt))

    raise RuntimeError("Alpha Vantage request retry loop ended unexpectedly.")


def load_alpha_vantage(
    symbol: str | Iterable[str],
    api_key: str,
    frequency: Frequency,
    field: Field,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    include_factors: FactorSelection = "market",
    timeout: float | tuple[float, float] = 30,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Download one selected Alpha Vantage series for one or more tickers.

    ``symbol`` may be one ticker string or an iterable of ticker strings.
    ``frequency`` must be ``"monthly"`` or ``"weekly"`` and ``field`` is
    required; it must be ``"open"``, ``"high"``, ``"low"``, ``"close"``, or
    ``"returns"``. A single ticker produces one selected-field column.
    Multiple tickers produce one column per ticker, named with the ticker
    symbols. Daily Alpha Vantage data is intentionally not supported because
    the adjusted daily endpoint requires premium access.

    ``include_factors`` selects decimal-return factors from the Kenneth French
    Data Library. ``"market"`` (the default) adds the market excess return
    and risk-free rate, ``"ff3"`` adds the three-factor model and risk-free
    rate, ``"ff5"`` adds the five-factor model and risk-free rate, and
    ``"none"`` adds no factors. Weekly FF5 data is not published by the
    Kenneth French Data Library.
    """

    frequency = _validate_frequency(frequency)
    field = _validate_field(field)
    if field is None:
        raise ValueError(
            "field is required and must be one of 'open', 'high', 'low', "
            "'close', or 'returns'."
        )
    factor_selection = _validate_include_factors(include_factors)
    symbols = _normalize_symbols(symbol)
    frames = [
        _load_alpha_vantage(
            ticker,
            api_key,
            frequency,
            start_date,
            end_date,
            field=field,
            timeout=timeout,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            session=session,
        )
        for ticker in symbols
    ]
    if len(frames) == 1:
        result = frames[0]
    else:
        result = pd.concat(
            [
                frame.rename(columns={frame.columns[0]: ticker})
                for frame, ticker in zip(frames, symbols)
            ],
            axis=1,
            join="outer",
        )
    factor_data = _load_alpha_vantage_factors(
        frequency,
        start_date,
        end_date,
        factor_selection,
    )
    if factor_data is not None:
        result = result.join(factor_data, how="left")
    result.attrs["symbols"] = symbols
    result.attrs["frequency"] = frequency
    result.attrs["field"] = field
    result.attrs["include_factors"] = factor_selection
    return result


def load_alpha_vantage_monthly(
    symbol: str,
    api_key: str,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    field: Field | None = None,
    timeout: float | tuple[float, float] = 30,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Download monthly adjusted data, optionally selecting one field.

    ``field`` may be ``"open"``, ``"high"``, ``"low"``, ``"close"``, or
    ``"returns"``. When omitted, all parsed fields are returned.
    """

    return _load_alpha_vantage(
        symbol,
        api_key,
        "monthly",
        start_date,
        end_date,
        field=field,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        session=session,
    )


def load_alpha_vantage_weekly(
    symbol: str,
    api_key: str,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    field: Field | None = None,
    timeout: float | tuple[float, float] = 30,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Download weekly adjusted data, optionally selecting one field.

    ``field`` may be ``"open"``, ``"high"``, ``"low"``, ``"close"``, or
    ``"returns"``. When omitted, all parsed fields are returned.
    """

    return _load_alpha_vantage(
        symbol,
        api_key,
        "weekly",
        start_date,
        end_date,
        field=field,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        session=session,
    )


def load_alpha_vantage_daily(
    symbol: str,
    api_key: str,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    field: Field | None = None,
    outputsize: Literal["compact", "full"] = "compact",
    timeout: float | tuple[float, float] = 30,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Disabled compatibility wrapper for the premium daily endpoint."""

    return _load_alpha_vantage(
        symbol,
        api_key,
        "daily",
        start_date,
        end_date,
        field=field,
        outputsize=outputsize,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        session=session,
    )


def format_alpha_vantage(
    response: requests.Response,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    field: Field | None = None,
) -> pd.DataFrame:
    """Format a monthly response, optionally selecting one field."""

    return format_alpha_vantage_time_series(
        response, "monthly", start_date, end_date, field=field
    )


def format_alpha_vantage_weekly(
    response: requests.Response,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    field: Field | None = None,
) -> pd.DataFrame:
    """Format a weekly response, optionally selecting one field."""

    return format_alpha_vantage_time_series(
        response, "weekly", start_date, end_date, field=field
    )


def format_alpha_vantage_daily(
    response: requests.Response,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    field: Field | None = None,
) -> pd.DataFrame:
    """Disabled compatibility wrapper for the premium daily endpoint."""

    return format_alpha_vantage_time_series(
        response, "daily", start_date, end_date, field=field
    )


def format_alpha_vantage_time_series(
    response: requests.Response,
    frequency: Frequency = "monthly",
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    field: Field | None = None,
) -> pd.DataFrame:
    """Format an adjusted Alpha Vantage response for one frequency.

    Monthly bounds use ``YYYY-MM``. Weekly bounds use ``YYYY-MM-DD``.
    Monthly and weekly results use a ``PeriodIndex``. Every
    result includes ``Return`` as its final column: the decimal percentage
    change in ``Adjusted Close`` (for example, ``0.01`` means 1 percent).
    The first available observation has no prior observation, so its return is
    ``NaN``. If ``field`` is supplied, only the corresponding column is
    returned. Accepted values are ``"open"``, ``"high"``, ``"low"``,
    ``"close"``, and ``"returns"``.
    """

    frequency = _validate_frequency(frequency)
    field = _validate_field(field)
    config = _FREQUENCY_CONFIG[frequency]
    start_bound, end_bound = _validate_date_range(start_date, end_date, frequency)

    response.raise_for_status()

    try:
        data = response.json()
    except ValueError as error:
        raise AlphaVantageResponseError(
            "Alpha Vantage response did not contain valid JSON."
        ) from error

    if not isinstance(data, Mapping):
        raise AlphaVantageResponseError(
            "Alpha Vantage response must be a JSON object."
        )

    if "Note" in data:
        raise AlphaVantageRateLimitError(f"Alpha Vantage rate limit: {data['Note']}")
    if "Error Message" in data:
        raise AlphaVantageResponseError(
            f"Alpha Vantage API error: {data['Error Message']}"
        )
    if "Information" in data:
        raise AlphaVantageResponseError(
            f"Alpha Vantage information: {data['Information']}"
        )

    response_key = config["response_key"]
    ts_data = data.get(response_key)
    if not isinstance(ts_data, Mapping) or not ts_data:
        raise AlphaVantageResponseError(
            f"Alpha Vantage response did not contain a nonempty '{response_key}'."
        )

    fields = config["fields"]
    for date, observation in ts_data.items():
        if not isinstance(observation, Mapping):
            raise AlphaVantageResponseError(
                f"Alpha Vantage observation for {date!r} must be a JSON object."
            )
        missing_fields = [field for field in fields if field not in observation]
        if missing_fields:
            raise AlphaVantageResponseError(
                f"Alpha Vantage observation for {date!r} is missing expected fields: "
                f"{', '.join(missing_fields)}."
            )

    df = pd.DataFrame.from_dict(ts_data, orient="index")
    df = df.loc[:, list(fields)].rename(columns=fields)

    try:
        df = df.apply(pd.to_numeric, errors="raise")
    except (TypeError, ValueError) as error:
        raise AlphaVantageResponseError(
            f"Alpha Vantage {frequency} observations contain nonnumeric values."
        ) from error

    if df.isna().any().any() or df.isin([float("inf"), float("-inf")]).any().any():
        raise AlphaVantageResponseError(
            f"Alpha Vantage {frequency} observations contain missing or non-finite values."
        )

    if (df["Volume"] < 0).any() or (df["Dividend Amount"] < 0).any():
        raise AlphaVantageResponseError(
            "Alpha Vantage volume and dividend amounts must be nonnegative."
        )
    if "Split Coefficient" in df and (df["Split Coefficient"] <= 0).any():
        raise AlphaVantageResponseError(
            "Alpha Vantage split coefficients must be positive."
        )

    try:
        df.index = pd.to_datetime(df.index, errors="raise")
    except (TypeError, ValueError) as error:
        raise AlphaVantageResponseError(
            f"Alpha Vantage {frequency} observations contain an invalid date."
        ) from error

    if config["index_type"] == "period":
        df.index = df.index.to_period(config["index_frequency"])
    else:
        df.index = df.index.normalize()
    if not df.index.is_unique:
        raise AlphaVantageResponseError(
            f"Alpha Vantage response contains multiple observations for one "
            f"{frequency} period."
        )
    df = df.sort_index()

    # Calculate before applying date bounds so the first requested observation
    # can use the prior observation returned by Alpha Vantage when available.
    df["Return"] = df["Adjusted Close"].pct_change()

    if start_bound is not None:
        df = df[df.index >= start_bound]
    if end_bound is not None:
        df = df[df.index <= end_bound]

    df.index.name = "date"
    metadata = data.get("Meta Data")
    if isinstance(metadata, Mapping) and metadata.get("2. Symbol"):
        df.attrs["symbol"] = metadata["2. Symbol"]

    if field is not None:
        selected = df[[_FIELD_COLUMNS[field]]].copy()
        selected.attrs = df.attrs.copy()
        return selected

    return df
