import numpy as np
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

