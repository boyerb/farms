# farms

Financial Analysis & Risk Management (`farms`) is a Python toolkit for
teaching and research. It provides a simple interface for downloading
Fama-French factors and portfolio returns from the
[Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).

## Installation

`farms` requires Python 3.11 or newer.
It supports Pandas 2.2 through the Pandas 3.x release series.

```bash
python -m pip install farms
```

To work on a local checkout, install it in editable mode:

```bash
python -m pip install -e .
```

The data-loading functions require an internet connection when called.

## Alpha Vantage adjusted prices

`format_alpha_vantage` formats a response from Alpha Vantage's
`TIME_SERIES_MONTHLY_ADJUSTED` endpoint. `load_alpha_vantage_monthly` downloads
and formats the same data, with timeouts and retries for transient failures.
For one or more tickers and a selected series across any supported frequency,
use `load_alpha_vantage`; its `frequency` and `field` arguments are required.
Obtain an API key from
[Alpha Vantage](https://www.alphavantage.co/support/#api-key) before making a
request.

For notebooks, `farms.get_alpha_vantage_api_key()` loads the key from Google
Colab Secrets when running in Colab, or from the local
`ALPHAVANTAGE_API_KEY` environment variable otherwise. It validates the setup
without printing the key:

```python
import farms

api_key = farms.get_alpha_vantage_api_key()
```

### Inputs

| Parameter | Required | Format and behavior |
| --- | --- | --- |
| `r` | Yes | A `requests.Response` from a successful `TIME_SERIES_MONTHLY_ADJUSTED` request. |
| `start_date` | No | `YYYY-MM`; `None` leaves the lower date bound unbounded. |
| `end_date` | No | `YYYY-MM`; `None` leaves the upper date bound unbounded. The range is inclusive. |
| `field` | No | Select one field: `"open"`, `"high"`, `"low"`, `"close"`, or `"returns"`. If omitted, return all fields. |

Invalid, reversed, rate-limited, or malformed API responses raise clear
exceptions.

For `load_alpha_vantage_monthly`, use `symbol` and `api_key` instead of `r`.
The optional `timeout`, `max_retries`, and `backoff_factor` parameters control
network behavior. The loader retries HTTP 429/5xx responses, connection errors,
and Alpha Vantage rate-limit messages. `AlphaVantageRateLimitError` and
`AlphaVantageResponseError` are available when callers need to handle those
conditions separately.

### Output

Returns a DataFrame with a monthly `PeriodIndex` named `date`, sorted
chronologically.

| Column | Description |
| --- | --- |
| `Open`, `High`, `Low`, `Close` | Monthly price fields returned by Alpha Vantage. |
| `Adjusted Close` | Split- and dividend-adjusted monthly closing price. |
| `Volume` | Monthly trading volume. |
| `Dividend Amount` | Dividend amount for the month. |
| `Return` | Decimal percentage change in `Adjusted Close`; `0.01` means 1%. The first available observation is `NaN` because it has no prior observation. |

All output columns are numeric. `Return` is the final column for monthly and
weekly Alpha Vantage results.

To request only one series, pass `field`. A single ticker produces a DataFrame
with one selected-field column. Multiple tickers are fetched and aligned by
date, producing one column per ticker:

```python
returns = farms.load_alpha_vantage(
    symbol=["MSFT", "AAPL", "GOOG"],
    api_key=os.environ["ALPHAVANTAGE_API_KEY"],
    frequency="monthly",
    field="returns",
)
```

The `field` option is available on the monthly and weekly loaders and their
corresponding formatters. `"returns"` uses the decimal percentage change in
`Adjusted Close`.

The generalized loader requires one ticker string or an iterable of ticker
strings, plus one field. By default, it also merges the monthly or weekly
Kenneth French market excess return and risk-free rate:

```python
close = farms.load_alpha_vantage(
    symbol=["MSFT", "AAPL"],
    api_key=os.environ["ALPHAVANTAGE_API_KEY"],
    frequency="weekly",
    field="close",
)
```

Use `include_factors` to choose the factor columns:

| `include_factors` | Added columns |
| --- | --- |
| `"market"` (default) | `ff_mkt_rf`, `ff_rf` |
| `"ff3"` | `ff_mkt_rf`, `ff_smb`, `ff_hml`, `ff_rf` |
| `"ff5"` | `ff_mkt_rf`, `ff_smb`, `ff_hml`, `ff_rmw`, `ff_cma`, `ff_rf` |
| `"none"` | No factor columns |

Factor values are decimal returns from the `farms` Ken French loader and are
joined by the Alpha Vantage date index. Weekly FF5 data is not published by
the Kenneth French Data Library, so `include_factors="ff5"` is available only
for monthly Alpha Vantage data.

Daily Alpha Vantage data is intentionally not exposed because the adjusted
daily endpoint requires premium access. This package's Alpha Vantage loader
is therefore fully usable with a free account and supports monthly and weekly
data only.

### Examples

```python
import os

import farms
monthly = farms.load_alpha_vantage_monthly(
    symbol="MSFT",
    api_key=os.environ["ALPHAVANTAGE_API_KEY"],
    start_date="2020-01",
    end_date="2020-12",
)
print(monthly.head())
```

Use `format_alpha_vantage(response)` directly when the HTTP request is managed
by the calling application.

The same parser supports weekly adjusted data:

```python
weekly = farms.load_alpha_vantage_weekly(
    symbol="MSFT",
    api_key=os.environ["ALPHAVANTAGE_API_KEY"],
    start_date="2020-01-01",
    end_date="2020-12-31",
)
```

Monthly results use a monthly `PeriodIndex`; weekly results use a `W-FRI`
`PeriodIndex`. Weekly date bounds use `YYYY-MM-DD`.

## CRSP stock data (WRDS)

`load_crsp_data` loads CRSP monthly or daily stock-file observations through a
caller-provided [WRDS](https://wrds-www.wharton.upenn.edu/) connection. You
need a WRDS account with access to the CRSP data set. `wrds` is intentionally
not installed as a required `farms` dependency, so install it separately:

The previous `get_crsp_msf_by_ids` name remains available as a compatibility
alias.

```bash
python -m pip install wrds
```

### Inputs

| Parameter | Required | Format and behavior |
| --- | --- | --- |
| `db` | Yes | An open `wrds.Connection` or compatible database wrapper. |
| `identifiers` | Yes | An iterable of PERMNOs or ticker strings; pass a single identifier as a one-element list. |
| `start_date` | Yes | `YYYY-MM` for monthly or `YYYY-MM-DD` for daily; `None` is not supported. |
| `end_date` | Yes | `YYYY-MM` for monthly or `YYYY-MM-DD` for daily; `None` is not supported. The range is inclusive. |
| `identifier_type` | No | `"permno"` or `"ticker"`. Providing it is recommended to avoid ambiguity. |
| `chunk_size` | No | Positive integer; defaults to `500`. |
| `frequency` | No | `"monthly"` or `"daily"`; defaults to `"monthly"`. |
| `include_factors` | No | `None`/`"none"`, `"market"`, `"ff3"`, or `"ff5"`; merges matching-frequency Ken French decimal returns. |

For monthly data, the date range refers to complete calendar months. For
example, `start_date="2020-01"` and `end_date="2020-03"` returns observations
from January through March 2020. For daily data, the range is inclusive of the
specified calendar dates.

### Output

Returns a DataFrame with a chronologically sorted `date` index. Monthly results
use a `PeriodIndex`; daily results use a `DatetimeIndex`. Columns include
PERMNO, PERMCO, ticker, company/name-history fields, and CRSP price, return,
volume, and shares-outstanding fields.
Ticker lookups use the historical CRSP name records, so a reused ticker may
return multiple PERMNOs over the requested date range.
`ret` and `retx` are decimal returns (`0.01` means 1%). `prc` follows the
CRSP price sign convention, `vol` is trading volume, and `shrout` is reported
by CRSP in thousands of shares.

When requested, factor columns use the non-conflicting names `ff_mkt_rf`,
`ff_smb`, `ff_hml`, `ff_rmw`, `ff_cma`, and `ff_rf`. The `market` option adds
`ff_mkt_rf` (the Fama-French market excess return) and `ff_rf`; `ff3` adds SMB
and HML; `ff5` also adds RMW and CMA. All factor values are decimal returns.

### Examples

Query by PERMNO:

```python
import farms
import wrds

db = wrds.Connection()
monthly = farms.load_crsp_data(
    db,
    identifiers=[14593, 12079],
    start_date="2020-01",
    end_date="2020-12",
    identifier_type="permno",
)
```

Or query by ticker:

```python
monthly = farms.load_crsp_data(
    db,
    identifiers=["AAPL", "MSFT"],
    start_date="2020-01",
    end_date="2020-12",
    identifier_type="ticker",
)
db.close()
```

## All-security CRSP loader

`load_all_crsp_data` loads every CRSP security in a bounded monthly or daily
date range. Optional `share_codes`, market-cap, and price screens are applied
using information observable at the beginning of each return period. For
monthly data, March 2009 observations use February 2009 month-end values. For
daily data, observations use the most recent prior CRSP trading observation.
It accepts the same `include_factors` options described above.

```python
monthly = farms.load_all_crsp_data(
    db,
    start_date="2009-03",
    end_date="2009-12",
    share_codes=(10, 11),
    market_cap_min=100_000_000,
    price_min=5,
)

daily = farms.load_all_crsp_data(
    db,
    start_date="2009-03-01",
    end_date="2009-03-31",
    frequency="daily",
    share_codes=(10, 11),
    price_min=5,
    price_max=500,
)
```

Daily data:

```python
daily = farms.load_crsp_data(
    db,
    identifiers=[14593, 12079],
    start_date="2020-01-02",
    end_date="2020-01-31",
    identifier_type="permno",
    frequency="daily",
)
```

Market capitalization is calculated as `abs(prc) * shrout * 1000`, since CRSP
reports `shrout` in thousands. Price and market-cap bounds are strict; use
only the lower bound for `> x`, only the upper bound for `< x`, or both for a
range.

## Unified Kenneth French loader

`load_ken_french_data` is the central loader for normalized Kenneth French
factor and portfolio data. The existing `get_ff3`, `get_ff5`, `get_ff3d`,
`get_ff5d`, and `get_ken_french_deciles` functions remain available as
convenience and compatibility wrappers.

```python
import farms

# Monthly, weekly, or daily factors
ff3 = farms.load_ken_french_data("ff3")
ff3_weekly = farms.load_ken_french_data("ff3", frequency="weekly")
ff5_daily = farms.load_ken_french_data("ff5", frequency="daily")

# All momentum deciles
momentum = farms.load_ken_french_data(
    "deciles",
    strategy="momentum",
)

# Selected portfolios plus Fama-French three-factor data
momentum_extremes = farms.load_ken_french_data(
    "deciles",
    strategy="momentum",
    portfolio=[1, 10],
    include_factors="ff3",
)
```

The first argument can be `"ff3"`, `"ff5"`, `"deciles"`, or
`"quintiles"`. FF3 supports monthly, weekly, and daily frequencies. FF5
supports monthly and daily frequencies; weekly FF5 returns are not published
by the Kenneth French Data Library and are therefore rejected by the loader.

Portfolio frequency support depends on the strategy. The loader supports
monthly data for all registered univariate strategies and daily data for
strategies with published daily files: size, book-to-market, profitability,
investment, momentum, and short-term reversal. The daily files provide true
decile portfolios. Monthly quintile views are available where the source
dataset provides true quintile columns; some ten-portfolio prior-return
datasets are decile-only. Weekly univariate decile and quintile data are not
published for the registered strategies.

Use `list_ken_french_data()` to inspect the registered strategy sources without
downloading returns:

```python
available = farms.list_ken_french_data()
available[available["strategy"] == "size"]
```

The result identifies each strategy's available decile or quintile view,
frequency, and underlying Kenneth French dataset. The `weighting` input remains
available when loading a listed source and can request either value-weighted or
equal-weighted returns when the source provides that table.

For portfolio data, `portfolio=None` or `"all"` returns every portfolio;
`portfolio="low"`, `portfolio="high"`, an integer, or a sequence of integers
selects specific portfolios. `include_factors=None` leaves portfolio data
unchanged, while `"market"`, `"ff3"`, or `"ff5"` adds factor columns.

## Fama-French factors

### Inputs

For Fama-French factor loaders and Kenneth French decile portfolios,
`start_date` and `end_date` are optional.

- When `start_date=None`, the loader requests the full available history,
  beginning from `1900-01-01`.
- When `end_date=None`, the loader requests observations through the latest
  date available from the Kenneth French Data Library.
- You may provide either bound independently.

Use month-formatted dates (`YYYY-MM`) for monthly data. Use day-formatted
dates (`YYYY-MM-DD`) for weekly, daily, and daily portfolio data.

### Outputs

All factor loaders return decimal returns (`0.01` means 1%) and an index named
`date`. This differs from the Kenneth French source files, which report
returns in percent.

| Function | Frequency and index | Columns |
| --- | --- | --- |
| `get_ff3` | Monthly `PeriodIndex` | `Mkt-RF`, `SMB`, `HML`, `RF` |
| `get_ff5` | Monthly `PeriodIndex` | `Mkt-RF`, `SMB`, `HML`, `RMW`, `CMA`, `RF` |
| `get_ff3d` | Daily `DatetimeIndex` | `Mkt-RF`, `SMB`, `HML`, `RF` |
| `get_ff5d` | Daily `DatetimeIndex` | `Mkt-RF`, `SMB`, `HML`, `RMW`, `CMA`, `RF` |

The unified loader also returns weekly FF3 data with a weekly `PeriodIndex`:

```python
ff3_weekly = farms.load_ken_french_data(
    "ff3",
    frequency="weekly",
    start_date="2020-01-01",
    end_date="2020-12-31",
)
```

### Examples

```python
# Full available history through the latest available observation
ff3 = farms.get_ff3()

# January 2000 through the latest available observation
ff5 = farms.get_ff5(start_date="2000-01")

# Earliest available history through December 2020
momentum = farms.get_ken_french_deciles(
    "momentum",
    end_date="2020-12",
)
```

Monthly three-factor data:

```python
import farms

ff3 = farms.get_ff3("2000-01", "2025-12")
print(ff3.head())
```

Weekly three-factor data:

```python
ff3_weekly = farms.load_ken_french_data(
    "ff3",
    frequency="weekly",
    start_date="2020-01-01",
    end_date="2025-12-31",
)
print(ff3_weekly.head())
```

Monthly five-factor data:

```python
ff5 = farms.get_ff5("2000-01", "2025-12")
print(ff5.head())
```

Daily three-factor data:

```python
ff3_daily = farms.get_ff3d("2025-01-01", "2025-12-31")
print(ff3_daily.head())
```

Daily five-factor data:

```python
ff5_daily = farms.get_ff5d("2025-01-01", "2025-12-31")
print(ff5_daily.head())
```

The daily five-factor result contains `Mkt-RF`, `SMB`, `HML`, `RMW`, `CMA`,
and `RF`. Dates are optional; supplying only `start_date` retrieves observations
from that date through the latest available observation:

```python
ff5_daily = farms.get_ff5d(start_date="2025-01-01")
```

Monthly and weekly factor data use a pandas `PeriodIndex`. Daily factor data
use a pandas `DatetimeIndex`.

## Kenneth French decile and quintile portfolios

### Inputs

| Parameter | Required | Format and behavior |
| --- | --- | --- |
| `stype` | Yes | A supported strategy below, or `"list"` to print the supported strategies. |
| `start_date` | No | `YYYY-MM`; `None` requests the full available history. |
| `end_date` | No | `YYYY-MM`; `None` requests data through the latest available observation. |
| `factors` | No | `None` (default), `"FF3"`, or `"FF5"`. |

The unified loader accepts `frequency="daily"` for the six strategies with
published daily decile files. For example:

```python
momentum_daily = farms.load_ken_french_data(
    "deciles",
    strategy="momentum",
    frequency="daily",
    start_date="2020-01-01",
    end_date="2020-12-31",
)
```

The legacy `ff3d` and `ff5d` data-type aliases remain accepted for backward
compatibility, but the preferred spelling is `"ff3"` or `"ff5"` with
`frequency="daily"`.
| `details` | No | Set to `True` to print the strategy title, construction details, and available dates. |

### Output

For a strategy, returns a DataFrame with a monthly `PeriodIndex` named `date`.
It contains `Dec 1` through `Dec 10`, plus `mkt-rf` and `rf` by default.
`factors="FF3"` adds `smb` and `hml`; `factors="FF5"` additionally adds
`rmw` and `cma`. With `stype="list"`, the function prints the supported
strategies and returns `None`.

All portfolio-return and factor columns are decimal returns (`0.01` means 1%).

With `details=True`, the function also prints the strategy title,
portfolio-construction details, and the available date range. It still returns
the same DataFrame.

### Examples

Display the available strategies:

```python
farms.get_ken_french_deciles("list")
```

Supported strategies are:

- `accruals`
- `beta`
- `booktomarket`
- `dividendyield`
- `earningsprice`
- `idiosyncraticvariance`
- `investment`
- `momentum`
- `netissuances`
- `profitability`
- `shorttermreversal`
- `size`
- `variance`

Load monthly value-weighted momentum deciles:

```python
momentum = farms.get_ken_french_deciles(
    "momentum",
    start_date="2000-01",
    end_date="2025-12",
)
print(momentum.head())
```

Add all three-factor columns:

```python
momentum_ff3 = farms.get_ken_french_deciles(
    "momentum",
    start_date="2000-01",
    end_date="2025-12",
    factors="FF3",
)
```

Add all five-factor columns:

```python
momentum_ff5 = farms.get_ken_french_deciles(
    "momentum",
    start_date="2000-01",
    end_date="2025-12",
    factors="FF5",
)
```

Print teaching details while retaining the returned DataFrame:

```python
momentum = farms.get_ken_french_deciles(
    "momentum",
    start_date="2000-01",
    end_date="2025-12",
    details=True,
)
```

## Running tests

Install pytest and run the suite from the repository root:

```bash
python -m pip install pytest
python -m pytest
```
