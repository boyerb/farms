import numpy as np
import pandas as pd
import pytest

import farms as fm


@pytest.fixture
def portfolio_inputs():
    expected_returns = np.array([0.05, 0.08, 0.11])
    covariance_matrix = np.array(
        [
            [0.04, 0.01, 0.00],
            [0.01, 0.05, 0.01],
            [0.00, 0.01, 0.06],
        ]
    )
    return expected_returns, covariance_matrix


def test_efrs_portfolio_returns_the_unconstrained_kkt_solution(portfolio_inputs):
    expected_returns, covariance_matrix = portfolio_inputs

    weights, expected_return, volatility = fm.EFRS_portfolio(
        0.08, expected_returns, covariance_matrix
    )

    np.testing.assert_allclose(weights, [0.36363636, 0.27272727, 0.36363636])
    assert weights.sum() == pytest.approx(1.0)
    assert expected_return == pytest.approx(0.08)
    assert volatility == pytest.approx(np.sqrt(weights @ covariance_matrix @ weights))


def test_efrs_portfolio_supports_long_only_bounds(portfolio_inputs):
    expected_returns, covariance_matrix = portfolio_inputs

    weights, expected_return, _ = fm.efrs_portfolio(
        0.10,
        expected_returns,
        covariance_matrix,
        allow_short=False,
    )

    assert np.all(weights >= -1e-8)
    assert weights.sum() == pytest.approx(1.0)
    assert expected_return == pytest.approx(0.10)


def test_efrs_portfolio_can_return_diagnostics(portfolio_inputs):
    expected_returns, covariance_matrix = portfolio_inputs

    result = fm.efrs_portfolio(
        0.08,
        expected_returns,
        covariance_matrix,
        return_result=True,
    )

    assert isinstance(result, fm.PortfolioResult)
    assert result.solver == "kkt"
    assert result.variance == pytest.approx(result.volatility**2)
    assert result.as_tuple()[1:] == pytest.approx((0.08, result.volatility))


def test_efrs_portfolio_rejects_infeasible_constant_return_target(portfolio_inputs):
    _, covariance_matrix = portfolio_inputs

    with pytest.raises(ValueError, match="target_return is infeasible"):
        fm.efrs_portfolio(0.08, np.array([0.05, 0.05, 0.05]), covariance_matrix)


@pytest.mark.parametrize(
    "expected_returns, covariance_matrix",
    [
        (np.array([0.05, np.nan, 0.11]), np.eye(3)),
        (np.array([0.05, 0.08, 0.11]), np.array([[1.0, 2.0], [2.0, 1.0]])),
    ],
)
def test_efrs_portfolio_rejects_invalid_inputs(expected_returns, covariance_matrix):
    with pytest.raises(ValueError):
        fm.efrs_portfolio(0.08, expected_returns, covariance_matrix)


def test_efrs_portfolio_rejects_infeasible_long_only_target(portfolio_inputs):
    expected_returns, covariance_matrix = portfolio_inputs

    with pytest.raises(ValueError, match="constraints are infeasible"):
        fm.efrs_portfolio(
            0.20,
            expected_returns,
            covariance_matrix,
            allow_short=False,
        )


def test_efrs_portfolio_supports_global_bounds_and_gross_exposure(portfolio_inputs):
    expected_returns, covariance_matrix = portfolio_inputs

    weights, _, _ = fm.efrs_portfolio(
        0.08,
        expected_returns,
        covariance_matrix,
        bounds=(-1.0, 1.0),
        max_gross_exposure=1.5,
    )

    assert np.all(weights <= 1.0 + 1e-8)
    assert np.all(weights >= -1.0 - 1e-8)
    assert np.abs(weights).sum() <= 1.5 + 1e-7


def test_tangent_portfolio_returns_fully_invested_exposures(portfolio_inputs):
    expected_returns, covariance_matrix = portfolio_inputs

    exposures, expected_return, volatility = fm.tangent_portfolio(
        expected_returns,
        covariance_matrix,
        rf=0.02,
    )

    assert exposures.shape == expected_returns.shape
    assert exposures.sum() == pytest.approx(1.0)
    assert expected_return == pytest.approx(exposures @ expected_returns)
    assert volatility == pytest.approx(
        np.sqrt(exposures @ covariance_matrix @ exposures)
    )


def test_tangent_portfolio_supports_long_only_bounds(portfolio_inputs):
    expected_returns, covariance_matrix = portfolio_inputs

    exposures, _, _ = fm.tangent_portfolio(
        expected_returns,
        covariance_matrix,
        rf=0.02,
        allow_short=False,
    )

    assert np.all(exposures >= -1e-8)
    assert exposures.sum() == pytest.approx(1.0)


def test_factor_tilt_portfolio_returns_base_and_factor_exposures():
    expected_returns = np.array([0.08, 0.02, 0.03, 0.01])
    covariance_matrix = np.array(
        [
            [0.04, 0.00, 0.00, 0.00],
            [0.00, 0.02, 0.00, 0.00],
            [0.00, 0.00, 0.03, 0.00],
            [0.00, 0.00, 0.00, 0.01],
        ]
    )

    exposures, expected_return, volatility = fm.factor_tilt_portfolio(
        expected_returns,
        covariance_matrix,
        rf=0.03,
    )

    assert exposures[0] == pytest.approx(1.0)
    assert exposures.shape == expected_returns.shape
    assert expected_return == pytest.approx(exposures @ expected_returns)
    assert volatility == pytest.approx(
        np.sqrt(exposures @ covariance_matrix @ exposures)
    )


def test_factor_tilt_portfolio_supports_a_nonzero_base_index():
    expected_returns = np.array([0.02, 0.08, 0.03])
    covariance_matrix = np.diag([0.02, 0.04, 0.03])

    exposures, _, _ = fm.factor_tilt_portfolio(
        expected_returns,
        covariance_matrix,
        rf=0.01,
        base_index=1,
    )

    assert exposures[1] == pytest.approx(1.0)


def test_historical_factor_tilt_portfolio_estimates_inputs_and_returns_diagnostics():
    returns = pd.DataFrame(
        {
            "base": [0.010, 0.020, 0.030, 0.000, 0.040, 0.015],
            "tilt": [0.020, 0.010, 0.040, 0.030, 0.000, 0.025],
        }
    )

    result = fm.historical_factor_tilt_portfolio(
        returns,
        base_column="base",
        tilt_bounds=(0.0, 0.0),
        return_result=True,
    )

    assert isinstance(result, fm.HistoricalFactorTiltResult)
    np.testing.assert_allclose(result.weights, [1.0, 0.0])
    np.testing.assert_allclose(result.mean_excess_returns, returns.mean().to_numpy())
    np.testing.assert_allclose(result.covariance_matrix, returns.cov().to_numpy())
    assert result.observations == len(returns)
    assert result.base_column == "base"
    assert result.sharpe == pytest.approx(result.expected_return / result.volatility)
    assert result.as_tuple()[1:] == pytest.approx(
        (result.expected_return, result.volatility)
    )


def test_historical_factor_tilt_portfolio_drops_invalid_rows_and_uses_default_base():
    returns = np.array(
        [
            [0.010, 0.020],
            [0.020, 0.010],
            [np.nan, 0.040],
            [0.000, 0.030],
            [0.040, 0.000],
            [0.015, 0.025],
        ]
    )

    result = fm.historical_factor_tilt_portfolio(
        returns,
        tilt_bounds=(0.0, 0.0),
        return_result=True,
    )

    assert result.weights[0] == pytest.approx(1.0)
    assert result.observations == 5
    assert result.base_column == 0


def test_historical_factor_tilt_portfolio_can_reject_invalid_rows():
    with pytest.raises(ValueError, match="missing or non-finite"):
        fm.historical_factor_tilt_portfolio(
            np.array([[0.01, 0.02], [np.nan, 0.03]]),
            missing="raise",
        )


@pytest.mark.parametrize(
    "function, kwargs",
    [
        (fm.tangent_portfolio, {}),
        (fm.factor_tilt_portfolio, {}),
    ],
)
def test_sharpe_portfolio_functions_reject_singular_covariance(function, kwargs):
    with pytest.raises(ValueError, match="positive definite"):
        function(
            np.array([0.05, 0.08]),
            np.zeros((2, 2)),
            rf=0.02,
            **kwargs,
        )

