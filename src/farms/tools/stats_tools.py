import numpy as np
import pandas as pd
import statsmodels.api as sm


_ANNUALIZATION_FACTORS = {
    "daily": 252,
    "weekly": 52,
    "monthly": 12,
}


def summary_stats(
    returns: pd.DataFrame,
    risk_free: pd.Series | float | int | None = None,
    frequency: str = "monthly",
) -> pd.DataFrame:
    """Calculate annualized summary statistics for portfolio returns.

    Parameters
    ----------
    returns : pandas.DataFrame
        DataFrame of decimal period returns. Each column represents a
        portfolio or asset.
    risk_free : pandas.Series, float, int, or None, default None
        Decimal risk-free return for each observation, or a scalar risk-free
        return that applies to every observation. If supplied, annualized
        excess mean and Sharpe ratio are included in the result.
    frequency : {"daily", "weekly", "monthly"}, default "monthly"
        Frequency of the observations. The function uses 252, 52, or 12
        periods per year, respectively.

    Returns
    -------
    pandas.DataFrame
        One row per return column. The default columns are ``Observations``,
        ``Annualized arithmetic mean``, and ``Annualized volatility``. When
        ``risk_free`` is supplied, ``Annualized excess mean`` and
        ``Annualized Sharpe ratio`` are added.

    Notes
    -----
    Arithmetic means are annualized by multiplying by the number of periods
    per year. Volatility is annualized using square-root-of-time scaling.
    Minimums and percentiles are intentionally not included because they are
    period-specific distribution statistics, not quantities that should be
    annualized by simple multiplication.
    """

    if not isinstance(returns, pd.DataFrame):
        raise TypeError("returns must be a pandas DataFrame")

    if not isinstance(frequency, str):
        raise TypeError("frequency must be 'daily', 'weekly', or 'monthly'")
    frequency = frequency.lower()
    if frequency not in _ANNUALIZATION_FACTORS:
        valid = ", ".join(_ANNUALIZATION_FACTORS)
        raise ValueError(f"frequency must be one of: {valid}")

    non_numeric_columns = [
        column
        for column in returns.columns
        if not pd.api.types.is_numeric_dtype(returns[column])
    ]
    if non_numeric_columns:
        raise TypeError(
            "returns must contain only numeric columns; "
            f"non-numeric columns: {non_numeric_columns}"
        )

    periods_per_year = _ANNUALIZATION_FACTORS[frequency]
    annualized_mean = periods_per_year * returns.mean()
    annualized_volatility = np.sqrt(periods_per_year) * returns.std()

    result = pd.DataFrame(index=returns.columns)
    result["Observations"] = returns.count()
    result["Annualized arithmetic mean"] = annualized_mean
    result["Annualized volatility"] = annualized_volatility

    if risk_free is not None:
        if isinstance(risk_free, pd.DataFrame):
            if risk_free.shape[1] != 1:
                raise TypeError("risk_free DataFrame must contain exactly one column")
            risk_free = risk_free.iloc[:, 0]

        if isinstance(risk_free, pd.Series):
            if not pd.api.types.is_numeric_dtype(risk_free):
                raise TypeError("risk_free must contain numeric values")
            risk_free = risk_free.reindex(returns.index)
            excess_returns = returns.sub(risk_free, axis=0)
        elif np.isscalar(risk_free) and isinstance(risk_free, (int, float, np.number)):
            excess_returns = returns - risk_free
        else:
            raise TypeError("risk_free must be a numeric Series or scalar")

        annualized_excess_mean = periods_per_year * excess_returns.mean()
        result["Annualized excess mean"] = annualized_excess_mean
        result["Annualized Sharpe ratio"] = annualized_excess_mean.div(
            annualized_volatility.where(annualized_volatility != 0)
        )

    return result


def intercept(y,x):
    x_with_intercept = sm.add_constant(x)

    # Fit the model: y = β0 + β1*x
    model = sm.OLS(y, x_with_intercept)
    results = model.fit()

    # Return the slope (coefficient of x)
    return results.params[0]  # The slope is the second parameter (after the intercept)


def slope(y,x):
    x_with_intercept = sm.add_constant(x)

    # Fit the model: y = β0 + β1*x
    model = sm.OLS(y, x_with_intercept)
    results = model.fit()

    # Return the slope (coefficient of x)
    return results.params[1]  # The slope is the second parameter (after the intercept)



def run_ols(X, Y, ci=0.95):
    """
    Runs OLS regression of Y on X and returns coefficients and confidence intervals.

    Parameters
    ----------
    X : pandas Series or DataFrame
        Independent variable(s)
    Y : pandas Series
        Dependent variable
    ci : float, default 0.95
        Confidence level (e.g., 0.95 for 95% CI)
    Returns
    -------
    results_df : pandas DataFrame
        Table with coefficient, lower CI, upper CI
    """

    # If X is a Series, convert to DataFrame
    if isinstance(X, pd.Series):
        X = X.to_frame()

    # Add constant for intercept
    X = sm.add_constant(X)

    # Fit model
    model = sm.OLS(Y, X).fit()

    # Confidence intervals
    alpha = 1 - ci
    ci_bounds = model.conf_int(alpha=alpha)
    ci_bounds.columns = ['ci_lower', 'ci_upper'] # nice names

    # Build output table (aligns by index: const, mkt-rf, etc.)
    results_df = pd.concat([model.params.rename('coef'), ci_bounds], axis=1)

    return results_df
