# farms

Financial Analysis & Risk Management (`farms`) is a Python toolkit for
teaching and research. It provides a simple interface for downloading
Fama-French factors and portfolio returns from the
[Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).

## Installation

`farms` requires Python 3.11 or newer.

```bash
python -m pip install farms
```

To work on a local checkout, install it in editable mode:

```bash
python -m pip install -e .
```

The data-loading functions require an internet connection when called.

## Alpha Vantage monthly adjusted prices

`format_alpha_vantage` formats a response from Alpha Vantage's
`TIME_SERIES_MONTHLY_ADJUSTED` endpoint. Obtain an API key from
[Alpha Vantage](https://www.alphavantage.co/support/#api-key) before making a
request.

### Inputs

| Parameter | Required | Format and behavior |
| --- | --- | --- |
| `r` | Yes | A `requests.Response` from a successful `TIME_SERIES_MONTHLY_ADJUSTED` request. |
| `start_date` | No | `YYYY-MM`; `None` leaves the lower date bound unbounded. |
| `end_date` | No | `YYYY-MM`; `None` leaves the upper date bound unbounded. The range is inclusive. |

Invalid, reversed, rate-limited, or malformed API responses raise clear
exceptions.

### Output

Returns a DataFrame with a monthly `PeriodIndex` named `date`, sorted
chronologically.

| Column | Description |
| --- | --- |
| `Open`, `High`, `Low`, `Close` | Monthly price fields returned by Alpha Vantage. |
| `Adjusted Close` | Split- and dividend-adjusted monthly closing price. |
| `Volume` | Monthly trading volume. |
| `Dividend Amount` | Dividend amount for the month. |

All output columns are numeric.

### Examples

```python
import os

import farms
import requests

response = requests.get(
    "https://www.alphavantage.co/query",
    params={
        "function": "TIME_SERIES_MONTHLY_ADJUSTED",
        "symbol": "MSFT",
        "apikey": os.environ["ALPHAVANTAGE_API_KEY"],
    },
    timeout=30,
)

monthly = farms.format_alpha_vantage(
    response,
    start_date="2020-01",
    end_date="2020-12",
)
print(monthly.head())
```

## CRSP monthly stock data (WRDS)

`get_crsp_msf_by_ids` loads CRSP Monthly Stock File observations through a
caller-provided [WRDS](https://wrds-www.wharton.upenn.edu/) connection. You
need a WRDS account with access to the CRSP data set. `wrds` is intentionally
not installed as a required `farms` dependency, so install it separately:

```bash
python -m pip install wrds
```

### Inputs

| Parameter | Required | Format and behavior |
| --- | --- | --- |
| `db` | Yes | An open `wrds.Connection` or compatible database wrapper. |
| `identifiers` | Yes | A list of PERMNOs or ticker strings. |
| `start_date` | Yes | `YYYY-MM`; `None` is not supported. |
| `end_date` | Yes | `YYYY-MM`; `None` is not supported. The range is inclusive. |
| `identifier_type` | No | `"permno"` or `"ticker"`. Providing it is recommended to avoid ambiguity. |
| `chunk_size` | No | Positive integer; defaults to `500`. |

The date range refers to complete calendar months. For example,
`start_date="2020-01"` and `end_date="2020-03"` returns observations from
January through March 2020.

### Output

Returns a DataFrame with a monthly `PeriodIndex` named `date`, sorted
chronologically. Columns include PERMNO, PERMCO, ticker, company/name-history
fields, and CRSP price, return, volume, and shares-outstanding fields.
`ret` and `retx` are decimal returns (`0.01` means 1%). `prc` follows the
CRSP price sign convention, `vol` is trading volume, and `shrout` is reported
by CRSP in thousands of shares.

### Examples

Query by PERMNO:

```python
import farms
import wrds

db = wrds.Connection()
monthly = farms.get_crsp_msf_by_ids(
    db,
    identifiers=[14593, 12079],
    start_date="2020-01",
    end_date="2020-12",
    identifier_type="permno",
)
```

Or query by ticker:

```python
monthly = farms.get_crsp_msf_by_ids(
    db,
    identifiers=["AAPL", "MSFT"],
    start_date="2020-01",
    end_date="2020-12",
    identifier_type="ticker",
)
db.close()
```

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
