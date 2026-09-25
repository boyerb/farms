import numpy as np
import pandas as pd
import pytest

import farms as fm


def test_summary_stats_annualizes_monthly_returns_and_excess_returns():
    returns = pd.DataFrame(
        {
            "Portfolio A": [0.01, 0.03, 0.02],
            "Portfolio B": [0.00, 0.02, 0.04],
        },
        index=pd.period_range("2024-01", periods=3, freq="M"),
    )
    risk_free = pd.Series(0.005, index=returns.index, name="rf")

    result = fm.summary_stats(returns, risk_free=risk_free, frequency="monthly")

    assert list(result.columns) == [
        "Observations",
        "Annualized arithmetic mean",
        "Annualized volatility",
        "Annualized excess mean",
        "Annualized Sharpe ratio",
    ]
    assert result.loc["Portfolio A", "Observations"] == 3
    assert result.loc["Portfolio A", "Annualized arithmetic mean"] == pytest.approx(0.24)
    assert result.loc["Portfolio A", "Annualized excess mean"] == pytest.approx(0.18)
    assert result.loc["Portfolio A", "Annualized volatility"] == pytest.approx(
        np.sqrt(12) * returns["Portfolio A"].std()
    )


@pytest.mark.parametrize(
    ("frequency", "periods_per_year"),
    [("daily", 252), ("weekly", 52), ("monthly", 12)],
)
def test_summary_stats_uses_frequency_specific_annualization(frequency, periods_per_year):
    returns = pd.DataFrame({"Portfolio": [0.01, 0.02]})

    result = fm.summary_stats(returns, frequency=frequency)

    assert result.loc["Portfolio", "Annualized arithmetic mean"] == pytest.approx(
        periods_per_year * returns["Portfolio"].mean()
    )
    assert result.loc["Portfolio", "Annualized volatility"] == pytest.approx(
        np.sqrt(periods_per_year) * returns["Portfolio"].std()
    )
    assert "Annualized excess mean" not in result


def test_summary_stats_accepts_a_scalar_risk_free_rate():
    returns = pd.DataFrame({"Portfolio": [0.01, 0.02]})

    result = fm.summary_stats(returns, risk_free=0.005)

    assert result.loc["Portfolio", "Annualized excess mean"] == pytest.approx(0.12)


def test_summary_stats_returns_nan_sharpe_for_zero_volatility():
    returns = pd.DataFrame({"Portfolio": [0.01, 0.01, 0.01]})

    result = fm.summary_stats(returns, risk_free=0.005)

    assert np.isnan(result.loc["Portfolio", "Annualized Sharpe ratio"])


def test_summary_stats_rejects_invalid_frequency_and_non_numeric_columns():
    returns = pd.DataFrame({"Portfolio": [0.01, 0.02]})

    with pytest.raises(ValueError, match="frequency must be one of"):
        fm.summary_stats(returns, frequency="yearly")

    with pytest.raises(TypeError, match="only numeric columns"):
        fm.summary_stats(pd.DataFrame({"Portfolio": ["0.01", "0.02"]}))
