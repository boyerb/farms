# `farms` API reference

This page documents the public functions exported by `farms`. Each function
lists its required inputs, optional inputs, and outputs. Returns are generally
decimal returns: `0.01` represents 1 percent.

## Alpha Vantage data

### `get_alpha_vantage_api_key()`

Returns the Alpha Vantage API key from Colab Secrets or the local
`ALPHAVANTAGE_API_KEY` environment variable.

**Required Inputs**

- None.

**Optional Inputs**

- None.

**Outputs**

- `str` — The configured Alpha Vantage API key. Raises an error when no valid
  key is available.

### `load_alpha_vantage()`

Downloads one selected Alpha Vantage series for one or more tickers and can
merge Ken French factor returns.

**Required Inputs**

- `symbol` — A ticker string or an iterable of ticker strings. Example: `symbol=['AAPL', 'MSFT']`.
- `api_key` — Alpha Vantage API key. Example: `api_key=os.environ['ALPHAVANTAGE_API_KEY']`.
- `frequency` — Requested data frequency. Potential values are `"monthly"` and `"weekly"`. Example: `frequency='monthly'`.
- `field` — Selected series. Potential values are `"open"`, `"high"`, `"low"`, `"close"`, and `"returns"`. Example: `field='returns'`.

**Optional Inputs**

- `start_date` — Default is `None`. Sets the beginning of the inclusive sample period. Use `YYYY-MM` for monthly data and `YYYY-MM-DD` for weekly data. Example: `start_date='2000-01'`.
- `end_date` — Default is `None`. Sets the end of the inclusive sample period. Example: `end_date='2025-12'`.
- `include_factors` — Default is `"market"`. Adds Ken French factor returns. Potential values are `None` or `"none"` for no factors, `"market"` for `mkt-rf` and `rf`, `"ff3"` for Fama-French three factors and `rf`, and `"ff5"` for Fama-French five factors and `rf`. Example: `include_factors='ff3'`.
- `timeout` — Default is `30`. Sets the HTTP timeout in seconds, or accepts a `(connect, read)` timeout tuple. Example: `timeout=60`.
- `max_retries` — Default is `3`. Sets the maximum number of retries for transient failures and rate-limit responses. Example: `max_retries=5`.
- `backoff_factor` — Default is `1.0`. Sets the exponential retry backoff factor. Example: `backoff_factor=2.0`.
- `session` — Default is `None`. Accepts an optional `requests.Session` for connection reuse or custom request configuration. Example: `session=requests.Session()`.

**Outputs**

- `pandas.DataFrame` — A date-indexed DataFrame containing one selected series per ticker and any requested factor columns. The result includes metadata in `DataFrame.attrs` for symbols, frequency, field, and factor selection.

### `load_alpha_vantage_monthly()`

Downloads monthly adjusted Alpha Vantage data.

**Required Inputs**

- `symbol` — Ticker symbol. Example: `symbol='MSFT'`.
- `api_key` — Alpha Vantage API key. Example: `api_key=os.environ['ALPHAVANTAGE_API_KEY']`.

**Optional Inputs**

- `start_date` — Default is `None`. Sets the inclusive beginning of the sample period using `YYYY-MM`. Example: `start_date='2020-01'`.
- `end_date` — Default is `None`. Sets the inclusive end of the sample period using `YYYY-MM`. Example: `end_date='2025-12'`.
- `field` — Default is `None`. Selects one field or returns all parsed fields. Potential values are `"open"`, `"high"`, `"low"`, `"close"`, and `"returns"`. Example: `field='close'`.
- `timeout` — Default is `30`. Sets the HTTP timeout in seconds or accepts a `(connect, read)` tuple. Example: `timeout=60`.
- `max_retries` — Default is `3`. Sets the maximum number of transient-failure retries. Example: `max_retries=5`.
- `backoff_factor` — Default is `1.0`. Sets the exponential retry backoff factor. Example: `backoff_factor=2.0`.
- `session` — Default is `None`. Accepts an optional `requests.Session`. Example: `session=requests.Session()`.

**Outputs**

- `pandas.DataFrame` — Monthly adjusted data indexed by a monthly `PeriodIndex`. The default output includes parsed price fields and `Return`.

### `load_alpha_vantage_weekly()`

Downloads weekly adjusted Alpha Vantage data.

**Required Inputs**

- `symbol` — Ticker symbol. Example: `symbol='MSFT'`.
- `api_key` — Alpha Vantage API key. Example: `api_key=os.environ['ALPHAVANTAGE_API_KEY']`.

**Optional Inputs**

- `start_date` — Default is `None`. Sets the inclusive beginning of the sample period using `YYYY-MM-DD`. Example: `start_date='2020-01-01'`.
- `end_date` — Default is `None`. Sets the inclusive end of the sample period using `YYYY-MM-DD`. Example: `end_date='2025-12-31'`.
- `field` — Default is `None`. Selects one field or returns all parsed fields. Potential values are `"open"`, `"high"`, `"low"`, `"close"`, and `"returns"`. Example: `field='returns'`.
- `timeout` — Default is `30`. Sets the HTTP timeout in seconds or accepts a `(connect, read)` tuple. Example: `timeout=60`.
- `max_retries` — Default is `3`. Sets the maximum number of transient-failure retries. Example: `max_retries=5`.
- `backoff_factor` — Default is `1.0`. Sets the exponential retry backoff factor. Example: `backoff_factor=2.0`.
- `session` — Default is `None`. Accepts an optional `requests.Session`. Example: `session=requests.Session()`.

**Outputs**

- `pandas.DataFrame` — Weekly adjusted data indexed by a weekly `PeriodIndex`. The default output includes parsed price fields and `Return`.

### `load_alpha_vantage_daily()`

Compatibility wrapper for the premium Alpha Vantage daily endpoint. The daily
adjusted endpoint is not supported for ordinary free-account use.

**Required Inputs**

- `symbol` — Ticker symbol. Example: `symbol='MSFT'`.
- `api_key` — Alpha Vantage API key. Example: `api_key=os.environ['ALPHAVANTAGE_API_KEY']`.

**Optional Inputs**

- `start_date` — Default is `None`. Sets the inclusive beginning of the sample period. Example: `start_date='2020-01-01'`.
- `end_date` — Default is `None`. Sets the inclusive end of the sample period. Example: `end_date='2025-12-31'`.
- `field` — Default is `None`. Selects one field. Potential values are `"open"`, `"high"`, `"low"`, `"close"`, and `"returns"`. Example: `field='close'`.
- `outputsize` — Default is `"compact"`. Selects the Alpha Vantage response size. Potential values are `"compact"` and `"full"`. Example: `outputsize='full'`.
- `timeout` — Default is `30`. Sets the HTTP timeout in seconds or accepts a `(connect, read)` tuple. Example: `timeout=60`.
- `max_retries` — Default is `3`. Sets the maximum number of transient-failure retries. Example: `max_retries=5`.
- `backoff_factor` — Default is `1.0`. Sets the exponential retry backoff factor. Example: `backoff_factor=2.0`.
- `session` — Default is `None`. Accepts an optional `requests.Session`. Example: `session=requests.Session()`.

**Outputs**

- `pandas.DataFrame` — Parsed daily data when the endpoint is available. Premium-access or endpoint errors are raised rather than silently returning incomplete data.

### `format_alpha_vantage()`

Formats a monthly Alpha Vantage `requests.Response` without performing a
network request.

**Required Inputs**

- `response` — A successful Alpha Vantage `requests.Response`. Example: `response=requests.get(url)`.

**Optional Inputs**

- `start_date` — Default is `None`. Filters the inclusive beginning of the monthly sample using `YYYY-MM`. Example: `start_date='2020-01'`.
- `end_date` — Default is `None`. Filters the inclusive end of the monthly sample using `YYYY-MM`. Example: `end_date='2025-12'`.
- `field` — Default is `None`. Selects one field or returns all parsed fields. Potential values are `"open"`, `"high"`, `"low"`, `"close"`, and `"returns"`. Example: `field='returns'`.

**Outputs**

- `pandas.DataFrame` — Formatted monthly data indexed by a monthly `PeriodIndex`. The default includes `Return`, whose first observation is `NaN`.

### `format_alpha_vantage_weekly()`

Formats a weekly Alpha Vantage response without performing a network request.

**Required Inputs**

- `response` — A successful Alpha Vantage `requests.Response`. Example: `response=requests.get(url)`.

**Optional Inputs**

- `start_date` — Default is `None`. Filters the inclusive beginning of the weekly sample using `YYYY-MM-DD`. Example: `start_date='2020-01-01'`.
- `end_date` — Default is `None`. Filters the inclusive end of the weekly sample using `YYYY-MM-DD`. Example: `end_date='2025-12-31'`.
- `field` — Default is `None`. Selects one field or returns all parsed fields. Potential values are `"open"`, `"high"`, `"low"`, `"close"`, and `"returns"`. Example: `field='returns'`.

**Outputs**

- `pandas.DataFrame` — Formatted weekly data indexed by a weekly `PeriodIndex`. The default includes `Return`.

### `format_alpha_vantage_daily()`

Compatibility wrapper for formatting a daily Alpha Vantage response.

**Required Inputs**

- `response` — A successful Alpha Vantage `requests.Response`. Example: `response=requests.get(url)`.

**Optional Inputs**

- `start_date` — Default is `None`. Filters the inclusive beginning of the daily sample using `YYYY-MM-DD`. Example: `start_date='2020-01-01'`.
- `end_date` — Default is `None`. Filters the inclusive end of the daily sample using `YYYY-MM-DD`. Example: `end_date='2025-12-31'`.
- `field` — Default is `None`. Selects one field or returns all parsed fields. Potential values are `"open"`, `"high"`, `"low"`, `"close"`, and `"returns"`. Example: `field='returns'`.

**Outputs**

- `pandas.DataFrame` — Formatted daily data when the endpoint response is valid.

### `format_alpha_vantage_time_series()`

Formats an adjusted Alpha Vantage response for monthly or weekly data.

**Required Inputs**

- `response` — A successful Alpha Vantage `requests.Response`. Example: `response=requests.get(url)`.

**Optional Inputs**

- `frequency` — Default is `"monthly"`. Selects the response frequency. Potential values are `"monthly"` and `"weekly"`. Example: `frequency='weekly'`.
- `start_date` — Default is `None`. Filters the inclusive beginning of the sample using the format appropriate for `frequency`. Example: `start_date='2020-01'`.
- `end_date` — Default is `None`. Filters the inclusive end of the sample using the format appropriate for `frequency`. Example: `end_date='2025-12'`.
- `field` — Default is `None`. Selects one field or returns all parsed fields. Potential values are `"open"`, `"high"`, `"low"`, `"close"`, and `"returns"`. Example: `field='close'`.

**Outputs**

- `pandas.DataFrame` — A normalized DataFrame with a frequency-specific `PeriodIndex`. The default output includes `Return` as the final column.

## CRSP data

### `load_crsp_data()` / `get_crsp_msf_by_ids()`

`get_crsp_msf_by_ids()` is the public compatibility name for the same CRSP
identifier-based loader.

**Required Inputs**

- `db` — An open WRDS connection or compatible database wrapper. Example: `db=wrds.Connection(...)`.
- `identifiers` — A homogeneous iterable of ticker strings or CRSP PERMNO integers. A scalar string is not accepted. Example: `identifiers=['AAPL', 'MSFT']`.
- `start_date` — Inclusive beginning of the sample period. Use `YYYY-MM` for monthly data or `YYYY-MM-DD` for daily data. Example: `start_date='2020-01'`.
- `end_date` — Inclusive end of the sample period. Example: `end_date='2025-12'`.

**Optional Inputs**

- `chunk_size` — Default is `500`. Sets the maximum number of identifiers per SQL `IN` clause. Example: `chunk_size=1000`.
- `identifier_type` — Default is `None`, which infers the type from a homogeneous identifier iterable. Potential values are `"permno"` and `"ticker"`. Example: `identifier_type='permno'`.
- `frequency` — Default is `"monthly"`. Selects the CRSP monthly or daily stock file. Potential values are `"monthly"` and `"daily"`. Example: `frequency='daily'`.
- `include_factors` — Default is `None`. Merges Ken French factors. Potential values are `None`, `"none"`, `"market"`, `"ff3"`, and `"ff5"`. Example: `include_factors='market'`.

**Outputs**

- `pandas.DataFrame` — Chronologically sorted CRSP observations with a `date` index and CRSP security, price, return, volume, and share-count columns. Monthly results use a `PeriodIndex`; daily results use a `DatetimeIndex`. Requested factor columns are included when selected.

### `load_all_crsp_data()`

Loads CRSP data for all securities in a date range, optionally applying
beginning-of-period screens.

**Required Inputs**

- `db` — An open WRDS connection or compatible database wrapper. Example: `db=wrds.Connection(...)`.
- `start_date` — Inclusive beginning of the sample period. Example: `start_date='2020-01'`.
- `end_date` — Inclusive end of the sample period. Example: `end_date='2025-12'`.

**Optional Inputs**

- `frequency` — Default is `"monthly"`. Potential values are `"monthly"` and `"daily"`. Example: `frequency='daily'`.
- `share_codes` — Default is `None`. Restricts observations to securities with selected CRSP share codes. Example: `share_codes=(10, 11)`.
- `market_cap_min` — Default is `None`. Sets a strict lower bound on beginning-of-period market capitalization in dollars. Example: `market_cap_min=100_000_000`.
- `market_cap_max` — Default is `None`. Sets a strict upper bound on beginning-of-period market capitalization in dollars. Example: `market_cap_max=10_000_000_000`.
- `price_min` — Default is `None`. Sets a strict lower bound on beginning-of-period absolute CRSP price. Example: `price_min=5`.
- `price_max` — Default is `None`. Sets a strict upper bound on beginning-of-period absolute CRSP price. Example: `price_max=500`.
- `include_factors` — Default is `None`. Merges Ken French factors. Potential values are `None`, `"none"`, `"market"`, `"ff3"`, and `"ff5"`. Example: `include_factors='ff5'`.

**Outputs**

- `pandas.DataFrame` — CRSP observations for all securities satisfying the requested screens. Monthly results use a monthly `PeriodIndex`; daily results use a `DatetimeIndex`.

## Kenneth French data

### `list_ken_french_data()`

Lists the registered Ken French portfolio strategy sources without downloading
the return data.

**Required Inputs**

- None.

**Optional Inputs**

- None.

**Outputs**

- `pandas.DataFrame` — One row for each registered strategy, portfolio granularity, and frequency combination.

### `load_ken_french_data()`

Loads normalized data from the Kenneth French Data Library.

**Required Inputs**

- `data_type` — Selects the factor model or portfolio granularity. Potential values are `"ff3"`, `"ff5"`, `"deciles"`, and `"quintiles"`; `"ff3d"` and `"ff5d"` are accepted legacy daily-factor aliases. Example: `data_type='deciles'`.

**Optional Inputs**

- `strategy` — Default is `None`. Selects the portfolio sorting characteristic, such as `"momentum"`, `"size"`, or `"booktomarket"`. Required for portfolio data and invalid for factor data. Example: `strategy='momentum'`.
- `frequency` — Default is `"monthly"`. Requests the source frequency. Potential values are `"monthly"`, `"weekly"`, and `"daily"`. Example: `frequency='daily'`.
- `start_date` — Default is `None`. Sets the inclusive beginning of the sample period. Example: `start_date='2000-01'`.
- `end_date` — Default is `None`. Sets the inclusive end of the sample period. Example: `end_date='2025-12'`.
- `portfolio` — Default is `None`, which returns every portfolio. Potential values are `None`, `"all"`, `"low"`, `"high"`, an integer, or a sequence of integers. Example: `portfolio=[1, 5, 10]`.
- `weighting` — Default is `"value"`. Selects value-weighted or equal-weighted portfolios. Potential values are `"value"` and `"equal"`. Example: `weighting='equal'`.
- `include_factors` — Default is `None`. Adds factor columns to portfolio data. Potential values are `None`, `"market"`, `"ff3"`, and `"ff5"`. Example: `include_factors='market'`.
- `details` — Default is `False`. Prints available portfolio construction details when `True`. Example: `details=True`.

**Outputs**

- `pandas.DataFrame` — Normalized factor or portfolio returns indexed by the observation date. Portfolio columns use decimal returns; optional factor columns include standardized names such as `mkt-rf`, `smb`, `hml`, `rmw`, `cma`, and `rf`.

### `get_ff3()`

Returns monthly Fama-French three-factor data.

**Required Inputs**

- None.

**Optional Inputs**

- `start_date` — Default is `None`. Sets the inclusive beginning of the sample period. Example: `start_date='2000-01'`.
- `end_date` — Default is `None`. Sets the inclusive end of the sample period. Example: `end_date='2025-12'`.

**Outputs**

- `pandas.DataFrame` — Monthly decimal-return Fama-French three-factor data, including `mkt-rf`, `smb`, `hml`, and `rf`.

### `get_ff5()`

Returns monthly Fama-French five-factor data.

**Required Inputs**

- None.

**Optional Inputs**

- `start_date` — Default is `None`. Sets the inclusive beginning of the sample period. Example: `start_date='2000-01'`.
- `end_date` — Default is `None`. Sets the inclusive end of the sample period. Example: `end_date='2025-12'`.

**Outputs**

- `pandas.DataFrame` — Monthly decimal-return Fama-French five-factor data, including `mkt-rf`, `smb`, `hml`, `rmw`, `cma`, and `rf`.

### `get_ff3d()`

Returns daily Fama-French three-factor data.

**Required Inputs**

- None.

**Optional Inputs**

- `start_date` — Default is `None`. Sets the inclusive beginning of the sample period. Example: `start_date='2000-01-01'`.
- `end_date` — Default is `None`. Sets the inclusive end of the sample period. Example: `end_date='2025-12-31'`.

**Outputs**

- `pandas.DataFrame` — Daily decimal-return Fama-French three-factor data, including `mkt-rf`, `smb`, `hml`, and `rf`.

### `get_ff5d()`

Returns daily Fama-French five-factor data.

**Required Inputs**

- None.

**Optional Inputs**

- `start_date` — Default is `None`. Sets the inclusive beginning of the sample period. Example: `start_date='2000-01-01'`.
- `end_date` — Default is `None`. Sets the inclusive end of the sample period. Example: `end_date='2025-12-31'`.

**Outputs**

- `pandas.DataFrame` — Daily decimal-return Fama-French five-factor data, including `mkt-rf`, `smb`, `hml`, `rmw`, `cma`, and `rf`.

### `market()`

Returns the market excess return and risk-free rate from the Ken French FF3
data.

**Required Inputs**

- None.

**Optional Inputs**

- `start_date` — Default is `None`. Sets the inclusive beginning of the sample period. Example: `start_date='2000-01'`.
- `end_date` — Default is `None`. Sets the inclusive end of the sample period. Example: `end_date='2025-12'`.
- `frequency` — Default is `"monthly"`. Potential values are `"monthly"`, `"weekly"`, and `"daily"`. Example: `frequency='daily'`.

**Outputs**

- `pandas.DataFrame` — A date-indexed DataFrame with decimal-return columns `mkt-rf` and `rf`.

### `get_ken_french_deciles()`

Legacy wrapper for monthly value-weighted Kenneth French decile portfolios.

**Required Inputs**

- `stype` — Portfolio sorting strategy, or `"list"` to print registered strategies. Example: `stype='momentum'`.

**Optional Inputs**

- `start_date` — Default is `None`. Sets the inclusive beginning of the sample period. Example: `start_date='2000-01'`.
- `end_date` — Default is `None`. Sets the inclusive end of the sample period. Example: `end_date='2025-12'`.
- `details` — Default is `None`. When `True`, prints portfolio construction details. Example: `details=True`.
- `factors` — Default is `None`, which includes market and risk-free columns for backward compatibility. Potential values are `None`, `"FF3"`, and `"FF5"`. Example: `factors='FF5'`.

**Outputs**

- `pandas.DataFrame` — Monthly value-weighted decile returns, optionally merged with factor columns.
- `None` — When `stype='list'`, the registered strategy names are printed and no DataFrame is returned.

## Black-Scholes option functions

### `black_scholes()`

Calculates a Black-Scholes call or put option value.

**Required Inputs**

- `type` — Option type. Potential values are `"call"` and `"put"`. Example: `type='call'`.
- `S` — Current underlying asset price. Example: `S=100`.
- `K` — Option strike price. Example: `K=105`.
- `T` — Time to expiration in years. Example: `T=1`.
- `rf` — Risk-free return for the period. Example: `rf=0.05`.
- `sigma` — Volatility of the underlying asset. Example: `sigma=0.20`.

**Optional Inputs**

- None.

**Outputs**

- `float` — The Black-Scholes option value.

### `implied_volatility()`

Solves for the volatility that matches a target option price.

**Required Inputs**

- `type` — Option type. Potential values are `"call"` and `"put"`. Example: `type='call'`.
- `option_price` — Observed option price. Example: `option_price=8.50`.
- `S` — Current underlying asset price. Example: `S=100`.
- `K` — Option strike price. Example: `K=105`.
- `T` — Time to expiration in years. Example: `T=1`.
- `r` — Risk-free return for the period. Example: `r=0.05`.

**Optional Inputs**

- None.

**Outputs**

- `float` — Implied volatility found between `1e-6` and `5.0`.
- `numpy.nan` — Returned when no root exists in the search interval.

## Portfolio functions

### `efrs_portfolio()` / `EFRS_portfolio()`

Computes the minimum-variance fully invested portfolio for a target return.
There is no separate risk-free allocation. `EFRS_portfolio()` is the
backward-compatible public name; `efrs_portfolio()` is the canonical name.

**Required Inputs**

- `target_return` — Finite target return on the same time scale as `expected_returns`. Example: `target_return=0.08`.
- `expected_returns` — One-dimensional vector of finite expected asset returns. Example: `expected_returns=np.array([0.05, 0.08, 0.11])`.
- `covariance_matrix` — Square, symmetric, positive-semidefinite covariance matrix with one row and column per asset. Example: `covariance_matrix=np.array([[0.04, 0.01], [0.01, 0.05]])`.

**Optional Inputs**

- `bounds` — Default is `None`. Sets a global `(lower, upper)` bound or one bound pair per asset. Example: `bounds=(0.0, 1.0)`.
- `allow_short` — Default is `True`. Allows unrestricted short positions when `True`; imposes nonnegative lower bounds when `False`. Potential values are `True` and `False`. Example: `allow_short=False`.
- `max_gross_exposure` — Default is `None`. Limits `sum(abs(weights))`; must be at least `1`. Example: `max_gross_exposure=1.5`.
- `initial_weights` — Default is `None`. Supplies the starting point for the numerical SLSQP solver. Example: `initial_weights=np.array([1/3, 1/3, 1/3])`.
- `additional_constraints` — Default is `None`. Supplies a list or tuple of SciPy-compatible SLSQP constraints and forces numerical optimization. Example: `additional_constraints=[{'type': 'ineq', 'fun': lambda w: w[0] - 0.10}]`.
- `solver` — Default is `"auto"`. Potential values are `"auto"`, `"kkt"`, and `"slsqp"`. Example: `solver='slsqp'`.
- `tolerance` — Default is `1e-8`. Sets solver and constraint-residual tolerance. Example: `tolerance=1e-10`.
- `maxiter` — Default is `1000`. Sets the maximum number of SLSQP iterations. Example: `maxiter=2000`.
- `covariance_tolerance` — Default is `1e-10`. Sets the tolerance for covariance symmetry and positive-semidefinite checks. Example: `covariance_tolerance=1e-8`.
- `regularization` — Default is `0.0`. Adds a nonnegative diagonal regularization value to the covariance matrix. Example: `regularization=1e-6`.
- `return_result` — Default is `False`. Returns a `PortfolioResult` instead of the legacy tuple when `True`. Potential values are `True` and `False`. Example: `return_result=True`.

**Outputs**

- `tuple` — When `return_result=False`, returns `(weights, expected_return, volatility)`.
  - `weights` — NumPy vector of portfolio weights that sum to one.
  - `expected_return` — Expected return of the computed portfolio.
  - `volatility` — Square root of the computed portfolio variance.
- `PortfolioResult` — When `return_result=True`, contains `weights`, `expected_return`, `volatility`, `variance`, `solver`, and `message`. Its `as_tuple()` method returns the legacy tuple.

### `portfolio_volatility()`

Calculates portfolio volatility from weights and a covariance matrix.

**Required Inputs**

- `weights` — One-dimensional portfolio weight vector. Example: `weights=np.array([0.5, 0.5])`.
- `covariance_matrix` — Covariance matrix compatible with `weights`. Example: `covariance_matrix=np.array([[0.04, 0.01], [0.01, 0.05]])`.

**Optional Inputs**

- None.

**Outputs**

- `float` or `numpy.float64` — Square root of `weights.T @ covariance_matrix @ weights`.

### `portfolio_sharpe()`

Calculates a portfolio Sharpe ratio.

**Required Inputs**

- `weights` — One-dimensional NumPy portfolio weight vector. Example: `weights=np.array([0.5, 0.5])`.
- `expected_returns` — One-dimensional NumPy vector of expected asset returns. Example: `expected_returns=np.array([0.06, 0.08])`.
- `covariance_matrix` — Square NumPy covariance matrix compatible with the weights and expected returns. Example: `covariance_matrix=np.eye(2) * 0.04`.

**Optional Inputs**

- `rf` — Default is `None`. Risk-free return subtracted from the portfolio return. Example: `rf=0.02`.
- `zerocost` — Default is `None`. When truthy, calculates the ratio using portfolio return rather than subtracting `rf`. Example: `zerocost=True`.

**Outputs**

- `float` — Portfolio excess return divided by portfolio volatility, or portfolio return divided by volatility when `zerocost` is truthy.

### `tangent_portfolio()`

Calculates the maximum-Sharpe fully invested portfolio of ordinary assets.
The returned exposures are ordinary asset weights and sum to one.

**Required Inputs**

- `expected_returns` — Expected asset return vector. Example: `expected_returns=np.array([0.05, 0.08, 0.11])`.
- `covariance_matrix` — Asset covariance matrix. Example: `covariance_matrix=np.eye(3) * 0.04`.

**Optional Inputs**

- `rf` — Default is `0.0`. Risk-free return used in the Sharpe-ratio objective. Example: `rf=0.02`.
- `allow_short` — Default is `True`. When `False`, imposes nonnegative asset weights.
- `bounds` — Optional global or per-asset weight bounds.
- `initial_weights` — Optional feasible starting weights for the optimizer.
- `tolerance` — Default is `1e-8`. Optimization tolerance.
- `maxiter` — Default is `1000`. Maximum number of optimizer iterations.
- `covariance_tolerance` — Default is `1e-10`. Tolerance used when validating the covariance matrix.
- `regularization` — Default is `0.0`. Optional diagonal covariance regularization.

**Outputs**

- `tuple` — Returns `(exposures, expected_return, volatility)`. `exposures` is the vector of ordinary asset weights and sums to one.

For example:

```python
exposures, expected_return, volatility = tangent_portfolio(
    expected_returns=np.array([0.05, 0.08, 0.11]),
    covariance_matrix=covariance_matrix,
    rf=0.02,
    allow_short=False,
)
```

### `factor_tilt_portfolio()`

Calculates the maximum-Sharpe factor exposures around a fixed base exposure.
Use this when one return series is a base portfolio, such as the market, and
the remaining return series are zero-cost factors, such as SMB, HML, and MOM.
The base exposure is fixed at `1.0`; the factor exposures are unconstrained by
the ordinary fully-invested weight constraint unless `tilt_bounds` are supplied.

**Required Inputs**

- `expected_returns` — Expected returns ordered as base portfolio, then zero-cost factors.
- `covariance_matrix` — Covariance matrix in the same order as `expected_returns`.

**Optional Inputs**

- `rf` — Default is `0.0`. Risk-free return used in the Sharpe-ratio objective.
- `base_index` — Default is `0`. Index of the exposure fixed at `1.0`.
- `tilt_bounds` — Optional bounds on the factor exposures.
- `initial_tilts` — Optional starting values for the factor exposures.
- `tolerance` — Default is `1e-8`. Optimization tolerance.
- `maxiter` — Default is `1000`. Maximum number of optimizer iterations.
- `covariance_tolerance` — Default is `1e-10`. Tolerance used when validating the covariance matrix.
- `regularization` — Default is `0.0`. Optional diagonal covariance regularization.

**Outputs**

- `tuple` — Returns `(exposures, expected_return, volatility)`. The base exposure is fixed at `1.0`; the remaining entries are optimized factor tilts.

For market, SMB, HML, and MOM returns:

```python
exposures, expected_return, volatility = factor_tilt_portfolio(
    expected_returns=np.array([mu_market, mu_smb, mu_hml, mu_mom]),
    covariance_matrix=factor_covariance_matrix,
    rf=rf,
)
```

The returned exposure vector has the form:

```text
[1.0, tilt_smb, tilt_hml, tilt_mom]
```

The Sharpe numerator is the expected total portfolio return minus `rf`:

```text
expected_return - rf
```

The covariance matrix must use the same ordering as `expected_returns`. The
factor return series should be measured on the same frequency and return
convention as the base series.

### `describe()`

Prints the mean and standard deviation of a series.

**Required Inputs**

- `name` — Label printed for the series. Example: `name='Market'`.
- `series` — Array-like series of observations. Example: `series=returns['Market']`.

**Optional Inputs**

- None.

**Outputs**

- `None` — Prints a formatted summary line and does not return a value.

## Plotting functions

### `plot_return_bars()`

Plots relative frequencies for discrete simulated return outcomes.

**Required Inputs**

- `simulated_returns` — One-dimensional simulated return observations. Example: `simulated_returns=np.array([0.0, 0.1, 0.1])`.
- `outcomes` — Possible return values. Bars are centered on these values. Example: `outcomes=[0.0, 0.1]`.

**Optional Inputs**

- `title` — Default is `None`. Sets the plot title. Example: `title='Simulated returns'`.
- `figsize` — Default is `(3.0, 3.0)`. Sets the figure size. Example: `figsize=(6, 4)`.
- `width` — Default is `0.04`. Sets the bar width in return units. Example: `width=0.02`.
- `alpha` — Default is `0.7`. Sets bar transparency. Example: `alpha=0.5`.
- `edgecolor` — Default is `'k'`. Sets the bar edge color. Example: `edgecolor='white'`.

**Outputs**

- `tuple` — Returns `(figure, axis)` containing the Matplotlib Figure and Axes objects.

### `plot_return_histograms()`

Plots return distributions for selected DataFrame columns.

**Required Inputs**

- `returns` — DataFrame containing numeric decimal-period returns. Example: `returns=portfolio_returns`.

**Optional Inputs**

- `columns` — Default is `None`, which plots all columns. Selects columns to plot. Example: `columns=['dec1', 'dec10']`.
- `bins` — Default is `'auto'`. Estimates bin count from pooled returns or accepts a positive integer. Example: `bins=15`.
- `show_mean` — Default is `True`. Draws a vertical line at each column's mean. Example: `show_mean=False`.
- `sharey` — Default is `True`. Uses one y-axis scale for all panels. Example: `sharey=False`.
- `figsize` — Default is `None`. Sets the overall figure size. Example: `figsize=(12, 4)`.
- `title` — Default is `None`. Sets a figure-level title. Example: `title='Return distributions'`.
- `alpha` — Default is `0.8`. Sets histogram transparency. Example: `alpha=0.5`.
- `edgecolor` — Default is `'white'`. Sets histogram-bar edge color. Example: `edgecolor='black'`.
- `ncols` — Default is `3`. Sets the number of panels per row. Example: `ncols=2`.

**Outputs**

- `tuple` — Returns `(figure, axes)`, where `axes` contains the visible Matplotlib Axes for the selected columns.

### `plot_return_scatter()`

Plots selected portfolio returns against a benchmark.

**Required Inputs**

- `returns` — DataFrame containing numeric decimal-period returns. Example: `returns=portfolio_returns`.
- `benchmark` — A Series or the name of a column in `returns` to use on the x-axis. Example: `benchmark='Market'`.

**Optional Inputs**

- `columns` — Default is `None`, which plots all columns except a named benchmark column. Example: `columns=['Portfolio A']`.
- `figsize` — Default is `None`. Sets the overall figure size. Example: `figsize=(10, 4)`.
- `title` — Default is `None`. Sets a figure-level title. Example: `title='Portfolio versus market'`.
- `alpha` — Default is `0.7`. Sets point transparency. Example: `alpha=0.5`.
- `color` — Default is `'steelblue'`. Sets point color. Example: `color='darkgreen'`.
- `ncols` — Default is `3`. Sets the number of panels per row. Example: `ncols=2`.
- `sharex` — Default is `True`. Shares the x-axis scale across panels. Example: `sharex=False`.
- `sharey` — Default is `True`. Shares the y-axis scale across panels. Example: `sharey=False`.

**Outputs**

- `tuple` — Returns `(figure, axes)`, where `axes` contains one visible Matplotlib Axes per selected return column.

### `plot_cumulative_wealth()`

Plots the growth of one dollar invested in selected portfolios.

**Required Inputs**

- `returns` — DataFrame containing numeric decimal-period returns. Example: `returns=portfolio_returns`.

**Optional Inputs**

- `columns` — Default is `None`, which plots all columns. Example: `columns=['dec1', 'dec10']`.
- `start` — Default is `None`. Selects the first observation included in the wealth calculation. Example: `start='2000-01-01'`.
- `figsize` — Default is `(8.0, 4.0)`. Sets the figure size. Example: `figsize=(10, 5)`.
- `title` — Default is `'Growth of One Dollar'`. Sets the plot title. Example: `title='Portfolio wealth'`.
- `xlabel` — Default is `'Date'`. Sets the horizontal-axis label. Example: `xlabel='Month'`.
- `ylabel` — Default is `'Dollars'`. Sets the vertical-axis label. Example: `ylabel='Portfolio value'`.
- `legend_ncols` — Default is `3`. Sets the number of legend columns. Example: `legend_ncols=2`.
- `legend_fontsize` — Default is `8`. Sets the legend font size. Example: `legend_fontsize=10`.
- `grid_alpha` — Default is `0.3`. Sets grid transparency. Example: `grid_alpha=0.5`.

**Outputs**

- `tuple` — Returns `(figure, axis)` containing the Matplotlib Figure and Axes objects.

## Statistics and regression functions

### `summary_stats()`

Calculates annualized summary statistics for portfolio returns.

**Required Inputs**

- `returns` — DataFrame containing numeric decimal-period returns. Example: `returns=portfolio_returns`.

**Optional Inputs**

- `risk_free` — Default is `None`. Accepts a numeric Series aligned to `returns.index`, a scalar numeric value, or a one-column DataFrame. When supplied, adds annualized excess mean and Sharpe ratio. The Sharpe ratio uses excess-return volatility as its denominator. Example: `risk_free=0.002`.
- `frequency` — Default is `'monthly'`. Selects the annualization frequency. Potential values are `'daily'`, `'weekly'`, and `'monthly'`. Example: `frequency='daily'`.

**Outputs**

- `pandas.DataFrame` — One row per return column with `Observations`, `Annualized arithmetic mean`, and `Annualized volatility`. When `risk_free` is supplied, also includes `Annualized excess mean` and `Annualized Sharpe ratio`.

### `intercept()`

Fits an OLS regression with an intercept and returns the estimated intercept.

**Required Inputs**

- `y` — Dependent-variable observations. Example: `y=returns['Portfolio']`.
- `x` — Independent-variable observations. Example: `x=returns['Market']`.

**Optional Inputs**

- None.

**Outputs**

- `float` or `numpy` scalar — Estimated regression intercept.

### `slope()`

Fits an OLS regression with an intercept and returns the estimated slope.

**Required Inputs**

- `y` — Dependent-variable observations. Example: `y=returns['Portfolio']`.
- `x` — Independent-variable observations. Example: `x=returns['Market']`.

**Optional Inputs**

- None.

**Outputs**

- `float` or `numpy` scalar — Estimated regression slope.

### `linear_regression_summary()`

Fits an OLS regression and returns coefficient estimates with confidence
intervals.

**Required Inputs**

- `X` — Independent variable Series or DataFrame. Example: `X=returns[['Market', 'SMB']]`.
- `Y` — Dependent variable Series. Example: `Y=returns['Portfolio']`.

**Optional Inputs**

- `ci` — Default is `0.95`. Sets the confidence level. Example: `ci=0.99`.

**Outputs**

- `pandas.DataFrame` — A coefficient table indexed by model term with columns `coef`, `ci_lower`, and `ci_upper`.

## Public exception classes

- `AlphaVantageError` — Base error for Alpha Vantage failures.
- `AlphaVantageRateLimitError` — Indicates an Alpha Vantage rate-limit response.
- `AlphaVantageResponseError` — Indicates an invalid or malformed Alpha Vantage response.
