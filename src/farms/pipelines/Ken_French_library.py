import pandas as pd
from pandas_datareader import data as web


_FACTOR_DATASETS = {
    "ff3": {
        "monthly": {
            "dataset": "F-F_Research_Data_Factors",
            "table": 0,
        },
        "daily": {
            "dataset": "F-F_Research_Data_Factors_daily",
            "table": 0,
        },
    },
    "ff5": {
        "monthly": {
            "dataset": "F-F_Research_Data_5_Factors_2x3",
            "table": 0,
        },
        "daily": {
            "dataset": "F-F_Research_Data_5_Factors_2x3_daily",
            "table": 0,
        },
    },
}


_DECILE_DATASETS = {
    "accruals": {
        "dataset": "Portfolios_Formed_on_AC",
        "title": "Accruals",
        "table": 0,
    },
    "beta": {
        "dataset": "Portfolios_Formed_on_BETA",
        "title": "Beta",
        "table": 0,
    },
    "booktomarket": {
        "dataset": "Portfolios_Formed_on_BE-ME",
        "title": "Book-to-Market",
        "table": 0,
    },
    "dividendyield": {
        "dataset": "Portfolios_Formed_on_D-P",
        "title": "Dividend Yield",
        "table": 0,
    },
    "earningsprice": {
        "dataset": "Portfolios_Formed_on_E-P",
        "title": "Earnings-to-Price",
        "table": 0,
    },
    "idiosyncraticvariance": {
        "dataset": "Portfolios_Formed_on_RESVAR",
        "title": "Idiosyncratic Variance",
        "table": 0,
    },
    "investment": {
        "dataset": "Portfolios_Formed_on_INV",
        "title": "Investment",
        "table": 0,
    },
    "momentum": {
        "dataset": "10_Portfolios_Prior_12_2",
        "title": "Momentum",
        "table": 0,
    },
    "netissuances": {
        "dataset": "Portfolios_Formed_on_NI",
        "title": "Net Share Issuances",
        "table": 0,
    },
    "profitability": {
        "dataset": "Portfolios_Formed_on_OP",
        "title": "Profitability",
        "table": 0,
    },
    "shorttermreversal": {
        "dataset": "10_Portfolios_Prior_1_0",
        "title": "Short-Term Reversal",
        "table": 0,
    },
    "size": {
        "dataset": "Portfolios_Formed_on_ME",
        "title": "Size",
        "table": 0,
    },
    "variance": {
        "dataset": "Portfolios_Formed_on_VAR",
        "title": "Variance",
        "table": 0,
    },
}

_DECILE_COLUMNS = [
    "Lo 10",
    *[f"Dec {number}" for number in range(2, 10)],
    "Hi 10",
]

_DECILE_OUTPUT_COLUMNS = [f"Dec {number}" for number in range(1, 11)]
_DECILE_SOURCE_ALIASES = {
    "Dec 1": ("Lo 10", "Lo PRIOR", "Dec 1", "PRIOR 1"),
    **{
        f"Dec {number}": (
            f"{number}-Dec",
            f"Dec {number}",
            f"PRIOR {number}",
        )
        for number in range(2, 10)
    },
    "Dec 10": ("Hi 10", "Hi PRIOR", "Dec 10", "PRIOR 10"),
}

_PORTFOLIO_VIEWS = {
    "deciles": {
        "count": 10,
        "prefix": "Dec",
        "source_columns": _DECILE_COLUMNS,
        "output_columns": _DECILE_OUTPUT_COLUMNS,
    },
    "quintiles": {
        "count": 5,
        "prefix": "Qnt",
        "source_columns": [
            "Lo 20",
            "Qnt 2",
            "Qnt 3",
            "Qnt 4",
            "Hi 20",
        ],
        "output_columns": [f"Qnt {number}" for number in range(1, 6)],
    },
}

_QUINTILE_DATASETS = {
    strategy: config
    for strategy, config in _DECILE_DATASETS.items()
    if strategy not in {"momentum", "shorttermreversal"}
}


def _load_french_dataset(dataset, start_date=None, end_date=None):
    """Load a dataset from the Kenneth French Data Library."""
    # pandas-datareader otherwise defaults to only five years of history.
    # The original farms loaders returned the complete French time series.
    reader_start = "1900-01-01" if start_date is None else start_date
    return web.DataReader(
        dataset,
        "famafrench",
        start=reader_start,
        end=end_date,
    )


def _inspect_french_dataset(dataset, start_date=None, end_date=None):
    """Return table metadata for a pandas-datareader French dataset."""
    result = _load_french_dataset(dataset, start_date, end_date)
    tables = {}

    for key, value in result.items():
        if isinstance(key, int) and isinstance(value, pd.DataFrame):
            tables[key] = {
                "rows": len(value),
                "columns": list(value.columns),
                "index_type": type(value.index).__name__,
                "index_frequency": getattr(value.index, "freqstr", None),
            }

    return {
        "dataset": dataset,
        "description": result.get("DESCR", ""),
        "tables": tables,
    }


def _load_decile_returns(strategy, start_date=None, end_date=None):
    """Return monthly value-weighted decile returns for a strategy."""
    try:
        config = _DECILE_DATASETS[strategy]
    except KeyError as exc:
        choices = ", ".join(sorted(_DECILE_DATASETS))
        raise ValueError(
            f"Unknown decile strategy {strategy!r}. Choose one of: {choices}."
        ) from exc

    result = _load_french_dataset(
        config["dataset"],
        start_date,
        end_date,
    )
    table = result[config["table"]].copy()

    source_columns, missing_columns = _resolve_portfolio_source_columns(
        table,
        "deciles",
    )
    if missing_columns:
        raise ValueError(
            f"{config['dataset']} table {config['table']} is missing expected "
            f"decile columns: {', '.join(missing_columns)}."
        )

    deciles = table.loc[:, source_columns].copy()
    deciles.columns = _DECILE_OUTPUT_COLUMNS
    deciles = deciles.apply(pd.to_numeric, errors="coerce") / 100
    deciles.index.name = "date"
    return deciles


def _resolve_portfolio_source_columns(table, granularity, strategy=None):
    """Resolve source column aliases into the canonical portfolio order."""
    def normalize_column_name(column):
        if isinstance(column, tuple):
            parts = [normalize_column_name(part) for part in column]
            return " ".join(part for part in parts if part)
        return " ".join(str(column).strip().split())

    if granularity == "deciles":
        aliases = _DECILE_SOURCE_ALIASES
    else:
        aliases = {
            column: (column,)
            for column in _PORTFOLIO_VIEWS[granularity]["source_columns"]
        }

    table_columns = {
        normalize_column_name(column): column for column in table.columns
    }
    source_columns = []
    missing_columns = []
    for output_column, candidates in aliases.items():
        source_column = next(
            (
                table_columns[normalize_column_name(candidate)]
                for candidate in candidates
                if normalize_column_name(candidate) in table_columns
            ),
            None,
        )
        if source_column is None:
            missing_columns.append(output_column)
        else:
            source_columns.append(source_column)
    return source_columns, missing_columns


def _load_factor_returns(model, frequency, start_date=None, end_date=None):
    """Load and normalize a registered Fama-French factor dataset."""
    try:
        config = _FACTOR_DATASETS[model][frequency]
    except KeyError as exc:
        supported_models = ", ".join(sorted(_FACTOR_DATASETS))
        raise ValueError(
            f"Unsupported factor selection {model!r} at {frequency!r} "
            f"frequency. Choose a model from: {supported_models}."
        ) from exc

    result = _load_french_dataset(
        config["dataset"],
        start_date,
        end_date,
    )
    df = result[config["table"]].copy()
    df = df.apply(pd.to_numeric, errors="coerce") / 100

    if frequency == "daily":
        if isinstance(df.index, pd.PeriodIndex):
            df.index = df.index.to_timestamp()
        df.index.freq = None

    df.index.name = "date"
    return df


def _load_weighted_portfolio_returns(
    granularity,
    strategy,
    weighting="value",
    start_date=None,
    end_date=None,
):
    """Load registered portfolio returns for the requested view and weighting."""
    if granularity == "deciles" and weighting == "value":
        return _load_decile_returns(strategy, start_date, end_date)

    if weighting not in {"value", "equal"}:
        raise ValueError("weighting must be 'value' or 'equal'.")

    datasets = {
        "deciles": _DECILE_DATASETS,
        "quintiles": _QUINTILE_DATASETS,
    }
    try:
        config = datasets[granularity][strategy]
    except KeyError as exc:
        choices = ", ".join(sorted(datasets[granularity]))
        raise ValueError(
            f"Unknown {granularity[:-1]} strategy {strategy!r}. "
            f"Choose one of: {choices}."
        ) from exc

    result = _load_french_dataset(
        config["dataset"],
        start_date,
        end_date,
    )
    table_number = config["table"] if weighting == "value" else 1
    if table_number not in result:
        raise ValueError(
            f"{config['dataset']} does not provide the requested "
            f"{weighting}-weighted {granularity} table at index {table_number}."
        )

    view = _PORTFOLIO_VIEWS[granularity]
    table = result[table_number].copy()
    source_columns, missing_columns = _resolve_portfolio_source_columns(
        table,
        granularity,
    )
    if missing_columns:
        raise ValueError(
            f"{config['dataset']} table {table_number} is missing expected "
            f"{granularity} columns: {', '.join(missing_columns)}."
        )

    portfolios = table.loc[:, source_columns].copy()
    portfolios.columns = view["output_columns"]
    portfolios = portfolios.apply(pd.to_numeric, errors="coerce") / 100
    portfolios.index.name = "date"
    return portfolios


def _select_portfolios(data, portfolio, view):
    """Select one or more canonical portfolio columns."""
    if portfolio is None or (
        isinstance(portfolio, str) and portfolio.lower() == "all"
    ):
        return data

    count = view["count"]
    prefix = view["prefix"]

    if isinstance(portfolio, str):
        aliases = {"low": 1, "high": count}
        try:
            portfolio_numbers = [aliases[portfolio.lower()]]
        except KeyError as exc:
            raise ValueError(
                "portfolio must be an integer, a sequence of integers, "
                "'low', 'high', or 'all'."
            ) from exc
    elif isinstance(portfolio, int) and not isinstance(portfolio, bool):
        portfolio_numbers = [portfolio]
    else:
        try:
            portfolio_numbers = list(portfolio)
        except TypeError as exc:
            raise ValueError(
                "portfolio must be an integer, a sequence of integers, "
                "'low', 'high', or 'all'."
            ) from exc

    if not portfolio_numbers or any(
        not isinstance(number, int) or isinstance(number, bool)
        or not 1 <= number <= count
        for number in portfolio_numbers
    ):
        raise ValueError(
            f"portfolio numbers must be integers from 1 through {count}."
        )

    columns = [f"{prefix} {number}" for number in portfolio_numbers]
    return data.loc[:, columns]


def load_ken_french_data(
    data_type,
    strategy=None,
    *,
    frequency="monthly",
    start_date=None,
    end_date=None,
    portfolio=None,
    weighting="value",
    include_factors=None,
    details=False,
):
    """Load normalized data from the Kenneth French Data Library.

    Parameters
    ----------
    data_type : {"ff3", "ff5", "deciles", "quintiles"}
        Select a factor model or portfolio granularity. The aliases ``ff3d``
        and ``ff5d`` are also accepted and select daily frequency.
    strategy : str, optional
        Portfolio sorting strategy, such as ``"momentum"`` or ``"size"``.
        Required for portfolio data and invalid for factor data.
    frequency : {"monthly", "daily"}, default "monthly"
        Factor frequency. Current portfolio datasets are monthly.
    portfolio : int, sequence of int, {"low", "high", "all"}, optional
        Portfolio selection. ``None`` and ``"all"`` return every portfolio.
    weighting : {"value", "equal"}, default "value"
        Portfolio weighting convention.
    include_factors : {None, "market", "ff3", "ff5"}, optional
        Additional monthly factors to merge into portfolio data. ``None``
        leaves the portfolio data unchanged; ``"market"`` adds ``mkt-rf``
        and ``rf``.
    details : bool, default False
        Print portfolio construction details when available.
    """
    normalized_type = str(data_type).lower()
    if normalized_type in {"ff3d", "ff5d"}:
        if frequency not in {"monthly", "daily"}:
            raise ValueError("frequency must be 'monthly' or 'daily'.")
        normalized_type = normalized_type[:3]
        frequency = "daily"

    if normalized_type in _FACTOR_DATASETS:
        if strategy is not None:
            raise ValueError("strategy is only valid for portfolio data.")
        if portfolio is not None:
            raise ValueError("portfolio is only valid for portfolio data.")
        if weighting != "value":
            raise ValueError("weighting is only valid for portfolio data.")
        if include_factors is not None:
            raise ValueError("include_factors is only valid for portfolio data.")
        if frequency not in {"monthly", "daily"}:
            raise ValueError("frequency must be 'monthly' or 'daily'.")
        return _load_factor_returns(
            normalized_type,
            frequency,
            start_date,
            end_date,
        )

    if normalized_type not in {"deciles", "quintiles"}:
        choices = ", ".join(
            ["ff3", "ff5", "deciles", "quintiles"]
        )
        raise ValueError(
            f"Unknown Kenneth French data_type {data_type!r}. Choose one of: "
            f"{choices}."
        )
    if strategy is None:
        raise ValueError("strategy is required for portfolio data.")
    if frequency != "monthly":
        raise ValueError("Current Kenneth French portfolio data is monthly only.")
    view = _PORTFOLIO_VIEWS[normalized_type]
    data = _load_weighted_portfolio_returns(
        normalized_type,
        strategy,
        weighting,
        start_date,
        end_date,
    )

    if details is True:
        metadata = _get_decile_metadata(strategy, data)
        _print_decile_details(metadata)

    data = _select_portfolios(data, portfolio, view)

    if include_factors is None:
        return data
    normalized_factors = str(include_factors).lower()
    if normalized_factors == "market":
        factors = None
    elif normalized_factors in {"ff3", "ff5"}:
        factors = normalized_factors.upper()
    else:
        raise ValueError(
            "include_factors must be None, 'market', 'ff3', or 'ff5'."
        )
    return _merge_decile_factors(data, factors, start_date, end_date)


def get_ff3(start_date=None, end_date=None):
    """Return monthly Fama-French three-factor data as decimal returns."""
    return load_ken_french_data(
        "ff3",
        start_date=start_date,
        end_date=end_date,
    )


def get_ff5(start_date=None, end_date=None):
    """Return monthly Fama-French five-factor data as decimal returns."""
    return load_ken_french_data(
        "ff5",
        start_date=start_date,
        end_date=end_date,
    )


def get_ff3d(start_date=None, end_date=None):
    """Return daily Fama-French three-factor data as decimal returns."""
    return load_ken_french_data(
        "ff3",
        frequency="daily",
        start_date=start_date,
        end_date=end_date,
    )


def get_ff5d(start_date=None, end_date=None):
    """Return daily Fama-French five-factor data as decimal returns."""
    return load_ken_french_data(
        "ff5",
        frequency="daily",
        start_date=start_date,
        end_date=end_date,
    )

_DECILE_DETAILS = {
    "accruals": (
        "The portfolios are formed on accruals at the end of each June using NYSE breakpoints.",
        "Accruals measure the change in operating working capital per split-adjusted share, "
        "scaled by book equity per share.",
        "Stocks are sorted into deciles, and each portfolio is value-weighted.",
    ),
    "beta": (
        "Stocks are sorted into deciles based on historical market betas.",
        "Portfolios are formed at the end of each June using NYSE breakpoints.",
        "Beta uses the preceding five years of monthly returns, with a two-year minimum.",
    ),
    "booktomarket": (
        "Portfolios are formed on book equity to market equity (BE/ME) at the end of "
        "each June using NYSE breakpoints.",
        "Book equity comes from the prior fiscal year; market equity is measured at "
        "the end of the prior December.",
    ),
    "dividendyield": (
        "Portfolios are formed on dividend yield (D/P) at the end of each June using "
        "NYSE breakpoints.",
        "Dividend yield is dividends paid from July through June per dollar of June "
        "market equity.",
    ),
    "earningsprice": (
        "Portfolios are formed on earnings-to-price (E/P) at the end of each June "
        "using NYSE breakpoints.",
        "Earnings come from the prior fiscal year, and price is represented by market equity.",
    ),
    "idiosyncraticvariance": (
        "Portfolios are formed monthly on residual-return variance using NYSE breakpoints.",
        "Residual variance is estimated from the Fama-French three-factor model using "
        "60 lagged trading days, with a 20-day minimum.",
    ),
    "investment": (
        "Investment is the change in total assets from fiscal year t-2 to t-1, "
        "divided by total assets in t-2.",
        "Deciles are formed using NYSE breakpoints.",
    ),
    "momentum": (
        "Stocks are sorted into deciles on prior returns from months t-12 through t-2.",
        "Portfolios are formed monthly using NYSE breakpoints and are value-weighted.",
    ),
    "netissuances": (
        "Portfolios are formed on net share issuance at the end of each June using "
        "NYSE breakpoints.",
        "Net issuance is the change in log split-adjusted shares outstanding between "
        "the prior two fiscal year ends.",
    ),
    "profitability": (
        "Portfolios are formed on operating profitability at the end of each June "
        "using NYSE breakpoints.",
        "Operating profitability is revenues less cost of goods sold, interest, and "
        "selling, general, and administrative expenses, divided by book equity.",
    ),
    "shorttermreversal": (
        "Stocks are sorted into deciles based on their prior one-month return.",
        "Portfolios are formed monthly using NYSE breakpoints and are value-weighted.",
    ),
    "size": (
        "Size deciles are formed at the end of each June using June market equity "
        "and NYSE breakpoints.",
    ),
    "variance": (
        "Portfolios are formed monthly on daily-return variance using NYSE breakpoints.",
        "Variance is estimated using 60 lagged trading days, with a 20-day minimum.",
    ),
}


def _get_decile_metadata(strategy, deciles):
    """Return structured teaching metadata for a decile strategy."""
    config = _DECILE_DATASETS[strategy]
    return {
        "strategy": strategy,
        "title": config["title"],
        "dataset": config["dataset"],
        "table": config["table"],
        "description": list(_DECILE_DETAILS[strategy]),
        "min_date": deciles.index.min(),
        "max_date": deciles.index.max(),
    }


def _print_decile_details(metadata):
    """Print structured decile metadata in a student-friendly format."""
    separator = "-" * max(16, len(metadata["title"]))
    print(separator)
    print(metadata["title"])
    print(separator)
    for line in metadata["description"]:
        print(line)
    print()
    print(
        f"Min Date: {metadata['min_date']}, "
        f"Max Date: {metadata['max_date']}"
    )


def _merge_decile_factors(deciles, factors=None, start_date=None, end_date=None):
    """Merge requested Fama-French factors into monthly decile returns."""
    if factors not in {None, "FF3", "FF5"}:
        raise ValueError("factors must be None, 'FF3', or 'FF5'.")

    if factors == "FF5":
        factor_data = get_ff5(start_date, end_date).rename(
            columns={
                "Mkt-RF": "mkt-rf",
                "SMB": "smb",
                "HML": "hml",
                "RMW": "rmw",
                "CMA": "cma",
                "RF": "rf",
            }
        )
        factor_columns = ["mkt-rf", "smb", "hml", "rmw", "cma", "rf"]
    elif factors == "FF3":
        factor_data = get_ff3(start_date, end_date).rename(
            columns={
                "Mkt-RF": "mkt-rf",
                "SMB": "smb",
                "HML": "hml",
                "RF": "rf",
            }
        )
        factor_columns = ["mkt-rf", "smb", "hml", "rf"]
    else:
        factor_data = get_ff3(start_date, end_date).rename(
            columns={"Mkt-RF": "mkt-rf", "RF": "rf"}
        )
        factor_columns = ["mkt-rf", "rf"]

    return deciles.merge(
        factor_data[factor_columns],
        left_index=True,
        right_index=True,
        how="inner",
    )


def get_ken_french_deciles(
    stype,
    start_date=None,
    end_date=None,
    details=None,
    factors=None,
):
    """Return monthly value-weighted Kenneth French decile portfolios."""
    if stype == "list":
        for strategy in _DECILE_DATASETS:
            print(strategy)
        return None

    if factors not in {None, "FF3", "FF5"}:
        raise ValueError("factors must be None, 'FF3', or 'FF5'.")

    # Preserve the legacy default: this wrapper includes market excess return
    # and the risk-free rate when factors is omitted. The new unified loader
    # leaves portfolio data unchanged unless include_factors is requested.
    include_factors = "market" if factors is None else factors
    return load_ken_french_data(
        "deciles",
        strategy=stype,
        start_date=start_date,
        end_date=end_date,
        include_factors=include_factors,
        details=details is True,
    )
