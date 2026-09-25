import pandas as pd
import pytest

from farms.pipelines import alpha_vantage
from farms.pipelines.alpha_vantage import (
    AlphaVantageRateLimitError,
    AlphaVantageResponseError,
)

_OUTPUT_COLUMNS = [
    "Open",
    "High",
    "Low",
    "Close",
    "Adjusted Close",
    "Volume",
    "Dividend Amount",
    "Return",
]


class _Response:
    def __init__(self, payload=None, error=None, status_code=200):
        self.payload = payload
        self.error = error
        self.status_code = status_code
        self.raise_for_status_called = False

    def raise_for_status(self):
        self.raise_for_status_called = True
        if self.error is not None:
            raise self.error

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def _month(open_price, dividend="0.0000", adjusted_close="10.5000"):
    return {
        "1. open": open_price,
        "2. high": "22.0000",
        "3. low": "9.0000",
        "4. close": "11.0000",
        "5. adjusted close": adjusted_close,
        "6. volume": "123456",
        "7. dividend amount": dividend,
    }


def _successful_payload():
    february = _month("20.0000", "0.1000", adjusted_close="11.5500")
    return {
        "Meta Data": {"2. Symbol": "TEST"},
        "Monthly Adjusted Time Series": {
            "2020-02-28": february,
            "2020-01-31": _month("10.0000"),
        },
    }


def _weekly_payload():
    return {
        "Meta Data": {"2. Symbol": "TEST"},
        "Weekly Adjusted Time Series": {
            "2020-02-28": _month("20.0000", "0.1000"),
            "2020-01-31": _month("10.0000"),
        },
    }


def test_formats_adjusted_monthly_data_by_explicit_api_field_names():
    response = _Response(_successful_payload())

    result = alpha_vantage.format_alpha_vantage(response)

    assert response.raise_for_status_called
    assert list(result.columns) == _OUTPUT_COLUMNS
    assert isinstance(result.index, pd.PeriodIndex)
    assert result.index.freqstr == "M"
    assert result.index.name == "date"
    assert list(result.index) == [
        pd.Period("2020-01", freq="M"),
        pd.Period("2020-02", freq="M"),
    ]
    assert result.loc[pd.Period("2020-01", freq="M"), "Open"] == pytest.approx(10.0)
    assert result.loc[pd.Period("2020-02", freq="M"), "Dividend Amount"] == pytest.approx(0.1)
    assert pd.isna(result.loc[pd.Period("2020-01", freq="M"), "Return"])
    assert result.loc[pd.Period("2020-02", freq="M"), "Return"] == pytest.approx(0.1)
    assert result.attrs["symbol"] == "TEST"


@pytest.mark.parametrize(
    "field, column",
    [
        ("open", "Open"),
        ("high", "High"),
        ("low", "Low"),
        ("close", "Close"),
        ("returns", "Return"),
    ],
)
def test_selects_one_monthly_field(field, column):
    result = alpha_vantage.format_alpha_vantage(
        _Response(_successful_payload()), field=field
    )

    assert list(result.columns) == [column]
    assert result.attrs["symbol"] == "TEST"


def test_field_mapping_does_not_depend_on_json_field_order():
    payload = _successful_payload()
    for date, month in payload["Monthly Adjusted Time Series"].items():
        payload["Monthly Adjusted Time Series"][date] = {
            "6. volume": month["6. volume"],
            "1. open": month["1. open"],
            "7. dividend amount": month["7. dividend amount"],
            "2. high": month["2. high"],
            "5. adjusted close": month["5. adjusted close"],
            "3. low": month["3. low"],
            "4. close": month["4. close"],
        }

    result = alpha_vantage.format_alpha_vantage(_Response(payload))

    january = result.loc[pd.Period("2020-01", freq="M")]
    assert january["Open"] == pytest.approx(10.0)
    assert january["Close"] == pytest.approx(11.0)
    assert january["Volume"] == pytest.approx(123456.0)


def test_filters_inclusive_month_range():
    result = alpha_vantage.format_alpha_vantage(
        _Response(_successful_payload()), "2020-02", "2020-02"
    )

    assert list(result.index) == [pd.Period("2020-02", freq="M")]


def test_formats_weekly_adjusted_data_with_weekly_periods():
    result = alpha_vantage.format_alpha_vantage_weekly(
        _Response(_weekly_payload()), "2020-01-01", "2020-02-28"
    )

    assert isinstance(result.index, pd.PeriodIndex)
    assert result.index.freqstr == "W-FRI"
    assert list(result.index) == [
        pd.Period("2020-01-31", freq="W-FRI"),
        pd.Period("2020-02-28", freq="W-FRI"),
    ]
    assert result.columns[-1] == "Return"
    assert result.attrs["symbol"] == "TEST"


def test_daily_formatter_is_disabled_for_free_account_compatibility():
    with pytest.raises(ValueError, match="daily.*not supported"):
        alpha_vantage.format_alpha_vantage_daily(_Response({}))


def test_empty_date_filter_preserves_public_schema():
    result = alpha_vantage.format_alpha_vantage(
        _Response(_successful_payload()), "2021-01", "2021-02"
    )

    assert result.empty
    assert list(result.columns) == _OUTPUT_COLUMNS
    assert isinstance(result.index, pd.PeriodIndex)
    assert result.index.name == "date"
    assert result.index.freqstr == "M"


@pytest.mark.parametrize(
    "start_date, end_date",
    [
        ("2020-01-01", "2020-02"),
        ("2020-01", "2020-02-01"),
        ("2020-03", "2020-02"),
    ],
)
def test_rejects_invalid_or_reversed_month_range(start_date, end_date):
    with pytest.raises(ValueError, match="YYYY-MM|after"):
        alpha_vantage.format_alpha_vantage(
            _Response(_successful_payload()), start_date, end_date
        )


def test_surfaces_http_errors_before_parsing_payload():
    response = _Response(error=RuntimeError("HTTP 503"))

    with pytest.raises(RuntimeError, match="HTTP 503"):
        alpha_vantage.format_alpha_vantage(response)

    assert response.raise_for_status_called


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"Note": "API call frequency limit reached."}, "rate limit"),
        ({"Error Message": "Invalid API call."}, "Invalid API call"),
        ({"Information": "The demo API key is for demo purposes only."}, "demo API key"),
    ],
)
def test_surfaces_alpha_vantage_error_payloads(payload, message):
    with pytest.raises(ValueError, match=message):
        alpha_vantage.format_alpha_vantage(_Response(payload))


def test_uses_specific_response_error_types():
    with pytest.raises(AlphaVantageRateLimitError):
        alpha_vantage.format_alpha_vantage(
            _Response({"Note": "API call frequency limit reached."})
        )


def test_rejects_invalid_field():
    with pytest.raises(ValueError, match="field"):
        alpha_vantage.format_alpha_vantage(
            _Response(_successful_payload()), field="volume"
        )


def test_load_alpha_vantage_passes_selected_field_to_formatter():
    session = _Session([_Response(_successful_payload())])

    result = alpha_vantage.load_alpha_vantage_monthly(
        "MSFT", "test-key", field="returns", session=session, backoff_factor=0
    )

    assert list(result.columns) == ["Return"]


def test_general_loader_accepts_one_ticker_and_requires_field():
    session = _Session([_Response(_successful_payload())])

    result = alpha_vantage.load_alpha_vantage(
        "MSFT",
        "test-key",
        frequency="monthly",
        field="close",
        session=session,
        backoff_factor=0,
    )

    assert list(result.columns) == ["Close"]
    assert session.calls[0][1]["params"]["symbol"] == "MSFT"


def test_general_loader_rejects_missing_field():
    with pytest.raises(ValueError, match="field is required"):
        alpha_vantage.load_alpha_vantage(
            "MSFT", "test-key", frequency="monthly", field=None
        )


def test_general_loader_rejects_daily_frequency_before_request():
    session = _Session([])

    with pytest.raises(ValueError, match="daily.*not supported"):
        alpha_vantage.load_alpha_vantage(
            "MSFT",
            "test-key",
            frequency="daily",
            field="close",
            session=session,
        )

    assert session.calls == []
    with pytest.raises(AlphaVantageResponseError):
        alpha_vantage.format_alpha_vantage(
            _Response({"Error Message": "Invalid API call."})
        )


def test_rejects_payload_with_missing_adjusted_monthly_field():
    payload = _successful_payload()
    del payload["Monthly Adjusted Time Series"]["2020-01-31"]["7. dividend amount"]

    with pytest.raises(ValueError, match="missing expected fields"):
        alpha_vantage.format_alpha_vantage(_Response(payload))


def test_rejects_malformed_json_response():
    with pytest.raises(ValueError, match="valid JSON"):
        alpha_vantage.format_alpha_vantage(_Response(ValueError("invalid JSON")))


def test_rejects_duplicate_months():
    payload = _successful_payload()
    payload["Monthly Adjusted Time Series"]["2020-02-15"] = _month("20.0000")

    with pytest.raises(ValueError, match="multiple observations"):
        alpha_vantage.format_alpha_vantage(_Response(payload))


class _Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return next(self.responses)


def test_load_alpha_vantage_monthly_fetches_and_formats_response():
    session = _Session([_Response(_successful_payload())])

    result = alpha_vantage.load_alpha_vantage_monthly(
        "MSFT", "test-key", start_date="2020-01", end_date="2020-02", session=session
    )

    assert len(session.calls) == 1
    url, kwargs = session.calls[0]
    assert url == "https://www.alphavantage.co/query"
    assert kwargs["params"] == {
        "function": "TIME_SERIES_MONTHLY_ADJUSTED",
        "symbol": "MSFT",
        "apikey": "test-key",
    }
    assert kwargs["timeout"] == 30
    assert list(result.index) == [
        pd.Period("2020-01", freq="M"),
        pd.Period("2020-02", freq="M"),
    ]


def test_load_alpha_vantage_monthly_retries_rate_limit_without_sleep():
    session = _Session(
        [
            _Response({"Note": "API call frequency limit reached."}),
            _Response(_successful_payload()),
        ]
    )

    result = alpha_vantage.load_alpha_vantage_monthly(
        "MSFT", "test-key", session=session, backoff_factor=0
    )

    assert len(session.calls) == 2
    assert not result.empty


def test_load_alpha_vantage_weekly_uses_weekly_endpoint():
    session = _Session([_Response(_weekly_payload())])

    result = alpha_vantage.load_alpha_vantage_weekly(
        "MSFT", "test-key", session=session, backoff_factor=0
    )

    assert session.calls[0][1]["params"]["function"] == "TIME_SERIES_WEEKLY_ADJUSTED"
    assert isinstance(result.index, pd.PeriodIndex)
    assert result.index.freqstr == "W-FRI"


def test_load_alpha_vantage_daily_is_disabled():
    with pytest.raises(ValueError, match="daily.*not supported"):
        alpha_vantage.load_alpha_vantage_daily(
            "MSFT", "test-key", session=_Session([])
        )
