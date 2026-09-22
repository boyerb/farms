from .pipelines.alpha_vantage import format_alpha_vantage
from .pipelines.crsp import get_crsp_msf_by_ids
from .pipelines.Ken_French_library import (
    get_ff3,
    get_ff5,
    get_ff3d,
    get_ff5d,
    get_ken_french_deciles,
    load_ken_french_data,
)

from .tools.black_scholes import black_scholes, implied_volatility
from .tools.portfolio_tools import describe, portfolio_volatility, portfolio_sharpe, EFRS_portfolio, tangent_portfolio
from .tools.stats_tools import intercept, slope, run_ols
from importlib.metadata import version

import pandas as pd
import warnings

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
    "format_alpha_vantage",
    "get_crsp_msf_by_ids",
    "get_ff3",
    "get_ff3d",
    "get_ff5",
    "get_ff5d",
    "get_ken_french_deciles",
    "load_ken_french_data",
    "black_scholes",
    "implied_volatility",
    "describe",
    "portfolio_volatility",
    "portfolio_sharpe",
    "EFRS_portfolio",
    "tangent_portfolio",
    "intercept",
    "slope",
    "run_ols"
]
