import re
import time
from collections.abc import Mapping
from numbers import Real

import pandas as pd
import requests


_MONTHLY_ADJUSTED_FIELDS = {
    "1. open": "Open",
    "2. high": "High",
    "3. low": "Low",
    "4. close": "Close",
    "5. adjusted close": "Adjusted Close",
    "6. volume": "Volume",
    "7. dividend amount": "Dividend Amount",
}
_ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"


class AlphaVantageError(ValueError):
    """Base class for invalid or unusable Alpha Vantage responses."""


class AlphaVantageRateLimitError(AlphaVantageError):
    """Raised when Alpha Vantage reports that the request rate was exceeded."""


class AlphaVantageResponseError(AlphaVantageError):
    """Raised when an Alpha Vantage response is malformed or reports an error."""


def _parse_month(value: str | None, name: str) -> pd.Period | None:
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}", value):
        raise ValueError(f"{name} must use the 'YYYY-MM' format.")
    try:
        return pd.Period(value, freq="M")
    except ValueError as error:
        raise ValueError(f"{name} must use the 'YYYY-MM' format.") from error


def _validate_month_range(
    start_date: str | None, end_date: str | None
) -> tuple[pd.Period | None, pd.Period | None]:
    start_period = _parse_month(start_date, "start_date")
    end_period = _parse_month(end_date, "end_date")
    if start_period is not None and end_period is not None and start_period > end_period:
        raise ValueError("start_date must not be after end_date.")
    return start_period, end_period


def load_alpha_vantage_monthly(
    symbol: str,
    api_key: str,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    timeout: float | tuple[float, float] = 30,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Download and format monthly adjusted prices from Alpha Vantage.

    Retries are attempted for HTTP 429/5xx responses and Alpha Vantage rate-limit
    messages, using exponential backoff. Pass a session to reuse connections or
    to inject a test double.
    """

    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol must be a nonempty string.")
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("api_key must be a nonempty string.")
    _validate_month_range(start_date, end_date)
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

    params = {
        "function": "TIME_SERIES_MONTHLY_ADJUSTED",
        "symbol": symbol,
        "apikey": api_key,
    }
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
            return format_alpha_vantage(response, start_date, end_date)
        except AlphaVantageRateLimitError:
            if attempt >= max_retries:
                raise
            if backoff_factor:
                time.sleep(backoff_factor * (2**attempt))

    raise RuntimeError("Alpha Vantage request retry loop ended unexpectedly.")


def format_alpha_vantage(
    response: requests.Response,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """Format an Alpha Vantage monthly adjusted response as a DataFrame.

    Parameters
    ----------
    response : requests.Response
        Response from an Alpha Vantage ``TIME_SERIES_MONTHLY_ADJUSTED`` request.
    start_date, end_date : str, optional
        Inclusive monthly filters in ``YYYY-MM`` format. ``None`` leaves that
        side of the date range unbounded.

    Returns
    -------
    pandas.DataFrame
        Numeric Open, High, Low, Close, Adjusted Close, Volume, and Dividend
        Amount columns with a monthly ``PeriodIndex`` named ``date``.

    Raises
    ------
    ValueError
        If dates are invalid.
    AlphaVantageError
        If the response is malformed or Alpha Vantage returns an API,
        information, or rate-limit message.
    """

    start_period, end_period = _validate_month_range(start_date, end_date)

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

    ts_data = data.get("Monthly Adjusted Time Series")
    if not isinstance(ts_data, Mapping) or not ts_data:
        raise AlphaVantageResponseError(
            "Alpha Vantage response did not contain a nonempty "
            "'Monthly Adjusted Time Series'."
        )

    for date, observation in ts_data.items():
        if not isinstance(observation, Mapping):
            raise AlphaVantageResponseError(
                f"Alpha Vantage observation for {date!r} must be a JSON object."
            )
        missing_fields = [
            field for field in _MONTHLY_ADJUSTED_FIELDS if field not in observation
        ]
        if missing_fields:
            raise AlphaVantageResponseError(
                f"Alpha Vantage observation for {date!r} is missing expected fields: "
                f"{', '.join(missing_fields)}."
            )

    # Convert the time series dictionary into a Pandas DataFrame.
    # Using orient="index" tells Pandas to use the dictionary keys (dates)
    # as the DataFrame index, so each row corresponds to one month.
    df = pd.DataFrame.from_dict(ts_data, orient="index")

    # Select source fields by name so JSON key order cannot affect the result.
    df = df.loc[:, list(_MONTHLY_ADJUSTED_FIELDS)].rename(
        columns=_MONTHLY_ADJUSTED_FIELDS
    )

    # Convert string values into numeric floats.
    # JSON encodes all numbers as strings, so they must be converted
    # for analysis, plotting, and calculations.
    try:
        df = df.apply(pd.to_numeric, errors="raise")
    except (TypeError, ValueError) as error:
        raise AlphaVantageResponseError(
            "Alpha Vantage monthly observations contain nonnumeric values."
        ) from error

    if df.isna().any().any() or df.isin([float("inf"), float("-inf")]).any().any():
        raise AlphaVantageResponseError(
            "Alpha Vantage monthly observations contain missing or non-finite values."
        )

    if (df["Volume"] < 0).any() or (df["Dividend Amount"] < 0).any():
        raise AlphaVantageResponseError(
            "Alpha Vantage volume and dividend amounts must be nonnegative."
        )

    # Convert the index to monthly periods and sort chronologically.
    try:
        df.index = pd.to_datetime(df.index, errors="raise")
    except (TypeError, ValueError) as error:
        raise AlphaVantageResponseError(
            "Alpha Vantage monthly observations contain an invalid date."
        ) from error
    df.index = df.index.to_period("M")
    if not df.index.is_unique:
        raise AlphaVantageResponseError(
            "Alpha Vantage response contains multiple observations for one month."
        )
    df = df.sort_index()

    # Apply optional date filtering.
    if start_period is not None:
        df = df[df.index >= start_period]
    if end_period is not None:
        df = df[df.index <= end_period]

    df.index.name = "date"
    metadata = data.get("Meta Data")
    if isinstance(metadata, Mapping) and metadata.get("2. Symbol"):
        df.attrs["symbol"] = metadata["2. Symbol"]

    return df
