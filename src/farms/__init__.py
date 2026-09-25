import warnings
from importlib.metadata import version

import pandas as pd

from .pipelines.alpha_vantage import (
    AlphaVantageError,
    AlphaVantageRateLimitError,
    AlphaVantageResponseError,
    format_alpha_vantage,
    format_alpha_vantage_daily,
    format_alpha_vantage_time_series,
    format_alpha_vantage_weekly,
    load_alpha_vantage_daily,
    load_alpha_vantage_monthly,
    load_alpha_vantage_weekly,
)
from .pipelines.crsp import (
    get_crsp_msf_by_ids,
    load_all_crsp_data,
    load_crsp_data,
)
from .pipelines.Ken_French_library import (
    get_ff3,
    get_ff3d,
    get_ff5,
    get_ff5d,
    get_ken_french_deciles,
    list_ken_french_data,
    load_ken_french_data,
)
from .tools.black_scholes import black_scholes, implied_volatility
from .tools.portfolio_tools import (
    EFRS_portfolio,
    describe,
    portfolio_sharpe,
    portfolio_volatility,
    tangent_portfolio,
)
from .tools.stats_tools import intercept, run_ols, slope

warnings.filterwarnings(
    "ignore",
    message="pandas only supports SQLAlchemy connectable.*",
    category=UserWarning,
)

pd.set_option('display.max_rows', None)  # Show all rows
pd.set_option('display.max_columns', None)  # Show all columns
pd.set_option('display.width', None)  # Adjust width to fit the output
pd.set_option('display.max_colwidth', None)  # Show full column content without truncation

__version__ = version("farms")

__all__ = [
    "AlphaVantageError",
    "AlphaVantageRateLimitError",
    "AlphaVantageResponseError",
    "EFRS_portfolio",
    "black_scholes",
    "describe",
    "format_alpha_vantage",
    "format_alpha_vantage_daily",
    "format_alpha_vantage_time_series",
    "format_alpha_vantage_weekly",
    "get_crsp_msf_by_ids",
    "get_ff3",
    "get_ff3d",
    "get_ff5",
    "get_ff5d",
    "get_ken_french_deciles",
    "implied_volatility",
    "intercept",
    "list_ken_french_data",
    "load_all_crsp_data",
    "load_alpha_vantage_daily",
    "load_alpha_vantage_monthly",
    "load_alpha_vantage_weekly",
    "load_crsp_data",
    "load_ken_french_data",
    "portfolio_sharpe",
    "portfolio_volatility",
    "run_ols",
    "slope",
    "tangent_portfolio"
]
