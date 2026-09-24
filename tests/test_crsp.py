import pandas as pd
import pytest

import farms
from farms.pipelines import crsp


_RESULT_COLUMNS = [
    "permno",
    "permco",
    "ticker",
    "comnam",
    "shrcd",
    "exchcd",
    "siccd",
    "prc",
    "ret",
    "retx",
    "vol",
    "shrout",
]


class _Database:
    """Minimal stand-in for the caller-owned WRDS database wrapper."""

    connection = object()


def _source_frame(rows):
    frame = pd.DataFrame(rows)
    for column in ["date", *_RESULT_COLUMNS]:
        if column not in frame:
            frame[column] = pd.NA
    return frame[["date", *_RESULT_COLUMNS]]


def _factor_frame(frequency="monthly"):
    if frequency == "monthly":
        index = pd.PeriodIndex(["2020-01"], freq="M", name="date")
    else:
        index = pd.DatetimeIndex(["2020-01-03"], name="date")
    return pd.DataFrame(
        {
            "Mkt-RF": [0.01],
            "SMB": [0.002],
            "HML": [-0.003],
            "RMW": [0.004],
            "CMA": [-0.005],
            "RF": [0.0001],
        },
        index=index,
    )


def _capture_queries(monkeypatch, frames):
    calls = []
    responses = iter(frames)

    def fake_read_sql_query(sql, con, params=None):
        calls.append({"sql": sql, "connection": con, "params": params})
        return next(responses).copy()

    monkeypatch.setattr(crsp.pd, "read_sql_query", fake_read_sql_query)
    return calls


def _values(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _values(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _values(item)
    else:
        yield value


def _parameter_dates(params):
    dates = set()
    for value in _values(params):
        try:
            dates.add(pd.Timestamp(value).date().isoformat())
        except (TypeError, ValueError):
            pass
    return dates


def test_permno_query_is_parameterized_and_returns_monthly_period_index(monkeypatch):
    calls = _capture_queries(
        monkeypatch,
        [
            _source_frame(
                [
                    {"date": "2020-02-28", "permno": 12079, "ticker": "MSFT"},
                    {"date": "2020-01-31", "permno": 14593, "ticker": "AAPL"},
                ]
            )
        ],
    )

    result = crsp.load_crsp_data(
        _Database(),
        [14593, 12079],
        "2020-01",
        "2020-02",
        identifier_type="permno",
    )

    assert len(calls) == 1
    call = calls[0]
    assert call["connection"] is _Database.connection
    assert call["params"] is not None
    assert {14593, 12079}.issubset(set(_values(call["params"])))
    assert {"2020-01-01", "2020-03-01"}.issubset(
        _parameter_dates(call["params"])
    )
    assert "14593" not in call["sql"]
    assert "12079" not in call["sql"]
    assert "a.date >= b.namedt" in call["sql"]
    assert "a.date <= b.nameendt" in call["sql"]
    assert "a.date < %s" in call["sql"]

    assert list(result.columns) == _RESULT_COLUMNS
    assert isinstance(result.index, pd.PeriodIndex)
    assert result.index.name == "date"
    assert list(result.index) == [
        pd.Period("2020-01", freq="M"),
        pd.Period("2020-02", freq="M"),
    ]
    assert list(result["permno"]) == [14593, 12079]


def test_ticker_query_normalizes_tickers_and_keeps_values_out_of_sql(monkeypatch):
    calls = _capture_queries(
        monkeypatch,
        [_source_frame([{"date": "2020-01-31", "permno": 14593, "ticker": "AAPL"}])],
    )

    crsp.load_crsp_data(
        _Database(), [" aapl "], "2020-01", "2020-01", identifier_type="ticker"
    )

    assert len(calls) == 1
    assert "AAPL" in set(_values(calls[0]["params"]))
    assert "AAPL" not in calls[0]["sql"]


def test_daily_query_uses_daily_tables_and_datetime_index(monkeypatch):
    calls = _capture_queries(
        monkeypatch,
        [_source_frame([{"date": "2020-01-03", "permno": 14593, "ticker": "AAPL"}])],
    )

    result = crsp.load_crsp_data(
        _Database(),
        [14593],
        "2020-01-02",
        "2020-01-03",
        identifier_type="permno",
        frequency="daily",
    )

    sql = calls[0]["sql"]
    assert "FROM crsp.dsf a" in sql
    assert "crsp.dsenames" in sql
    assert {"2020-01-02", "2020-01-04"}.issubset(
        _parameter_dates(calls[0]["params"])
    )
    assert isinstance(result.index, pd.DatetimeIndex)
    assert result.index.name == "date"
    assert list(result.index) == [pd.Timestamp("2020-01-03")]


def test_load_crsp_merges_market_factors_as_decimal_prefixed_columns(monkeypatch):
    _capture_queries(
        monkeypatch,
        [_source_frame([{"date": "2020-01-31", "permno": 14593}])],
    )
    factor_calls = []

    def fake_factor_loader(model, **kwargs):
        factor_calls.append((model, kwargs))
        return _factor_frame()

    monkeypatch.setattr(crsp, "load_ken_french_data", fake_factor_loader)

    result = crsp.load_crsp_data(
        _Database(),
        [14593],
        "2020-01",
        "2020-01",
        identifier_type="permno",
        include_factors="market",
    )

    assert factor_calls == [
        (
            "ff3",
            {
                "frequency": "monthly",
                "start_date": "2020-01",
                "end_date": "2020-01",
            },
        )
    ]
    assert list(result.columns[-2:]) == ["ff_mkt_rf", "ff_rf"]
    assert result.loc[pd.Period("2020-01", freq="M"), "ff_mkt_rf"] == pytest.approx(0.01)
    assert result.loc[pd.Period("2020-01", freq="M"), "ff_rf"] == pytest.approx(0.0001)
    assert "rf" not in result.columns
    assert "ret" in result.columns


def test_load_crsp_merges_daily_ff5_factors(monkeypatch):
    _capture_queries(
        monkeypatch,
        [_source_frame([{"date": "2020-01-03", "permno": 14593}])],
    )
    factor_calls = []

    def fake_factor_loader(model, **kwargs):
        factor_calls.append((model, kwargs))
        return _factor_frame("daily")

    monkeypatch.setattr(crsp, "load_ken_french_data", fake_factor_loader)

    result = crsp.load_crsp_data(
        _Database(),
        [14593],
        "2020-01-03",
        "2020-01-03",
        identifier_type="permno",
        frequency="daily",
        include_factors="ff5",
    )

    assert factor_calls[0][0] == "ff5"
    assert factor_calls[0][1]["frequency"] == "daily"
    assert list(result.columns[-6:]) == [
        "ff_mkt_rf", "ff_smb", "ff_hml", "ff_rmw", "ff_cma", "ff_rf"
    ]
    assert result.loc[pd.Timestamp("2020-01-03"), "ff_cma"] == pytest.approx(-0.005)


def test_load_all_crsp_merges_ff3_factors(monkeypatch):
    _capture_queries(
        monkeypatch,
        [_source_frame([{"date": "2020-01-31", "permno": 14593}])],
    )
    monkeypatch.setattr(
        crsp,
        "load_ken_french_data",
        lambda model, **kwargs: _factor_frame(),
    )

    result = crsp.load_all_crsp_data(
        _Database(),
        "2020-01",
        "2020-01",
        include_factors="ff3",
    )

    assert list(result.columns[-4:]) == [
        "ff_mkt_rf", "ff_smb", "ff_hml", "ff_rf"
    ]
    assert result.loc[pd.Period("2020-01", freq="M"), "ff_hml"] == pytest.approx(-0.003)


@pytest.mark.parametrize(
    "frequency, start_date, end_date, expected",
    [
        ("weekly", "2020-01", "2020-02", "frequency"),
        ("daily", "2020-01", "2020-02", "YYYY-MM-DD"),
        ("monthly", "2020-01-01", "2020-02-01", "YYYY-MM"),
    ],
)
def test_frequency_and_date_format_are_validated(
    frequency, start_date, end_date, expected
):
    with pytest.raises(ValueError, match=expected):
        crsp.load_crsp_data(
            _Database(),
            [14593],
            start_date,
            end_date,
            identifier_type="permno",
            frequency=frequency,
        )


def test_scalar_identifier_is_rejected():
    with pytest.raises(ValueError, match="one-element list"):
        crsp.load_crsp_data(
            _Database(), "AAPL", "2020-01", "2020-01", identifier_type="ticker"
        )


def test_loader_name_and_legacy_alias_are_public():
    assert crsp.get_crsp_msf_by_ids is crsp.load_crsp_data
    assert farms.load_crsp_data is crsp.load_crsp_data
    assert farms.get_crsp_msf_by_ids is crsp.load_crsp_data
    assert farms.load_all_crsp_data is crsp.load_all_crsp_data


@pytest.mark.parametrize(
    "identifiers, identifier_type",
    [([14593, "AAPL"], None), (["AAPL", ""], "ticker"), ([14593, True], "permno")],
)
def test_invalid_or_mixed_identifiers_are_rejected(identifiers, identifier_type):
    with pytest.raises(ValueError):
        crsp.load_crsp_data(
            _Database(), identifiers, "2020-01", "2020-02", identifier_type=identifier_type
        )


@pytest.mark.parametrize(
    "start_date, end_date",
    [("2020-01-01", "2020-02"), ("2020-01", "2020-02-01"), ("2020-03", "2020-02")],
)
def test_dates_must_be_ordered_months(start_date, end_date):
    with pytest.raises(ValueError):
        crsp.load_crsp_data(
            _Database(), [14593], start_date, end_date, identifier_type="permno"
        )


@pytest.mark.parametrize("chunk_size", [0, -1, 1.5, True])
def test_chunk_size_must_be_a_positive_integer(chunk_size):
    with pytest.raises(ValueError):
        crsp.load_crsp_data(
            _Database(), [14593], "2020-01", "2020-02", chunk_size=chunk_size,
            identifier_type="permno",
        )


def test_large_identifier_list_is_deduplicated_and_chunked(monkeypatch):
    calls = _capture_queries(
        monkeypatch,
        [
            _source_frame([{"date": "2020-01-31", "permno": 1}]),
            _source_frame([{"date": "2020-01-31", "permno": 3}]),
        ],
    )

    result = crsp.load_crsp_data(
        _Database(), [1, 2, 3, 1], "2020-01", "2020-01", chunk_size=2,
        identifier_type="permno",
    )

    assert len(calls) == 2
    assert [call["params"][2:] for call in calls] == [[1, 2], [3]]
    assert list(result["permno"]) == [1, 3]


def test_empty_result_has_the_same_public_schema(monkeypatch):
    _capture_queries(monkeypatch, [_source_frame([])])

    result = crsp.load_crsp_data(
        _Database(), [14593], "2020-01", "2020-01", identifier_type="permno"
    )

    assert list(result.columns) == _RESULT_COLUMNS
    assert isinstance(result.index, pd.PeriodIndex)
    assert result.index.name == "date"
    assert result.index.freqstr == "M"
    assert result.empty
    assert str(result["permno"].dtype) == "Int64"
    assert str(result["ticker"].dtype) == "string"


def test_duplicate_date_permno_rows_are_rejected(monkeypatch):
    _capture_queries(
        monkeypatch,
        [
            _source_frame(
                [
                    {"date": "2020-01-31", "permno": 14593},
                    {"date": "2020-01-31", "permno": 14593},
                ]
            )
        ],
    )

    with pytest.raises(RuntimeError, match="multiple rows"):
        crsp.load_crsp_data(
            _Database(), [14593], "2020-01", "2020-01", identifier_type="permno"
        )


def test_load_all_monthly_data_screens_on_prior_month_observations(monkeypatch):
    calls = _capture_queries(
        monkeypatch,
        [_source_frame([{"date": "2009-03-31", "permno": 14593}])],
    )

    result = crsp.load_all_crsp_data(
        _Database(),
        "2009-03",
        "2009-03",
        share_codes=(10, 11),
        market_cap_min=1_000_000,
        market_cap_max=2_000_000_000,
        price_min=5,
        price_max=500,
    )

    sql = calls[0]["sql"]
    params = calls[0]["params"]
    assert "FROM crspm.msf a" in sql
    assert "crspm.msenames" in sql
    assert "p.date = (a.date - INTERVAL '1 month')::date" in sql
    assert "a.permno IN" not in sql
    assert "ABS(screen.screen_prc) * screen.screen_shrout * 1000 > %s" in sql
    assert "ABS(screen.screen_prc) * screen.screen_shrout * 1000 < %s" in sql
    assert "ABS(screen.screen_prc) > %s" in sql
    assert "ABS(screen.screen_prc) < %s" in sql
    assert {"2009-03-01", "2009-04-01"}.issubset(_parameter_dates(params))
    assert {10, 11, 1_000_000.0, 2_000_000_000.0, 5.0, 500.0}.issubset(
        set(_values(params))
    )
    assert isinstance(result.index, pd.PeriodIndex)
    assert list(result.index) == [pd.Period("2009-03", freq="M")]


def test_load_all_daily_data_returns_datetime_index(monkeypatch):
    calls = _capture_queries(
        monkeypatch,
        [_source_frame([{"date": "2009-03-03", "permno": 14593}])],
    )

    result = crsp.load_all_crsp_data(
        _Database(), "2009-03-03", "2009-03-03", frequency="daily"
    )

    sql = calls[0]["sql"]
    assert "FROM crsp.dsf a" in sql
    assert "crsp.dsenames" in sql
    assert "LATERAL" not in sql
    assert {"2009-03-03", "2009-03-04"}.issubset(
        _parameter_dates(calls[0]["params"])
    )
    assert isinstance(result.index, pd.DatetimeIndex)
    assert result.index[0] == pd.Timestamp("2009-03-03")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"frequency": "weekly"},
        {"price_min": 10, "price_max": 10},
        {"market_cap_min": -1},
        {"share_codes": []},
    ],
)
def test_load_all_rejects_invalid_screen_arguments(kwargs):
    with pytest.raises(ValueError):
        crsp.load_all_crsp_data(
            _Database(), "2020-01", "2020-02", **kwargs
        )
