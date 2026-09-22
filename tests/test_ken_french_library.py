"""Unit tests for the Ken French data helpers.

These tests use small, artificial DataFrames instead of downloading live data.
The pytest ``monkeypatch`` fixture temporarily replaces download functions with
local fakes, which keeps the suite fast, repeatable, and usable offline.

Run this file from the repository root with::

    python -m pytest tests/test_ken_french_library.py -v

Useful pytest features demonstrated here:

* ``monkeypatch`` replaces a function only for the duration of one test.
* ``capsys`` captures printed output so that it can be checked.
* ``pytest.approx`` safely compares floating-point values.
* ``pytest.raises`` verifies that invalid input produces a helpful exception.
* ``pytest.mark.parametrize`` runs one test with several inputs.
"""

import pandas as pd
import pytest

from farms.pipelines import Ken_French_library as french


def test_load_french_dataset_forwards_reader_arguments(monkeypatch):
    """The low-level loader should pass its arguments to pandas-datareader."""
    expected = {0: "table", "DESCR": "description"}
    calls = []

    def fake_data_reader(dataset, source, start=None, end=None):
        calls.append((dataset, source, start, end))
        return expected

    monkeypatch.setattr(french.web, "DataReader", fake_data_reader)

    result = french._load_french_dataset(
        "F-F_Research_Data_Factors",
        "2020-01-01",
        "2020-12-31",
    )

    assert result is expected
    assert calls == [
        (
            "F-F_Research_Data_Factors",
            "famafrench",
            "2020-01-01",
            "2020-12-31",
        )
    ]


def test_load_french_dataset_defaults_to_full_history(monkeypatch):
    """An omitted start date should request all available historical data."""
    calls = []

    def fake_data_reader(dataset, source, start=None, end=None):
        calls.append((dataset, source, start, end))
        return {0: pd.DataFrame()}

    monkeypatch.setattr(french.web, "DataReader", fake_data_reader)

    french._load_french_dataset("Example")

    assert calls == [("Example", "famafrench", "1900-01-01", None)]


def test_decile_registry_contains_all_supported_strategies():
    """The registry should contain every public strategy in a uniform format."""
    assert set(french._DECILE_DATASETS) == {
        "accruals",
        "beta",
        "booktomarket",
        "dividendyield",
        "earningsprice",
        "idiosyncraticvariance",
        "investment",
        "momentum",
        "netissuances",
        "profitability",
        "shorttermreversal",
        "size",
        "variance",
    }
    assert all(
        {"dataset", "title", "table", "frequencies"}.issubset(config)
        for config in french._DECILE_DATASETS.values()
    )
    assert all(
        config["table"] == 0 for config in french._DECILE_DATASETS.values()
    )
    assert set(french._QUINTILE_DATASETS) == {
        strategy
        for strategy, config in french._DECILE_DATASETS.items()
        if "quintiles" in config["frequencies"]["monthly"]["granularities"]
    }
    assert set(french._DECILE_DATASETS["momentum"]["frequencies"]) == {
        "monthly",
        "daily",
    }
    assert "daily" not in french._DECILE_DATASETS["accruals"]["frequencies"]


def test_inspect_french_dataset_summarizes_dataframes(monkeypatch):
    """Dataset inspection should describe every returned DataFrame table."""
    monthly = pd.DataFrame(
        {"Lo 10": [1.0], "Hi 10": [2.0]},
        index=pd.period_range("2020-01", periods=1, freq="M"),
    )
    annual = pd.DataFrame(
        {"Lo 10": [3.0], "Hi 10": [4.0]},
        index=pd.period_range("2020", periods=1, freq="Y"),
    )
    monkeypatch.setattr(
        french,
        "_load_french_dataset",
        lambda dataset, start_date=None, end_date=None: {
            0: monthly,
            1: annual,
            "DESCR": "Example description",
        },
    )

    result = french._inspect_french_dataset("Example", "2020", "2021")

    assert result["dataset"] == "Example"
    assert result["description"] == "Example description"
    assert result["tables"] == {
        0: {
            "rows": 1,
            "columns": ["Lo 10", "Hi 10"],
            "index_type": "PeriodIndex",
            "index_frequency": "M",
        },
        1: {
            "rows": 1,
            "columns": ["Lo 10", "Hi 10"],
            "index_type": "PeriodIndex",
            "index_frequency": "Y-DEC",
        },
    }


@pytest.mark.parametrize("strategy", sorted(french._DECILE_DATASETS))
def test_load_decile_returns_normalizes_registered_strategy(monkeypatch, strategy):
    """Each strategy should produce ten consistently named decimal returns."""
    prefix_columns = {
        "Lo 20": [90.0, 91.0],
        "Qnt 2": [92.0, 93.0],
    }
    decile_columns = {
        "Lo 10": [1.0, 11.0],
        **{f"Dec {number}": [float(number), float(number + 10)] for number in range(2, 10)},
        "Hi 10": [10.0, 20.0],
    }
    source = pd.DataFrame(
        prefix_columns | decile_columns | {"not a decile": [99.0, 99.0]},
        index=pd.period_range("2020-01", "2020-02", freq="M"),
    )
    calls = []

    def fake_loader(dataset, start_date=None, end_date=None):
        calls.append((dataset, start_date, end_date))
        return {0: source}

    monkeypatch.setattr(french, "_load_french_dataset", fake_loader)

    result = french._load_decile_returns(strategy, "2020-01", "2020-02")

    config = french._DECILE_DATASETS[strategy]
    assert calls == [(config["dataset"], "2020-01", "2020-02")]
    assert list(result.columns) == [f"Dec {number}" for number in range(1, 11)]
    assert result.index.name == "date"
    assert result.iloc[0]["Dec 1"] == pytest.approx(0.01)
    assert result.iloc[0]["Dec 10"] == pytest.approx(0.10)
    assert result.iloc[1]["Dec 1"] == pytest.approx(0.11)


def test_load_decile_returns_rejects_unknown_strategy():
    """The internal loader should explain when a strategy is unsupported."""
    with pytest.raises(ValueError, match="Unknown decile strategy 'unknown'"):
        french._load_decile_returns("unknown")


def test_load_decile_returns_accepts_live_hyphenated_column_names(monkeypatch):
    source = pd.DataFrame(
        {
            "Lo 10": [1.0],
            **{f"{number}-Dec": [float(number)] for number in range(2, 10)},
            "Hi 10": [10.0],
        },
        index=pd.period_range("2020-01", periods=1, freq="M"),
    )
    monkeypatch.setattr(
        french,
        "_load_french_dataset",
        lambda dataset, start_date=None, end_date=None: {0: source},
    )

    result = french._load_decile_returns("momentum")

    assert list(result.columns) == [f"Dec {i}" for i in range(1, 11)]
    assert result.iloc[0]["Dec 2"] == pytest.approx(0.02)


def test_load_decile_returns_accepts_prior_column_names(monkeypatch):
    source = pd.DataFrame(
        {
            "Lo PRIOR": [1.0],
            **{f"PRIOR {number}": [float(number)] for number in range(2, 10)},
            "Hi PRIOR": [10.0],
        },
        index=pd.period_range("2020-01", periods=1, freq="M"),
    )
    monkeypatch.setattr(
        french,
        "_load_french_dataset",
        lambda dataset, start_date=None, end_date=None: {0: source},
    )

    result = french._load_decile_returns("momentum")

    assert list(result.columns) == [f"Dec {i}" for i in range(1, 11)]
    assert result.iloc[0]["Dec 10"] == pytest.approx(0.10)


def test_get_ff3_returns_monthly_decimal_factors(monkeypatch):
    """FF3 should return monthly factors converted from percentages to decimals."""
    source = pd.DataFrame(
        {
            "Mkt-RF": [2.00, -1.00],
            "SMB": [1.00, 0.50],
            "HML": [-0.50, 0.25],
            "RF": [0.10, 0.10],
        },
        index=pd.period_range("2020-01", "2020-02", freq="M"),
    )
    calls = []

    def fake_loader(dataset, start_date=None, end_date=None):
        calls.append((dataset, start_date, end_date))
        return {0: source, "DESCR": "Monthly Fama-French factors"}

    monkeypatch.setattr(french, "_load_french_dataset", fake_loader)

    result = french.get_ff3("2020-01", "2020-02")

    assert calls == [("F-F_Research_Data_Factors", "2020-01", "2020-02")]
    assert list(result.columns) == ["Mkt-RF", "SMB", "HML", "RF"]
    assert isinstance(result.index, pd.PeriodIndex)
    assert result.index.freqstr == "M"
    assert result.index.name == "date"
    assert result.loc[pd.Period("2020-01", freq="M"), "Mkt-RF"] == pytest.approx(0.02)
    assert result.loc[pd.Period("2020-02", freq="M"), "HML"] == pytest.approx(0.0025)


def test_get_ff5_filters_dates_and_returns_decimal_factors(monkeypatch):
    """FF5 should request the selected dates and return decimal factor values."""
    source = pd.DataFrame(
        {
            "Mkt-RF": [-1.00],
            "SMB": [0.50],
            "HML": [0.25],
            "RMW": [-0.10],
            "CMA": [0.30],
            "RF": [0.10],
        },
        index=pd.period_range("2020-02", "2020-02", freq="M"),
    )
    calls = []

    def fake_loader(dataset, start_date=None, end_date=None):
        calls.append((dataset, start_date, end_date))
        return {0: source}

    monkeypatch.setattr(french, "_load_french_dataset", fake_loader)

    result = french.get_ff5("2020-02", "2020-02")

    assert calls == [
        ("F-F_Research_Data_5_Factors_2x3", "2020-02", "2020-02")
    ]
    assert list(result.columns) == ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]
    assert list(result.index) == [pd.Period("2020-02", freq="M")]
    assert result.iloc[0]["Mkt-RF"] == pytest.approx(-0.01)
    assert result.iloc[0]["CMA"] == pytest.approx(0.003)


def test_get_ff3d_returns_filtered_daily_decimal_factors(monkeypatch):
    """Daily FF3 data should use calendar timestamps and decimal values."""
    source = pd.DataFrame(
        {
            "Mkt-RF": [-2.00],
            "SMB": [0.25],
            "HML": [0.50],
            "RF": [0.01],
        },
        index=pd.period_range("2020-01-03", "2020-01-03", freq="D"),
    )
    calls = []

    def fake_loader(dataset, start_date=None, end_date=None):
        calls.append((dataset, start_date, end_date))
        return {0: source}

    monkeypatch.setattr(french, "_load_french_dataset", fake_loader)

    result = french.get_ff3d("2020-01-03", "2020-01-03")

    assert calls == [
        ("F-F_Research_Data_Factors_daily", "2020-01-03", "2020-01-03")
    ]
    assert list(result.columns) == ["Mkt-RF", "SMB", "HML", "RF"]
    assert isinstance(result.index, pd.DatetimeIndex)
    assert result.index.freq is None
    assert result.index.name == "date"
    assert list(result.index) == [pd.Timestamp("2020-01-03")]
    assert result.iloc[0]["Mkt-RF"] == pytest.approx(-0.02)
    assert result.iloc[0]["RF"] == pytest.approx(0.0001)


def test_get_ff5d_returns_filtered_daily_decimal_factors(monkeypatch):
    """Daily FF5 data should use calendar timestamps and decimal values."""
    source = pd.DataFrame(
        {
            "Mkt-RF": [-2.00],
            "SMB": [0.25],
            "HML": [0.50],
            "RMW": [-0.10],
            "CMA": [0.30],
            "RF": [0.01],
        },
        index=pd.period_range("2020-01-03", "2020-01-03", freq="D"),
    )
    calls = []

    def fake_loader(dataset, start_date=None, end_date=None):
        calls.append((dataset, start_date, end_date))
        return {0: source}

    monkeypatch.setattr(french, "_load_french_dataset", fake_loader)

    result = french.get_ff5d("2020-01-03", "2020-01-03")

    assert calls == [
        ("F-F_Research_Data_5_Factors_2x3_daily", "2020-01-03", "2020-01-03")
    ]
    assert list(result.columns) == ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]
    assert isinstance(result.index, pd.DatetimeIndex)
    assert result.index.freq is None
    assert result.index.name == "date"
    assert list(result.index) == [pd.Timestamp("2020-01-03")]
    assert result.iloc[0]["Mkt-RF"] == pytest.approx(-0.02)
    assert result.iloc[0]["RMW"] == pytest.approx(-0.001)
    assert result.iloc[0]["CMA"] == pytest.approx(0.003)
    assert result.iloc[0]["RF"] == pytest.approx(0.0001)


def test_get_ff3_weekly_returns_period_index_and_decimal_factors(monkeypatch):
    """Weekly FF3 should use the published weekly source dataset."""
    source = pd.DataFrame(
        {
            "Mkt-RF": [2.00],
            "SMB": [0.25],
            "HML": [0.50],
            "RF": [0.01],
        },
        index=pd.period_range("2020-01-03", periods=1, freq="W-FRI"),
    )
    calls = []

    def fake_loader(dataset, start_date=None, end_date=None):
        calls.append((dataset, start_date, end_date))
        return {0: source}

    monkeypatch.setattr(french, "_load_french_dataset", fake_loader)

    result = french.load_ken_french_data(
        "ff3",
        frequency="weekly",
        start_date="2020-01-01",
        end_date="2020-01-31",
    )

    assert calls == [
        ("F-F_Research_Data_Factors_weekly", "2020-01-01", "2020-01-31")
    ]
    assert isinstance(result.index, pd.PeriodIndex)
    assert result.index.freqstr == "W-FRI"
    assert result.iloc[0]["Mkt-RF"] == pytest.approx(0.02)
    assert result.iloc[0]["RF"] == pytest.approx(0.0001)


def test_unified_loader_dispatches_factor_data(monkeypatch):
    source = pd.DataFrame(
        {
            "Mkt-RF": [2.00],
            "SMB": [1.00],
            "HML": [-0.50],
            "RF": [0.10],
        },
        index=pd.period_range("2020-01", periods=1, freq="M"),
    )
    calls = []

    def fake_loader(dataset, start_date=None, end_date=None):
        calls.append((dataset, start_date, end_date))
        return {0: source}

    monkeypatch.setattr(french, "_load_french_dataset", fake_loader)

    result = french.load_ken_french_data(
        "ff3",
        start_date="2020-01",
        end_date="2020-01",
    )

    assert calls == [
        ("F-F_Research_Data_Factors", "2020-01", "2020-01")
    ]
    assert list(result.columns) == ["Mkt-RF", "SMB", "HML", "RF"]
    assert result.iloc[0]["Mkt-RF"] == pytest.approx(0.02)


def test_unified_loader_accepts_legacy_daily_factor_alias(monkeypatch):
    source = pd.DataFrame(
        {
            "Mkt-RF": [2.00],
            "SMB": [1.00],
            "HML": [-0.50],
            "RF": [0.10],
        },
        index=pd.period_range("2020-01-03", periods=1, freq="D"),
    )
    calls = []

    def fake_loader(dataset, start_date=None, end_date=None):
        calls.append((dataset, start_date, end_date))
        return {0: source}

    monkeypatch.setattr(french, "_load_french_dataset", fake_loader)

    result = french.load_ken_french_data("ff3d")

    assert calls == [("F-F_Research_Data_Factors_daily", None, None)]
    assert isinstance(result.index, pd.DatetimeIndex)


def test_unified_loader_rejects_weekly_ff5():
    with pytest.raises(ValueError, match="Weekly FF5 data are not published"):
        french.load_ken_french_data("ff5", frequency="weekly")


def test_unified_loader_loads_daily_momentum_deciles(monkeypatch):
    source = pd.DataFrame(
        {
            "Lo PRIOR": [1.0],
            **{f"PRIOR {number}": [float(number)] for number in range(2, 10)},
            "Hi PRIOR": [10.0],
        },
        index=pd.period_range("2020-01-03", periods=1, freq="D"),
    )
    calls = []

    def fake_loader(dataset, start_date=None, end_date=None):
        calls.append((dataset, start_date, end_date))
        return {0: source}

    monkeypatch.setattr(french, "_load_french_dataset", fake_loader)

    result = french.load_ken_french_data(
        "deciles",
        strategy="momentum",
        frequency="daily",
        portfolio=[1, 10],
        start_date="2020-01-03",
        end_date="2020-01-03",
    )

    assert calls == [
        ("10_Portfolios_Prior_12_2_Daily", "2020-01-03", "2020-01-03")
    ]
    assert list(result.columns) == ["Dec 1", "Dec 10"]
    assert isinstance(result.index, pd.DatetimeIndex)
    assert result.iloc[0]["Dec 1"] == pytest.approx(0.01)
    assert result.iloc[0]["Dec 10"] == pytest.approx(0.10)


def test_unified_loader_rejects_daily_quintiles_without_true_source():
    with pytest.raises(ValueError, match="does not provide true quintiles"):
        french.load_ken_french_data(
            "quintiles",
            strategy="size",
            frequency="daily",
        )


def test_unified_loader_rejects_weekly_registered_strategy():
    with pytest.raises(ValueError, match="does not provide 'weekly' data"):
        french.load_ken_french_data(
            "deciles",
            strategy="momentum",
            frequency="weekly",
        )


def test_unified_loader_selects_portfolios_without_adding_factors(monkeypatch):
    monkeypatch.setattr(
        french,
        "_load_decile_returns",
        lambda strategy, start_date=None, end_date=None: _sample_deciles(),
    )

    result = french.load_ken_french_data(
        "deciles",
        strategy="momentum",
        portfolio=[1, 10],
    )

    assert list(result.columns) == ["Dec 1", "Dec 10"]
    assert result.iloc[0]["Dec 1"] == pytest.approx(-0.02)
    assert result.iloc[0]["Dec 10"] == pytest.approx(0.07)


def test_unified_loader_can_merge_requested_factors(monkeypatch):
    monkeypatch.setattr(
        french,
        "_load_decile_returns",
        lambda strategy, start_date=None, end_date=None: _sample_deciles(),
    )
    monkeypatch.setattr(french, "get_ff3", _sample_ff3)

    result = french.load_ken_french_data(
        "deciles",
        strategy="momentum",
        portfolio="high",
        include_factors="ff3",
    )

    assert list(result.columns) == [
        "Dec 10",
        "mkt-rf",
        "smb",
        "hml",
        "rf",
    ]
    assert result.iloc[0]["Dec 10"] == pytest.approx(0.07)
    assert result.iloc[0]["mkt-rf"] == pytest.approx(-0.01)


def test_unified_loader_supports_quintile_portfolios(monkeypatch):
    source = pd.DataFrame(
        {
            "Lo 20": [1.0],
            "Qnt 2": [2.0],
            "Qnt 3": [3.0],
            "Qnt 4": [4.0],
            "Hi 20": [5.0],
        },
        index=pd.period_range("2020-01", periods=1, freq="M"),
    )
    monkeypatch.setattr(
        french,
        "_load_french_dataset",
        lambda dataset, start_date=None, end_date=None: {0: source},
    )

    result = french.load_ken_french_data(
        "quintiles",
        strategy="size",
        portfolio="high",
    )

    assert list(result.columns) == ["Qnt 5"]
    assert result.iloc[0]["Qnt 5"] == pytest.approx(0.05)


def _sample_deciles():
    """Create one month of predictable decile returns for public-API tests."""
    return pd.DataFrame(
        {
            f"Dec {number}": [-0.02 + (number - 1) * 0.01]
            for number in range(1, 11)
        },
        index=pd.period_range("2020-02", periods=1, freq="M", name="date"),
    )


def _sample_ff3(start_date=None, end_date=None):
    """Create one month of predictable FF3 returns for merge tests."""
    return pd.DataFrame(
        {
            "Mkt-RF": [-0.01],
            "SMB": [0.005],
            "HML": [0.0025],
            "RF": [0.001],
        },
        index=pd.period_range("2020-02", periods=1, freq="M", name="date"),
    )


def _sample_ff5(start_date=None, end_date=None):
    """Create one month of predictable FF5 returns for merge tests."""
    result = _sample_ff3()
    result["RMW"] = -0.001
    result["CMA"] = 0.003
    return result[["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]]


@pytest.mark.parametrize("strategy", sorted(french._DECILE_DATASETS))
def test_public_decile_loader_supports_every_strategy(monkeypatch, strategy):
    """The public loader should accept every strategy registered by the package."""
    calls = []
    deciles = _sample_deciles()

    def fake_decile_loader(stype, start_date=None, end_date=None):
        calls.append((stype, start_date, end_date))
        return deciles

    monkeypatch.setattr(french, "_load_decile_returns", fake_decile_loader)
    monkeypatch.setattr(french, "get_ff3", _sample_ff3)

    result = french.get_ken_french_deciles(
        strategy,
        start_date="2020-02",
        end_date="2020-02",
    )

    assert calls == [(strategy, "2020-02", "2020-02")]
    assert list(result.columns) == [
        *[f"Dec {number}" for number in range(1, 11)],
        "mkt-rf",
        "rf",
    ]


@pytest.mark.parametrize(
    ("factors", "expected_columns"),
    [
        (None, ["mkt-rf", "rf"]),
        ("FF3", ["mkt-rf", "smb", "hml", "rf"]),
        ("FF5", ["mkt-rf", "smb", "hml", "rmw", "cma", "rf"]),
    ],
)
def test_public_decile_loader_merges_requested_factors(
    monkeypatch, factors, expected_columns
):
    """The public loader should merge the default, FF3, or FF5 factor set."""
    monkeypatch.setattr(
        french,
        "_load_decile_returns",
        lambda strategy, start_date=None, end_date=None: _sample_deciles(),
    )
    monkeypatch.setattr(french, "get_ff3", _sample_ff3)
    monkeypatch.setattr(french, "get_ff5", _sample_ff5)

    result = french.get_ken_french_deciles("momentum", factors=factors)

    assert list(result.columns) == [
        *[f"Dec {number}" for number in range(1, 11)],
        *expected_columns,
    ]
    assert result.iloc[0]["Dec 1"] == pytest.approx(-0.02)
    assert result.iloc[0]["Dec 10"] == pytest.approx(0.07)
    assert result.iloc[0]["mkt-rf"] == pytest.approx(-0.01)


@pytest.mark.parametrize("factors", [None, "FF3", "FF5"])
def test_public_decile_loader_forwards_dates_to_factor_loader(monkeypatch, factors):
    calls = []
    monkeypatch.setattr(
        french,
        "_load_decile_returns",
        lambda strategy, start_date=None, end_date=None: _sample_deciles(),
    )

    def fake_ff3(start_date=None, end_date=None):
        calls.append(("FF3", start_date, end_date))
        return _sample_ff3()

    def fake_ff5(start_date=None, end_date=None):
        calls.append(("FF5", start_date, end_date))
        return _sample_ff5()

    monkeypatch.setattr(french, "get_ff3", fake_ff3)
    monkeypatch.setattr(french, "get_ff5", fake_ff5)

    french.get_ken_french_deciles(
        "momentum", "2020-01", "2020-02", factors=factors
    )

    expected_loader = "FF5" if factors == "FF5" else "FF3"
    assert calls == [(expected_loader, "2020-01", "2020-02")]


def test_public_decile_loader_rejects_invalid_factor_selection(monkeypatch):
    monkeypatch.setattr(
        french,
        "_load_decile_returns",
        lambda strategy, start_date=None, end_date=None: _sample_deciles(),
    )

    with pytest.raises(ValueError, match="factors must be None, 'FF3', or 'FF5'"):
        french.get_ken_french_deciles("momentum", factors="FF4")


def test_public_decile_loader_lists_strategies_without_downloading(capsys):
    """The special ``list`` request should print choices without loading data."""
    result = french.get_ken_french_deciles("list")

    assert result is None
    assert capsys.readouterr().out.splitlines() == list(french._DECILE_DATASETS)


def test_public_decile_loader_prints_teaching_details(monkeypatch, capsys):
    """The details option should print the strategy's teaching notes and dates."""
    monkeypatch.setattr(
        french,
        "_load_decile_returns",
        lambda strategy, start_date=None, end_date=None: _sample_deciles(),
    )
    monkeypatch.setattr(french, "get_ff3", _sample_ff3)

    french.get_ken_french_deciles("momentum", details=True)

    output = capsys.readouterr().out
    assert "Momentum" in output
    assert "prior returns from months t-12 through t-2" in output
    assert "Min Date: 2020-02, Max Date: 2020-02" in output


def test_get_decile_metadata_returns_structured_information():
    """Metadata should be returned in a predictable, reusable dictionary."""
    metadata = french._get_decile_metadata("momentum", _sample_deciles())

    assert metadata == {
        "strategy": "momentum",
        "title": "Momentum",
        "dataset": "10_Portfolios_Prior_12_2",
        "table": 0,
        "description": list(french._DECILE_DETAILS["momentum"]),
        "min_date": pd.Period("2020-02", freq="M"),
        "max_date": pd.Period("2020-02", freq="M"),
    }


def test_print_decile_details_displays_structured_metadata(capsys):
    """The display helper should print structured metadata for a student."""
    metadata = french._get_decile_metadata("momentum", _sample_deciles())

    result = french._print_decile_details(metadata)

    assert result is None
    output = capsys.readouterr().out
    assert "Momentum" in output
    assert "prior returns from months t-12 through t-2" in output
    assert "Min Date: 2020-02, Max Date: 2020-02" in output


def test_public_decile_loader_rejects_unknown_strategy():
    """The public loader should report unsupported strategies clearly."""
    with pytest.raises(ValueError, match="Unknown decile strategy 'unknown'"):
        french.get_ken_french_deciles("unknown")
