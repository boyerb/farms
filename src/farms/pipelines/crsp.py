import math
import re
from numbers import Integral, Real
from typing import Iterable, List, Literal, Union

import pandas as pd

from .Ken_French_library import load_ken_french_data


_RESULT_COLUMNS = [
    "permno",
    "permco",
    "ticker",
    "comnam",
    "shrcd",
    "exchcd",
    "siccd",
    "prc",
    "ret",
    "retx",
    "vol",
    "shrout",
]

_EMPTY_RESULT_DTYPES = {
    "permno": "Int64",
    "permco": "Int64",
    "ticker": "string",
    "comnam": "string",
    "shrcd": "Int64",
    "exchcd": "Int64",
    "siccd": "Int64",
    "prc": "Float64",
    "ret": "Float64",
    "retx": "Float64",
    "vol": "Float64",
    "shrout": "Float64",
}

_CRSP_FACTOR_COLUMNS = {
    "Mkt-RF": "ff_mkt_rf",
    "SMB": "ff_smb",
    "HML": "ff_hml",
    "RMW": "ff_rmw",
    "CMA": "ff_cma",
    "RF": "ff_rf",
}


def _merge_crsp_factors(
    data: pd.DataFrame,
    start_date: str,
    end_date: str,
    frequency: Literal["monthly", "daily"],
    include_factors: Literal["none", "market", "ff3", "ff5"] | None,
) -> pd.DataFrame:
    """Merge requested decimal Fama-French returns onto CRSP observations."""
    if include_factors is None:
        return data

    selection = str(include_factors).lower()
    if selection == "none":
        return data
    if selection not in {"market", "ff3", "ff5"}:
        raise ValueError(
            "include_factors must be None, 'none', 'market', 'ff3', or 'ff5'."
        )

    model = "ff3" if selection == "market" else selection
    factor_data = load_ken_french_data(
        model,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
    ).rename(columns=_CRSP_FACTOR_COLUMNS)

    if selection == "market":
        factor_columns = ["ff_mkt_rf", "ff_rf"]
    elif selection == "ff3":
        factor_columns = ["ff_mkt_rf", "ff_smb", "ff_hml", "ff_rf"]
    else:
        factor_columns = [
            "ff_mkt_rf",
            "ff_smb",
            "ff_hml",
            "ff_rmw",
            "ff_cma",
            "ff_rf",
        ]

    missing_columns = [
        column for column in factor_columns if column not in factor_data.columns
    ]
    if missing_columns:
        raise ValueError(
            "Ken French factor data is missing required columns: "
            + ", ".join(missing_columns)
        )

    return data.join(factor_data[factor_columns], how="left")


def load_crsp_data(
    db,
    identifiers: Iterable[Union[str, int]],
    start_date: str,
    end_date: str,
    chunk_size: int = 500,
    identifier_type: Literal["permno", "ticker"] | None = None,
    frequency: Literal["monthly", "daily"] = "monthly",
    include_factors: Literal["none", "market", "ff3", "ff5"] | None = None,
) -> pd.DataFrame:

    """
    Pull CRSP monthly or daily stock-file data for TICKERS or PERMNOs.

    Parameters
    ----------
    identifiers : iterable of str|int
        Either all tickers (e.g., ['AAPL','MSFT']) or all PERMNOs (e.g., [14593, 12079]).
        Mixed types are not allowed when ``identifier_type`` is omitted.
        A scalar string is not accepted; pass it as a one-element iterable.
    identifier_type : {'permno', 'ticker'}, optional
        Explicitly select how to interpret ``identifiers``. When omitted, the
        type is inferred only from a homogeneous list of integers or strings.
    start_date, end_date : str
        Required, inclusive date range to filter `a.date`. Use ``YYYY-MM``
        for monthly data or ``YYYY-MM-DD`` for daily data.
    chunk_size : int
        Max identifiers per SQL IN() chunk to avoid overly long queries.
    frequency : {'monthly', 'daily'}
        Select CRSP Monthly Stock File (``crspm.msf``) or Daily Stock File
        (``crsp.dsf``). Defaults to ``"monthly"``.
    include_factors : {None, 'none', 'market', 'ff3', 'ff5'}, optional
        Merge Ken French decimal returns at the matching frequency. ``'market'``
        adds ``ff_mkt_rf`` and ``ff_rf``; ``'ff3'`` adds those plus ``ff_smb``
        and ``ff_hml``; ``'ff5'`` adds ``ff_rmw`` and ``ff_cma`` as well.
        ``None`` and ``'none'`` leave the CRSP data unchanged.

    Returns
    -------
    pandas.DataFrame
        A chronologically sorted date index named ``date`` and columns:
        permno, permco, ticker, comnam, shrcd, exchcd, siccd, prc, ret, retx,
        vol, shrout, and any requested prefixed Ken French factor columns.
        Monthly results use a PeriodIndex; daily results use a DatetimeIndex.
        Ticker lookups use historical CRSP name records and may return multiple
        PERMNOs when a ticker was reused over time.
    """
    
    # Establish the connection object
    con = db.connection
    if hasattr(con, "connection"):
        con = con.connection
    
    if (
        not isinstance(chunk_size, Integral)
        or isinstance(chunk_size, bool)
        or chunk_size <= 0
    ):
        raise ValueError("chunk_size must be a positive integer.")

    if frequency not in {"monthly", "daily"}:
        raise ValueError("frequency must be either 'monthly' or 'daily'.")

    date_pattern = r"\d{4}-\d{2}" if frequency == "monthly" else r"\d{4}-\d{2}-\d{2}"
    expected_date_format = "YYYY-MM" if frequency == "monthly" else "YYYY-MM-DD"
    if not all(
        isinstance(value, str) and re.fullmatch(date_pattern, value)
        for value in (start_date, end_date)
    ):
        raise ValueError(f"start_date and end_date must be in '{expected_date_format}' format.")

    try:
        if frequency == "monthly":
            start_period = pd.Period(start_date, freq="M")
            end_period = pd.Period(end_date, freq="M")
            if start_period > end_period:
                raise ValueError("start_date must not be after end_date.")
            start = start_period.start_time
            end_exclusive = (end_period + 1).start_time
        else:
            start = pd.Timestamp(start_date).normalize()
            end = pd.Timestamp(end_date).normalize()
            if start > end:
                raise ValueError("start_date must not be after end_date.")
            end_exclusive = end + pd.Timedelta(1, unit="D")
    except ValueError as error:
        if str(error) == "start_date must not be after end_date.":
            raise
        raise ValueError(
            f"start_date and end_date must be in '{expected_date_format}' format."
        ) from error

    # Normalize identifiers and auto-detect type
    if isinstance(identifiers, (str, bytes)):
        raise ValueError(
            "identifiers must be an iterable of identifiers; "
            "pass a scalar identifier as a one-element list."
        )
    try:
        ids_list: List[Union[str, int]] = list(identifiers)
    except TypeError as error:
        raise ValueError("identifiers must be an iterable of identifiers.") from error
    if not ids_list:
        raise ValueError("identifiers list is empty.")

    def is_permno_value(value: object) -> bool:
        return (
            isinstance(value, Integral)
            and not isinstance(value, bool)
        ) or (isinstance(value, str) and value.strip().isdigit())

    if identifier_type is not None and identifier_type not in {"permno", "ticker"}:
        raise ValueError("identifier_type must be either 'permno' or 'ticker'.")

    if identifier_type is None:
        all_integers = all(
            isinstance(value, Integral) and not isinstance(value, bool)
            for value in ids_list
        )
        all_strings = all(isinstance(value, str) for value in ids_list)

        if all_integers:
            id_type = "permno"
        elif all_strings:
            id_type = "permno" if all(is_permno_value(value) for value in ids_list) else "ticker"
        else:
            raise ValueError(
                "Mixed identifier types are ambiguous; pass identifier_type explicitly."
            )
    else:
        id_type = identifier_type

    if id_type == "permno":
        if not all(is_permno_value(value) for value in ids_list):
            raise ValueError("PERMNO identifiers must be integers or digit-only strings.")
        ids_list = [int(value) for value in ids_list]
        if any(value <= 0 for value in ids_list):
            raise ValueError("PERMNO identifiers must be positive integers.")
    else:
        if not all(isinstance(value, str) for value in ids_list):
            raise ValueError("Ticker identifiers must be strings.")
        ids_list = [value.strip().upper() for value in ids_list]
        if any(not value for value in ids_list):
            raise ValueError("Ticker identifiers must not be empty.")
    # Preserve the caller's first-seen order while avoiding duplicate queries
    # and duplicate rows when repeated identifiers span multiple chunks.
    ids_list = list(dict.fromkeys(ids_list))

    if frequency == "monthly":
        data_table = "crspm.msf"
        names_table = "crspm.msenames"
    else:
        data_table = "crsp.dsf"
        names_table = "crsp.dsenames"

    # Base SELECT/JOIN and date validity join to the corresponding names table.
    base_sql = f"""
        SELECT 
            a.date, 
            a.permno,
            a.permco, 
            b.ticker, 
            b.comnam, 
            b.shrcd, 
            b.exchcd, 
            b.siccd, 
            a.prc, 
            a.ret, 
            a.retx, 
            a.vol, 
            a.shrout
        FROM {data_table} a
        INNER JOIN {names_table} b
            ON a.permno = b.permno
        WHERE a.date >= b.namedt 
          AND a.date <= b.nameendt
          AND a.date >= %s
          AND a.date < %s
    """

    # Build WHERE clause chunks
    def chunk(seq, n):
        for i in range(0, len(seq), n):
            yield seq[i:i+n]

    dfs = []

    for sub in chunk(ids_list, chunk_size):
        placeholders = ", ".join(["%s"] * len(sub))
        if id_type == "permno":
            where_ids = f" AND a.permno IN ({placeholders})"
        else:
            where_ids = f" AND b.ticker IN ({placeholders})"

        sql = base_sql + where_ids
        params = [start, end_exclusive, *sub]
        dfs.append(pd.read_sql_query(sql, con, params=params))

    out = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    if out.empty:
        out = pd.DataFrame(
            {
                column: pd.Series(dtype=dtype)
                for column, dtype in _EMPTY_RESULT_DTYPES.items()
            }
        )
        if frequency == "monthly":
            out.index = pd.PeriodIndex([], freq="M", name="date")
        else:
            out.index = pd.DatetimeIndex([], name="date")
        return _merge_crsp_factors(
            out, start_date, end_date, frequency, include_factors
        )

    if out.duplicated(subset=["date", "permno"]).any():
        raise RuntimeError(
            "CRSP query returned multiple rows for at least one "
            "(date, permno) pair; check the msenames validity join."
        )

    out = out.sort_values(["date", "permno"]).reset_index(drop=True).copy()
    dates = pd.to_datetime(out["date"])
    if frequency == "monthly":
        date_periods = dates.dt.to_period("M")
        out.index = pd.PeriodIndex(date_periods, freq="M", name="date")
    else:
        out.index = pd.DatetimeIndex(dates, name="date")
    return _merge_crsp_factors(
        out.drop(columns=["date"]),
        start_date,
        end_date,
        frequency,
        include_factors,
    )


def load_all_crsp_data(
    db,
    start_date: str,
    end_date: str,
    frequency: Literal["monthly", "daily"] = "monthly",
    *,
    share_codes: Iterable[int] | None = None,
    market_cap_min: Real | None = None,
    market_cap_max: Real | None = None,
    price_min: Real | None = None,
    price_max: Real | None = None,
    include_factors: Literal["none", "market", "ff3", "ff5"] | None = None,
) -> pd.DataFrame:
    """Load CRSP data for all securities in a monthly or daily date range.

    Screens are evaluated using information observable at the beginning of
    each return period. For monthly data, this means the prior month-end. For
    daily data, this means the most recent prior CRSP trading observation.

    Parameters
    ----------
    db : object
        An open WRDS connection or compatible database wrapper.
    start_date, end_date : str
        ``YYYY-MM`` for monthly data or ``YYYY-MM-DD`` for daily data. The
        requested range is inclusive.
    frequency : {'monthly', 'daily'}
        Select CRSP Monthly Stock File (``crspm.msf``) or Daily Stock File
        (``crsp.dsf``).
    include_factors : {None, 'none', 'market', 'ff3', 'ff5'}, optional
        Merge Ken French decimal returns at the matching frequency. ``'market'``
        adds ``ff_mkt_rf`` and ``ff_rf``; ``'ff3'`` adds those plus ``ff_smb``
        and ``ff_hml``; ``'ff5'`` adds ``ff_rmw`` and ``ff_cma`` as well.
        ``None`` and ``'none'`` leave the CRSP data unchanged.
    share_codes : iterable of int, optional
        Restrict observations to securities whose share code at the beginning
        of the period is in this collection. Use ``(10, 11)`` for common
        stocks.
    market_cap_min, market_cap_max : real, optional
        Strict lower and upper bounds, in dollars, for beginning-of-period
        market capitalization. Market cap is calculated as
        ``abs(prc) * shrout * 1000``.
    price_min, price_max : real, optional
        Strict lower and upper bounds, in dollars, for beginning-of-period
        absolute CRSP price. CRSP may store negative prices as a sign
        convention, so screens use ``abs(prc)``.

    Returns
    -------
    pandas.DataFrame
        The standard CRSP columns returned by :func:`load_crsp_data`. Monthly
        results have a monthly ``PeriodIndex`` named ``date``; daily results
        have a ``DatetimeIndex`` named ``date``.

    Notes
    -----
    The function returns a potentially very large DataFrame. Keep date ranges
    bounded and apply screens when possible.
    """

    if frequency not in {"monthly", "daily"}:
        raise ValueError("frequency must be either 'monthly' or 'daily'.")

    date_pattern = r"\d{4}-\d{2}" if frequency == "monthly" else r"\d{4}-\d{2}-\d{2}"
    if not all(
        isinstance(value, str) and re.fullmatch(date_pattern, value)
        for value in (start_date, end_date)
    ):
        expected = "YYYY-MM" if frequency == "monthly" else "YYYY-MM-DD"
        raise ValueError(f"start_date and end_date must be in '{expected}' format.")

    try:
        if frequency == "monthly":
            start_period = pd.Period(start_date, freq="M")
            end_period = pd.Period(end_date, freq="M")
            if start_period > end_period:
                raise ValueError("start_date must not be after end_date.")
            start = start_period.start_time
            end_exclusive = (end_period + 1).start_time
        else:
            start = pd.Timestamp(start_date).normalize()
            end = pd.Timestamp(end_date).normalize()
            if start > end:
                raise ValueError("start_date must not be after end_date.")
            end_exclusive = end + pd.Timedelta(1, unit="D")
    except ValueError as error:
        if str(error) == "start_date must not be after end_date.":
            raise
        expected = "YYYY-MM" if frequency == "monthly" else "YYYY-MM-DD"
        raise ValueError(f"start_date and end_date must be in '{expected}' format.") from error

    def validate_bound(value: Real | None, name: str) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"{name} must be a finite non-negative number.")
        numeric_value = float(value)
        if not math.isfinite(numeric_value) or numeric_value < 0:
            raise ValueError(f"{name} must be a finite non-negative number.")
        return numeric_value

    market_cap_min = validate_bound(market_cap_min, "market_cap_min")
    market_cap_max = validate_bound(market_cap_max, "market_cap_max")
    price_min = validate_bound(price_min, "price_min")
    price_max = validate_bound(price_max, "price_max")

    for lower_name, lower, upper_name, upper in (
        ("market_cap_min", market_cap_min, "market_cap_max", market_cap_max),
        ("price_min", price_min, "price_max", price_max),
    ):
        if lower is not None and upper is not None and lower >= upper:
            raise ValueError(f"{lower_name} must be less than {upper_name}.")

    if share_codes is not None:
        if isinstance(share_codes, (str, bytes)):
            raise ValueError("share_codes must be an iterable of integers.")
        try:
            share_codes = list(share_codes)
        except TypeError as error:
            raise ValueError("share_codes must be an iterable of integers.") from error
        if not share_codes:
            raise ValueError("share_codes must not be empty.")
        if not all(
            isinstance(value, Integral) and not isinstance(value, bool)
            for value in share_codes
        ):
            raise ValueError("share_codes must be an iterable of integers.")
        share_codes = list(dict.fromkeys(int(value) for value in share_codes))

    con = db.connection
    if hasattr(con, "connection"):
        con = con.connection

    if frequency == "monthly":
        data_table = "crspm.msf"
        names_table = "crspm.msenames"
        prior_date_condition = "AND p.date = (a.date - INTERVAL '1 month')::date"
    else:
        data_table = "crsp.dsf"
        names_table = "crsp.dsenames"
        prior_date_condition = ""

    screen_values = (
        share_codes is not None
        or market_cap_min is not None
        or market_cap_max is not None
        or price_min is not None
        or price_max is not None
    )
    screen_join = ""
    screen_filters = []
    params: list[object] = [start, end_exclusive]

    if screen_values:
        screen_join = f"""
        LEFT JOIN LATERAL (
            SELECT
                p.date AS screen_date,
                p.prc AS screen_prc,
                p.shrout AS screen_shrout,
                pb.shrcd AS screen_shrcd
            FROM {data_table} p
            LEFT JOIN {names_table} pb
                ON p.permno = pb.permno
               AND p.date >= pb.namedt
               AND p.date <= pb.nameendt
            WHERE p.permno = a.permno
              AND p.date < a.date
              {prior_date_condition}
            ORDER BY p.date DESC, pb.nameendt DESC NULLS LAST
            LIMIT 1
        ) screen ON TRUE
        """
        screen_filters.append("screen.screen_date IS NOT NULL")

        if share_codes is not None:
            placeholders = ", ".join(["%s"] * len(share_codes))
            screen_filters.append(f"screen.screen_shrcd IN ({placeholders})")
            params.extend(share_codes)

        if market_cap_min is not None:
            screen_filters.append(
                "ABS(screen.screen_prc) * screen.screen_shrout * 1000 > %s"
            )
            params.append(market_cap_min)
        if market_cap_max is not None:
            screen_filters.append(
                "ABS(screen.screen_prc) * screen.screen_shrout * 1000 < %s"
            )
            params.append(market_cap_max)
        if price_min is not None:
            screen_filters.append("ABS(screen.screen_prc) > %s")
            params.append(price_min)
        if price_max is not None:
            screen_filters.append("ABS(screen.screen_prc) < %s")
            params.append(price_max)

    where_filters = ["a.date >= %s", "a.date < %s", *screen_filters]
    sql = f"""
        SELECT
            a.date,
            a.permno,
            a.permco,
            b.ticker,
            b.comnam,
            b.shrcd,
            b.exchcd,
            b.siccd,
            a.prc,
            a.ret,
            a.retx,
            a.vol,
            a.shrout
        FROM {data_table} a
        INNER JOIN {names_table} b
            ON a.permno = b.permno
           AND a.date >= b.namedt
           AND a.date <= b.nameendt
        {screen_join}
        WHERE {' AND '.join(where_filters)}
    """

    out = pd.read_sql_query(sql, con, params=params)
    if out.empty:
        out = pd.DataFrame(
            {
                column: pd.Series(dtype=dtype)
                for column, dtype in _EMPTY_RESULT_DTYPES.items()
            }
        )
        if frequency == "monthly":
            out.index = pd.PeriodIndex([], freq="M", name="date")
        else:
            out.index = pd.DatetimeIndex([], name="date")
        return _merge_crsp_factors(
            out, start_date, end_date, frequency, include_factors
        )

    if out.duplicated(subset=["date", "permno"]).any():
        raise RuntimeError(
            "CRSP query returned multiple rows for at least one "
            "(date, permno) pair; check the msenames validity join."
        )

    out = out.sort_values(["date", "permno"]).reset_index(drop=True).copy()
    dates = pd.to_datetime(out["date"])
    if frequency == "monthly":
        out.index = pd.PeriodIndex(dates.dt.to_period("M"), freq="M", name="date")
    else:
        out.index = pd.DatetimeIndex(dates, name="date")
    return _merge_crsp_factors(
        out.drop(columns=["date"]),
        start_date,
        end_date,
        frequency,
        include_factors,
    )


# Backward-compatible name retained for existing callers.
get_crsp_msf_by_ids = load_crsp_data
