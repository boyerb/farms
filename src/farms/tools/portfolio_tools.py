from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.linalg import solve
from scipy.optimize import linprog, minimize


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class PortfolioResult:
    """Result returned by :func:`efrs_portfolio` when requested."""

    weights: FloatArray
    expected_return: float
    volatility: float
    variance: float
    solver: str
    message: str

    def as_tuple(self) -> tuple[FloatArray, float, float]:
        """Return the legacy ``(weights, expected_return, volatility)`` form."""
        return self.weights, self.expected_return, self.volatility

def describe(name, series):
    std = np.std(series)         # Compute the standard deviation (volatility)
    mean = np.mean(series)       # Compute the mean (average return)
    # Print formatted output with consistent spacing and precision
    print(f"{name:20s} |  Mean: {mean:.4f} | Std Dev: {std:.6f}")


def portfolio_volatility(weights, covariance_matrix):
    return np.sqrt(weights.T @ covariance_matrix @ weights)  # Essential Math Fact #5


def _prepare_portfolio_inputs(
    expected_returns: ArrayLike,
    covariance_matrix: ArrayLike,
    *,
    covariance_tolerance: float,
    regularization: float,
) -> tuple[FloatArray, FloatArray]:
    """Convert and validate the inputs used by the frontier solver."""
    if not np.isscalar(covariance_tolerance) or not np.isfinite(covariance_tolerance):
        raise ValueError("covariance_tolerance must be a finite scalar")
    if covariance_tolerance <= 0:
        raise ValueError("covariance_tolerance must be positive")
    if not np.isscalar(regularization) or not np.isfinite(regularization):
        raise ValueError("regularization must be a finite scalar")
    if regularization < 0:
        raise ValueError("regularization must be nonnegative")

    try:
        mu = np.asarray(expected_returns, dtype=float)
        sigma = np.asarray(covariance_matrix, dtype=float)
    except (TypeError, ValueError) as exc:
        raise TypeError("expected_returns and covariance_matrix must be numeric") from exc

    if mu.ndim != 1 or mu.size == 0:
        raise ValueError("expected_returns must be a non-empty one-dimensional vector")
    if sigma.ndim != 2 or sigma.shape != (mu.size, mu.size):
        raise ValueError(
            "covariance_matrix must be a square matrix with one row and column per asset"
        )
    if not np.all(np.isfinite(mu)) or not np.all(np.isfinite(sigma)):
        raise ValueError("expected_returns and covariance_matrix must contain only finite values")

    if not np.allclose(
        sigma,
        sigma.T,
        rtol=covariance_tolerance,
        atol=covariance_tolerance,
    ):
        raise ValueError("covariance_matrix must be symmetric")
    sigma = (sigma + sigma.T) / 2.0

    if regularization:
        sigma = sigma + regularization * np.eye(mu.size)

    scale = max(float(np.max(np.abs(sigma))), np.finfo(float).eps)
    eigenvalues = np.linalg.eigvalsh(sigma)
    eigenvalue_tolerance = covariance_tolerance * scale
    minimum_eigenvalue = float(eigenvalues[0])
    if minimum_eigenvalue < -eigenvalue_tolerance:
        raise ValueError("covariance_matrix must be positive semidefinite")
    if minimum_eigenvalue < 0:
        # Remove only a round-off-sized negative eigenvalue.
        sigma = sigma + (-minimum_eigenvalue) * np.eye(mu.size)

    return mu, sigma


def _normalise_bounds(
    bounds: tuple[float | None, float | None] | list[tuple[float | None, float | None]] | None,
    n_assets: int,
    *,
    allow_short: bool,
) -> list[tuple[float | None, float | None]]:
    """Return bounds in the form expected by SciPy."""
    if bounds is None:
        normalised = [(None, None) for _ in range(n_assets)]
    else:
        raw_bounds = list(bounds)
        if len(raw_bounds) == 2 and all(
            item is None or np.isscalar(item) for item in raw_bounds
        ):
            raw_bounds = [tuple(raw_bounds) for _ in range(n_assets)]
        if len(raw_bounds) != n_assets:
            raise ValueError("bounds must contain one (lower, upper) pair per asset")

        normalised = []
        for bound in raw_bounds:
            if bound is None or len(bound) != 2:
                raise ValueError("each bound must be a (lower, upper) pair")
            lower, upper = bound
            lower = None if lower is None else float(lower)
            upper = None if upper is None else float(upper)
            if lower is not None and not np.isfinite(lower):
                raise ValueError("bound values must be finite or None")
            if upper is not None and not np.isfinite(upper):
                raise ValueError("bound values must be finite or None")
            if lower is not None and upper is not None and lower > upper:
                raise ValueError("each lower bound must be less than or equal to its upper bound")
            normalised.append((lower, upper))

    if not allow_short and any(lower is not None and lower < 0 for lower, _ in normalised):
        raise ValueError("allow_short=False cannot be combined with negative lower bounds")
    if not allow_short:
        normalised = [
            (0.0 if lower is None else lower, upper)
            for lower, upper in normalised
        ]
    return normalised


def _feasible_start(
    expected_returns: FloatArray,
    target_return: float,
    bounds: list[tuple[float | None, float | None]],
    *,
    include_target_constraint: bool,
    max_gross_exposure: float | None = None,
) -> FloatArray | None:
    """Find a feasible point for constrained optimization, if one exists."""
    n_assets = expected_returns.size
    variable_count = n_assets
    equality_matrix = [np.ones(n_assets)]
    equality_targets = [1.0]
    if include_target_constraint:
        equality_matrix.append(expected_returns)
        equality_targets.append(target_return)

    if max_gross_exposure is not None:
        # Add nonnegative auxiliary variables t with -t <= w <= t so that
        # sum(t) <= max_gross_exposure represents the gross-exposure limit.
        variable_count = 2 * n_assets
        equality_matrix = [
            np.concatenate([row, np.zeros(n_assets)]) for row in equality_matrix
        ]
        gross_constraints = []
        for asset_index in range(n_assets):
            row = np.zeros(variable_count)
            row[asset_index] = 1.0
            row[n_assets + asset_index] = -1.0
            gross_constraints.append(row)
            gross_constraints.append(-row)
        gross_constraints.append(
            np.concatenate([np.zeros(n_assets), np.ones(n_assets)])
        )
        A_ub = np.vstack(gross_constraints)
        b_ub = np.concatenate(
            [np.zeros(2 * n_assets), [float(max_gross_exposure)]]
        )
        bounds = bounds + [(0.0, None)] * n_assets
    else:
        A_ub = None
        b_ub = None

    result = linprog(
        c=np.zeros(variable_count),
        A_eq=np.vstack(equality_matrix),
        b_eq=np.asarray(equality_targets),
        A_ub=A_ub,
        b_ub=b_ub,
        bounds=bounds,
        method="highs",
    )
    if not result.success:
        return None
    return np.asarray(result.x[:n_assets], dtype=float)


def _solve_kkt(
    covariance_matrix: FloatArray,
    expected_returns: FloatArray,
    target_return: float,
    *,
    include_target_constraint: bool,
) -> FloatArray:
    """Solve the equality-constrained minimum-variance problem."""
    n_assets = expected_returns.size
    constraint_matrix = [np.ones(n_assets)]
    constraint_targets = [1.0]
    if include_target_constraint:
        constraint_matrix.append(expected_returns)
        constraint_targets.append(target_return)

    A = np.column_stack(constraint_matrix)
    KKT = np.block(
        [
            [covariance_matrix, A],
            [A.T, np.zeros((A.shape[1], A.shape[1]))],
        ]
    )
    rhs = np.concatenate([np.zeros(n_assets), np.asarray(constraint_targets)])
    solution = solve(KKT, rhs, assume_a="sym", check_finite=True)
    return np.asarray(solution[:n_assets], dtype=float)


def efrs_portfolio(
    target_return: float,
    expected_returns: ArrayLike,
    covariance_matrix: ArrayLike,
    *,
    bounds: tuple[float | None, float | None]
    | list[tuple[float | None, float | None]]
    | None = None,
    allow_short: bool = True,
    max_gross_exposure: float | None = None,
    initial_weights: ArrayLike | None = None,
    additional_constraints: list[dict] | tuple[dict, ...] | None = None,
    solver: str = "auto",
    tolerance: float = 1e-8,
    maxiter: int = 1_000,
    covariance_tolerance: float = 1e-10,
    regularization: float = 0.0,
    return_result: bool = False,
) -> tuple[FloatArray, float, float] | PortfolioResult:
    """Compute the minimum-variance portfolio for a target expected return.

    The portfolio is fully invested in the supplied assets, so there is no
    separate risk-free allocation. By default, short selling is allowed and
    weights are otherwise unrestricted. Use ``bounds`` or ``allow_short=False``
    to impose investment limits.

    Parameters
    ----------
    target_return:
        Target return on the same time scale as ``expected_returns``.
    expected_returns:
        One-dimensional asset expected-return vector.
    covariance_matrix:
        Symmetric positive-semidefinite covariance matrix.
    bounds:
        Either one global ``(lower, upper)`` pair or one pair per asset.
    allow_short:
        If false, impose nonnegative lower bounds.
    max_gross_exposure:
        Optional upper bound on ``sum(abs(weights))``.
    initial_weights:
        Optional starting point for the numerical solver.
    additional_constraints:
        Additional SciPy-compatible SLSQP constraints. These force the
        constrained numerical solver.
    solver:
        ``"auto"`` uses the KKT solution when possible, ``"kkt"`` requires
        that solution, and ``"slsqp"`` always uses the numerical solver.
    return_result:
        If true, return a :class:`PortfolioResult`; otherwise preserve the
        historical three-value tuple return type.
    """
    if not np.isscalar(target_return) or not np.isfinite(target_return):
        raise ValueError("target_return must be a finite scalar")
    if solver not in {"auto", "kkt", "slsqp"}:
        raise ValueError("solver must be one of 'auto', 'kkt', or 'slsqp'")
    if not isinstance(allow_short, (bool, np.bool_)):
        raise TypeError("allow_short must be a boolean")
    if not isinstance(maxiter, (int, np.integer)) or maxiter <= 0:
        raise ValueError("maxiter must be a positive integer")
    if not np.isscalar(tolerance) or not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("tolerance must be a positive finite scalar")
    if max_gross_exposure is not None:
        if (
            not np.isscalar(max_gross_exposure)
            or not np.isfinite(max_gross_exposure)
            or max_gross_exposure < 1
        ):
            raise ValueError("max_gross_exposure must be finite and at least 1")
    if additional_constraints is None:
        additional_constraints = []

    mu, sigma = _prepare_portfolio_inputs(
        expected_returns,
        covariance_matrix,
        covariance_tolerance=covariance_tolerance,
        regularization=regularization,
    )
    n_assets = mu.size
    normalised_bounds = _normalise_bounds(
        bounds,
        n_assets,
        allow_short=bool(allow_short),
    )

    target_tolerance = tolerance * max(1.0, abs(float(target_return)))
    returns_are_constant = bool(np.ptp(mu) <= target_tolerance)
    if returns_are_constant and abs(float(target_return) - float(mu[0])) > target_tolerance:
        raise ValueError(
            "target_return is infeasible because all assets have the same expected return"
        )

    include_target_constraint = not returns_are_constant
    has_bounds = any(lower is not None or upper is not None for lower, upper in normalised_bounds)
    has_additional_constraints = bool(additional_constraints)
    use_kkt = (
        solver in {"auto", "kkt"}
        and not has_bounds
        and max_gross_exposure is None
        and not has_additional_constraints
    )

    weights: FloatArray | None = None
    solver_name = "kkt"
    solver_message = "KKT equality-constrained solution"

    if use_kkt:
        try:
            weights = _solve_kkt(
                sigma,
                mu,
                float(target_return),
                include_target_constraint=include_target_constraint,
            )
        except (np.linalg.LinAlgError, ValueError) as exc:
            if solver == "kkt":
                raise ValueError(
                    "the KKT system is singular; use solver='slsqp' or regularize the covariance matrix"
                ) from exc

    if weights is None:
        solver_name = "slsqp"
        if initial_weights is None:
            weights = _feasible_start(
                mu,
                float(target_return),
                normalised_bounds,
                include_target_constraint=include_target_constraint,
                max_gross_exposure=max_gross_exposure,
            )
            if weights is None:
                if not has_additional_constraints:
                    raise ValueError(
                        "portfolio constraints are infeasible for target_return"
                    )
                weights = np.full(n_assets, 1.0 / n_assets)
        else:
            try:
                weights = np.asarray(initial_weights, dtype=float)
            except (TypeError, ValueError) as exc:
                raise TypeError("initial_weights must be numeric") from exc
            if weights.shape != (n_assets,) or not np.all(np.isfinite(weights)):
                raise ValueError("initial_weights must be a finite vector with one value per asset")

        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        ]
        if include_target_constraint:
            constraints.append(
                {"type": "eq", "fun": lambda w: w @ mu - float(target_return)}
            )
        if max_gross_exposure is not None:
            constraints.append(
                {
                    "type": "ineq",
                    "fun": lambda w: float(max_gross_exposure) - np.sum(np.abs(w)),
                }
            )
        constraints.extend(additional_constraints)

        result = minimize(
            fun=lambda w: float(w @ sigma @ w),
            x0=weights,
            jac=lambda w: 2.0 * sigma @ w,
            method="SLSQP",
            bounds=normalised_bounds,
            constraints=constraints,
            options={"ftol": tolerance, "maxiter": maxiter, "disp": False},
        )
        if not result.success:
            raise ValueError(f"portfolio optimization failed: {result.message}")
        weights = np.asarray(result.x, dtype=float)
        solver_message = str(result.message)

    expected_return = float(weights @ mu)
    variance = float(weights @ sigma @ weights)
    if variance < -target_tolerance:
        raise ValueError("computed portfolio variance is negative; covariance validation failed")
    variance = max(variance, 0.0)
    volatility = float(np.sqrt(variance))

    weight_residual = abs(float(np.sum(weights)) - 1.0)
    return_residual = abs(expected_return - float(target_return))
    if weight_residual > tolerance or return_residual > target_tolerance:
        raise ValueError(
            "portfolio solver returned a solution that violates the portfolio constraints"
        )

    result_object = PortfolioResult(
        weights=weights,
        expected_return=expected_return,
        volatility=volatility,
        variance=variance,
        solver=solver_name,
        message=solver_message,
    )
    return result_object if return_result else result_object.as_tuple()


def EFRS_portfolio(
    target_return: float,
    expected_returns: ArrayLike,
    covariance_matrix: ArrayLike,
    **kwargs,
) -> tuple[FloatArray, float, float] | PortfolioResult:
    """Backward-compatible wrapper for :func:`efrs_portfolio`."""
    return efrs_portfolio(target_return, expected_returns, covariance_matrix, **kwargs)


def portfolio_sharpe(weights: np.ndarray, expected_returns: np.ndarray,
                     covariance_matrix: np.ndarray, rf=None, zerocost=None) -> float:
    """
    Computes the Sharpe ratio of a portfolio given the asset weights, expected returns,
    covariance matrix, and risk-free rate.

    Parameters:
    -----------
    weights : np.ndarray
        A 1D NumPy array of portfolio weights (shape: `(n_assets,)`).
    expected_returns : np.ndarray
        A 1D NumPy array of expected returns for each asset (shape: `(n_assets,)`).
    covariance_matrix : np.ndarray
        A 2D NumPy array representing the covariance matrix of asset returns (shape: `(n_assets, n_assets)`).
    rf : float
        The risk-free rate.

    Returns:
    --------
    float
        The Sharpe ratio of the portfolio.

    Raises:
    -------
    TypeError:
        If any of the inputs are not NumPy arrays.
    ValueError:
        If the dimensions of inputs do not match.
    """

    # Enforce that all inputs are NumPy arrays
    if not isinstance(weights, np.ndarray):
        raise TypeError("weights must be a NumPy array")
    if not isinstance(expected_returns, np.ndarray):
        raise TypeError("expected_returns must be a NumPy array")
    if not isinstance(covariance_matrix, np.ndarray):
        raise TypeError("covariance_matrix must be a NumPy array")

    # Ensure correct dimensions
    if weights.ndim != 1:
        raise ValueError("weights must be a 1D vector")
    if expected_returns.ndim != 1:
        raise ValueError("expected_returns must be a 1D vector")
    if covariance_matrix.ndim != 2:
        raise ValueError("covariance_matrix must be a 2D array")

    # Get the number of assets from expected returns and weights
    n_assets = expected_returns.shape[0]

    # Check that weights and expected returns have the same length
    if weights.shape[0] != n_assets:
        raise ValueError(f"weights and expected_returns must have the same length ({n_assets})")

    # Check that the covariance matrix is square and matches the number of assets
    if covariance_matrix.shape != (n_assets, n_assets):
        raise ValueError(f"covariance_matrix must be a square matrix of shape ({n_assets}, {n_assets})")

    # Compute portfolio return as the weighted sum of expected asset returns
    port_ret = weights.T @ expected_returns

    # Compute portfolio volatility using the given covariance matrix
    port_vol = portfolio_volatility(weights, covariance_matrix)

    if zerocost:
        Sharpe=(port_ret) / port_vol
    else:
        Sharpe=(port_ret - rf) / port_vol

    # Compute and return the Sharpe ratio (excess return divided by risk)
    return Sharpe


def tangent_portfolio(expected_returns, covariance_matrix, rf=None, factors=None):
    """
    Calculates the weights, expected return, and volatility of the tangent portfolio.

    Parameters:
    expected_returns (np.array): Vector of expected returns for each asset.
    covariance_matrix (np.array): Covariance matrix of asset returns.
    rf (float): Risk-free rate of return.

    Returns:
    tuple: A tuple containing the tangent portfolio weights, expected return, and volatility.
    """
    N = expected_returns.shape[0]
    initial_weights = np.ones(N) / N  # Initialize as a 1D column vector

    if factors is not True:
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})  # Constraint: weights sum to 1

        def neg_portfolio_sharpe(x, expected_returns, covariance_matrix, rf):
            return -portfolio_sharpe(x, expected_returns, covariance_matrix, rf)

        # Perform optimization
        result = minimize(fun=neg_portfolio_sharpe, x0=initial_weights, args=(expected_returns, covariance_matrix, rf),
                      method="SLSQP", constraints=constraints)

        # Ensure result.x is reshaped as a column vector (N x 1)
        tangent_weights = result.x

        # Compute expected return and volatility for the tangent portfolio
        tangent_return = tangent_weights.T @ expected_returns
        tangent_volatility = portfolio_volatility(tangent_weights, covariance_matrix)
    else:
        constraints = ({'type': 'eq', 'fun': lambda x: x[0] - 1})  # Constraint: weights sum to 1

        def neg_portfolio_sharpe(x, expected_returns, covariance_matrix):
            return -portfolio_sharpe(
                x, expected_returns, covariance_matrix, zerocost=True
            )

        # Perform optimization
        result = minimize(fun=neg_portfolio_sharpe, x0=initial_weights, args=(expected_returns, covariance_matrix),
                      method="SLSQP", constraints=constraints)

        # Ensure result.x is reshaped as a column vector (N x 1)
        tangent_weights = result.x

        # Compute expected return and volatility for the tangent portfolio
        tangent_return = tangent_weights.T @ expected_returns
        tangent_volatility = portfolio_volatility(tangent_weights, covariance_matrix)


    return tangent_weights, tangent_return, tangent_volatility
