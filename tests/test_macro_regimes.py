"""Tests for macro-regime allocation rules built from ETF price signals."""

import numpy as np
import pandas as pd

from src.macro_regimes import (
    credit_regime_weights,
    inflation_rotation_weights,
    term_structure_tilt_weights,
)


def _panel(paths, *, periods=900, seed=5):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2016-01-01", periods=periods)
    prices = {}
    for name, (drift, volatility) in paths.items():
        shocks = rng.normal(drift, volatility, size=periods)
        prices[name] = 100.0 * np.exp(np.cumsum(shocks))
    return pd.DataFrame(prices, index=dates)


def test_credit_regime_goes_defensive_when_credit_breaks_down():
    # Credit falls hard while its safe-ish benchmark grinds up: the HYG/IEF
    # ratio breaks below trend, so the rule must hold the defensive book.
    panel = _panel({
        "HYG": (-0.0025, 0.004),
        "IEF": (0.0004, 0.002),
        "SPY": (0.0006, 0.008),
        "TLT": (0.0003, 0.006),
    })
    weights = credit_regime_weights(
        panel,
        credit_asset="HYG",
        safe_asset="IEF",
        risk_assets=("SPY",),
        defensive_assets=("TLT", "IEF"),
        trend_window=100,
    )
    live = weights.loc[weights.sum(axis=1) > 0]
    assert len(live) > 0
    assert (live["SPY"] == 0.0).all()
    late = live.tail(200)
    assert (late[["TLT", "IEF"]].sum(axis=1) > 0.99).all()


def test_credit_regime_stays_risk_on_when_credit_leads():
    panel = _panel({
        "HYG": (0.0015, 0.003),
        "IEF": (0.0001, 0.002),
        "SPY": (0.0018, 0.004),
        "TLT": (0.0002, 0.006),
    })
    weights = credit_regime_weights(
        panel,
        credit_asset="HYG",
        safe_asset="IEF",
        risk_assets=("SPY",),
        defensive_assets=("TLT", "IEF"),
        trend_window=100,
    )
    live = weights.loc[weights.sum(axis=1) > 0].tail(200)
    # With credit leading and the risk asset trending up, the rule stays risk-on;
    # the defensive fallback exists for the case where momentum itself turns.
    assert (live["SPY"] > 0.99).all()


def test_inflation_rotation_holds_trending_inflation_assets_and_falls_back_to_duration():
    inflation_up = _panel({"TIP": (0.0009, 0.003), "GLD": (0.0008, 0.004), "DBC": (0.0012, 0.006), "TLT": (-0.0004, 0.004)})
    weights = inflation_rotation_weights(inflation_up, trend_window=100, top_n=2)
    live = weights.loc[weights.sum(axis=1) > 0].tail(150)
    assert (live[["TIP", "GLD", "DBC"]].sum(axis=1) > 0.99).all()
    assert (live["TLT"] == 0.0).all()

    deflation = _panel({"TIP": (-0.0009, 0.003), "GLD": (-0.0008, 0.004), "DBC": (-0.0012, 0.006), "TLT": (0.0006, 0.004)})
    weights = inflation_rotation_weights(deflation, trend_window=100, top_n=2)
    live = weights.loc[weights.sum(axis=1) > 0].tail(150)
    assert (live["TLT"] > 0.99).all()


def test_term_structure_tilt_rotates_with_the_duration_trend():
    flattening = _panel({"TLT": (0.0012, 0.004), "IEF": (0.0010, 0.003), "SHY": (0.0001, 0.0005), "SPY": (0.0004, 0.008), "XLF": (0.0002, 0.009)})
    weights = term_structure_tilt_weights(flattening, lookback=100, trend_window=100)
    live = weights.loc[weights.sum(axis=1) > 0].tail(150)
    assert (live[["TLT", "IEF"]].sum(axis=1) > 0.99).all()

    steepening = _panel({"TLT": (-0.0012, 0.004), "IEF": (-0.0008, 0.003), "SHY": (0.0002, 0.0005), "SPY": (0.0009, 0.008), "XLF": (0.0010, 0.009)})
    weights = term_structure_tilt_weights(steepening, lookback=100, trend_window=100)
    live = weights.loc[weights.sum(axis=1) > 0].tail(150)
    assert (live[["SPY", "XLF"]].sum(axis=1) > 0.99).all()


def test_macro_regime_builders_are_long_only_normalised_and_lookahead_free():
    panel = _panel({
        "HYG": (0.0003, 0.004),
        "IEF": (0.0002, 0.003),
        "SHY": (0.0001, 0.0006),
        "TLT": (0.0002, 0.006),
        "SPY": (0.0004, 0.009),
        "XLF": (0.0003, 0.010),
        "TIP": (0.0002, 0.004),
        "GLD": (0.0002, 0.005),
        "DBC": (0.0001, 0.007),
    }, periods=1_200)
    builders = {
        "credit": lambda data: credit_regime_weights(data, trend_window=100, risk_assets=("SPY", "XLF"), defensive_assets=("TLT", "IEF")),
        "inflation": lambda data: inflation_rotation_weights(data, trend_window=100, top_n=2),
        "term": lambda data: term_structure_tilt_weights(data, lookback=100, trend_window=100),
    }
    for name, builder in builders.items():
        weights = builder(panel)
        assert (weights.to_numpy() >= -1e-12).all(), name
        row_sums = weights.sum(axis=1)
        live = row_sums[row_sums > 0.0]
        assert len(live) > 0, name
        assert np.allclose(live.to_numpy(), 1.0, atol=1e-9), name

        cutoff = panel.index[900]
        truncated = builder(panel.loc[:cutoff])
        pd.testing.assert_frame_equal(weights.loc[:cutoff], truncated)


def test_macro_regime_builders_reject_missing_assets_and_bad_parameters():
    panel = _panel({"HYG": (0.0003, 0.004), "SPY": (0.0004, 0.009)}, periods=400)
    for call in (
        lambda: credit_regime_weights(panel, credit_asset="MISSING"),
        lambda: credit_regime_weights(panel, risk_assets=("MISSING",)),
        lambda: credit_regime_weights(panel, trend_window=2),
        lambda: inflation_rotation_weights(panel),
        lambda: inflation_rotation_weights(panel, top_n=0),
        lambda: term_structure_tilt_weights(panel),
        lambda: term_structure_tilt_weights(panel, lookback=5),
    ):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError("Expected a ValueError for invalid macro-regime inputs")


def test_trend_gate_holds_the_asset_above_its_average_and_defense_below_it():
    from src.macro_regimes import trend_gate_weights

    dates = pd.bdate_range("2015-01-01", periods=900)
    up_then_down = np.concatenate([np.linspace(100.0, 200.0, 450), np.linspace(200.0, 90.0, 450)])
    panel = pd.DataFrame(
        {"SPY": up_then_down, "IEF": np.linspace(100.0, 110.0, 900)},
        index=dates,
    )
    weights = trend_gate_weights(panel, asset="SPY", defensive_assets=("IEF",), window=100)

    rising = weights.iloc[300:440]
    falling = weights.iloc[600:890]
    assert (rising["SPY"] > 0.99).all()
    assert (falling["IEF"] > 0.99).all()
    # Warm-up holds nothing; after the average exists the book is fully invested.
    row_sums = weights.sum(axis=1)
    live = row_sums[row_sums > 0.0]
    assert len(live) == 900 - 100
    assert np.allclose(live.to_numpy(), 1.0)

    cutoff = dates[700]
    truncated = trend_gate_weights(panel.loc[:cutoff], asset="SPY", defensive_assets=("IEF",), window=100)
    pd.testing.assert_frame_equal(weights.loc[:cutoff], truncated)

    for call in (
        lambda: trend_gate_weights(panel, asset="MISSING"),
        lambda: trend_gate_weights(panel, window=2),
        lambda: trend_gate_weights(panel, defensive_assets=("MISSING",)),
    ):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError("Expected invalid trend-gate inputs to fail")
