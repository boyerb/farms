import math
from collections.abc import Sequence

import numpy as np
import pandas as pd


def plot_return_histograms(
    returns: pd.DataFrame,
    columns: Sequence[str] | None = None,
    bins: int | str = "auto",
    show_mean: bool = True,
    sharey: bool = True,
    figsize: tuple[float, float] | None = None,
    title: str | None = None,
    alpha: float = 0.8,
    edgecolor: str | None = "white",
    ncols: int = 3,
):
    """Plot return distributions for selected portfolio columns.

    Parameters
    ----------
    returns : pandas.DataFrame
        DataFrame containing decimal period returns.
    columns : sequence of str, optional
        Columns to plot. If omitted, all columns are plotted.
    bins : int or {"auto"}, default "auto"
        Bin selection method. ``"auto"`` estimates a suitable number of
        bins from the pooled returns. A positive integer can be supplied for
        manual control.
    show_mean : bool, default True
        Whether to add a vertical line at each column's mean return.
    sharey : bool, default True
        Whether all histogram panels use the same y-axis scale.
    figsize : tuple of float, optional
        Overall figure size. If omitted, the size is scaled to the grid.
    title : str, optional
        Figure-level title.
    alpha : float, default 0.8
        Histogram transparency.
    edgecolor : str or None, default "white"
        Edge color passed to ``Axes.hist``.
    ncols : int, default 3
        Number of subplot columns. Additional panels wrap onto new rows.

    Returns
    -------
    tuple
        ``(figure, axes)`` where ``axes`` is a list containing the visible
        axes for the selected columns. Unused axes in the final row are
        hidden but remain part of the figure layout.

    Notes
    -----
    Matplotlib is included with ``farms``. Install it with
    ``pip install farms`` if it is not already available.
    """

    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise ImportError(
            "plot_return_histograms requires Matplotlib; "
            "install it with 'pip install farms'"
        ) from exc

    if not isinstance(returns, pd.DataFrame):
        raise TypeError("returns must be a pandas DataFrame")

    selected_columns = list(returns.columns if columns is None else columns)
    if not selected_columns:
        raise ValueError("columns must contain at least one return column")
    missing_columns = [column for column in selected_columns if column not in returns]
    if missing_columns:
        raise KeyError(f"columns not found in returns: {missing_columns}")
    non_numeric_columns = [
        column
        for column in selected_columns
        if not pd.api.types.is_numeric_dtype(returns[column])
    ]
    if non_numeric_columns:
        raise TypeError(
            "returns must contain only numeric columns; "
            f"non-numeric columns: {non_numeric_columns}"
        )

    if isinstance(bins, str):
        if bins != "auto":
            raise ValueError("bins must be 'auto' or a positive integer")
    elif not isinstance(bins, int) or isinstance(bins, bool) or bins <= 0:
        raise ValueError("bins must be 'auto' or a positive integer")
    if not isinstance(ncols, int) or isinstance(ncols, bool) or ncols <= 0:
        raise ValueError("ncols must be a positive integer")
    if not isinstance(alpha, (int, float)) or not 0 < alpha <= 1:
        raise ValueError("alpha must be greater than 0 and no greater than 1")

    nrows = math.ceil(len(selected_columns) / ncols)
    if figsize is None:
        figsize = (4.0 * ncols, 3.5 * nrows)

    # Use one set of bin edges for every panel so the distributions remain
    # directly comparable when the function lays out several portfolios.
    pooled_returns = returns[selected_columns].stack().dropna().to_numpy()
    if pooled_returns.size == 0:
        raise ValueError("selected return columns must contain at least one value")
    histogram_bins = np.histogram_bin_edges(pooled_returns, bins=bins)

    figure, axes_grid = plt.subplots(
        nrows,
        ncols,
        figsize=figsize,
        sharey=sharey,
        squeeze=False,
    )
    axes = [axis for row in axes_grid for axis in row]

    for column, axis in zip(selected_columns, axes):
        axis.hist(
            returns[column],
            bins=histogram_bins,
            edgecolor=edgecolor,
            alpha=alpha,
        )
        if show_mean:
            axis.axvline(
                returns[column].mean(),
                color="darkred",
                linestyle="--",
            )
        axis.set_title(column)
        axis.set_xlabel("Return")
        axis.grid(alpha=0.2)

    axes[0].set_ylabel("Number of observations")
    for axis in axes[len(selected_columns):]:
        axis.set_visible(False)

    if title is not None:
        figure.suptitle(title)
        figure.tight_layout(rect=(0, 0, 1, 0.95))
    else:
        figure.tight_layout()

    return figure, axes[:len(selected_columns)]


def plot_cumulative_wealth(
    returns: pd.DataFrame,
    columns: Sequence[str] | None = None,
    start: str | pd.Timestamp | pd.Period | None = None,
    figsize: tuple[float, float] = (8.0, 4.0),
    title: str = "Growth of One Dollar",
    xlabel: str = "Date",
    ylabel: str = "Dollars",
    legend_ncols: int = 3,
    legend_fontsize: float | str = 8,
    grid_alpha: float = 0.3,
):
    """Plot the growth of one dollar invested in selected portfolios.

    Parameters
    ----------
    returns : pandas.DataFrame
        DataFrame containing decimal period returns.
    columns : sequence of str, optional
        Columns to plot. If omitted, all columns are plotted.
    start : str, pandas.Timestamp, or pandas.Period, optional
        First observation to include. This is especially useful for selecting
        a starting date from a longer return history.
    figsize : tuple of float, default (8.0, 4.0)
        Figure size passed to ``plt.subplots``.
    title : str, default "Growth of One Dollar"
        Plot title.
    xlabel : str, default "Date"
        Horizontal-axis label.
    ylabel : str, default "Dollars"
        Vertical-axis label.
    legend_ncols : int, default 3
        Number of columns used by the legend.
    legend_fontsize : float or str, default 8
        Legend font size.
    grid_alpha : float, default 0.3
        Transparency of the grid lines.

    Returns
    -------
    tuple
        ``(figure, axis)`` containing the Matplotlib figure and axis.

    Notes
    -----
    Matplotlib is included with ``farms``. Install it with
    ``pip install farms`` if it is not already available.
    """

    try:
        import matplotlib.pyplot as plt
        from matplotlib.ticker import StrMethodFormatter
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise ImportError(
            "plot_cumulative_wealth requires Matplotlib; "
            "install it with 'pip install farms'"
        ) from exc

    if not isinstance(returns, pd.DataFrame):
        raise TypeError("returns must be a pandas DataFrame")

    selected_columns = list(returns.columns if columns is None else columns)
    if not selected_columns:
        raise ValueError("columns must contain at least one return column")
    missing_columns = [column for column in selected_columns if column not in returns]
    if missing_columns:
        raise KeyError(f"columns not found in returns: {missing_columns}")
    non_numeric_columns = [
        column
        for column in selected_columns
        if not pd.api.types.is_numeric_dtype(returns[column])
    ]
    if non_numeric_columns:
        raise TypeError(
            "returns must contain only numeric columns; "
            f"non-numeric columns: {non_numeric_columns}"
        )
    if not isinstance(legend_ncols, int) or isinstance(legend_ncols, bool) or legend_ncols <= 0:
        raise ValueError("legend_ncols must be a positive integer")
    if not 0 <= grid_alpha <= 1:
        raise ValueError("grid_alpha must be between 0 and 1")

    selected_returns = returns.loc[:, selected_columns]
    if start is not None:
        selected_returns = selected_returns.loc[start:]
    if selected_returns.empty:
        raise ValueError("no return observations remain after applying start")

    # Compound period returns to show the value of one dollar over time.
    cumulative_wealth = (1 + selected_returns).cumprod()
    plot_index = cumulative_wealth.index
    if isinstance(plot_index, pd.PeriodIndex):
        plot_index = plot_index.to_timestamp()

    figure, axis = plt.subplots(figsize=figsize)
    for column in selected_columns:
        axis.plot(plot_index, cumulative_wealth[column], label=column)

    axis.set_title(title)
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    axis.legend(ncol=legend_ncols, fontsize=legend_fontsize)
    axis.grid(alpha=grid_alpha)
    figure.tight_layout()

    return figure, axis
