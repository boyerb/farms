import numpy as np
import pandas as pd
import pytest

import farms as fm

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")


def test_plot_return_histograms_wraps_columns_and_shows_means():
    returns = pd.DataFrame(
        {
            "Dec 1": [0.01, -0.02, 0.03],
            "Dec 5": [0.02, -0.01, 0.02],
            "Dec 10": [0.03, -0.01, 0.04],
            "Market": [0.02, -0.01, 0.03],
        }
    )

    figure, axes = fm.plot_return_histograms(
        returns,
        columns=["Dec 1", "Dec 5", "Dec 10", "Market"],
        ncols=3,
        show_mean=True,
        title="Return distributions",
    )

    assert len(axes) == 4
    assert figure._suptitle.get_text() == "Return distributions"
    assert all(axis.lines for axis in axes)
    assert figure.axes[-1].get_visible() is False


def test_plot_return_histograms_can_hide_mean_lines_and_use_independent_y_scales():
    returns = pd.DataFrame({"A": [0.01, 0.02], "B": [0.03, 0.04]})

    figure, axes = fm.plot_return_histograms(
        returns,
        show_mean=False,
        sharey=False,
        ncols=2,
    )

    assert all(not axis.lines for axis in axes)
    assert not axes[0].get_shared_y_axes().joined(axes[0], axes[1])
    assert figure is not None


def test_plot_return_histograms_auto_uses_common_bin_edges():
    returns = pd.DataFrame(
        {
            "A": [-0.10, -0.05, 0.01, 0.02, 0.04],
            "B": [0.03, 0.06, 0.08, 0.10, 0.12],
        }
    )

    figure, axes = fm.plot_return_histograms(returns)

    first_edges = np.array(
        [patch.get_x() for patch in axes[0].patches]
        + [axes[0].patches[-1].get_x() + axes[0].patches[-1].get_width()]
    )
    second_edges = np.array(
        [patch.get_x() for patch in axes[1].patches]
        + [axes[1].patches[-1].get_x() + axes[1].patches[-1].get_width()]
    )

    np.testing.assert_allclose(first_edges, second_edges)
    assert len(first_edges) > 2
    figure.clf()


def test_plot_return_histograms_accepts_integer_bin_override():
    returns = pd.DataFrame({"A": [0.01, 0.02, 0.03], "B": [0.04, 0.05, 0.06]})

    figure, axes = fm.plot_return_histograms(returns, bins=4)

    assert len(axes[0].patches) == 4
    figure.clf()


def test_plot_return_histograms_rejects_unknown_bin_method():
    returns = pd.DataFrame({"A": [0.01, 0.02, 0.03]})

    with pytest.raises(ValueError, match="'auto'"):
        fm.plot_return_histograms(returns, bins="fd")


def test_plot_cumulative_wealth_compounds_selected_period_returns():
    returns = pd.DataFrame(
        {
            "Dec 1": [0.10, -0.05, 0.20],
            "Dec 10": [0.05, 0.10, -0.02],
            "Other": [0.50, 0.50, 0.50],
        },
        index=pd.period_range("2000-01", periods=3, freq="M"),
    )

    figure, axis = fm.plot_cumulative_wealth(
        returns,
        columns=["Dec 1", "Dec 10"],
        start="2000-02-01",
    )

    np.testing.assert_allclose(axis.lines[0].get_ydata(), [0.95, 1.14])
    np.testing.assert_allclose(axis.lines[1].get_ydata(), [1.10, 1.078])
    assert axis.get_title() == "Growth of One Dollar"
    assert [text.get_text() for text in axis.get_legend().get_texts()] == [
        "Dec 1",
        "Dec 10",
    ]
    figure.clf()
