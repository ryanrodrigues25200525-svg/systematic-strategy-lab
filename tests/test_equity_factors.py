"""Tests for residual momentum, long-horizon reversal, and quality composites."""

import numpy as np
import pandas as pd

from src.equity_factors import (
    long_term_reversal_weights,
    quality_composite_returns,
    residual_momentum_weights,
)


def _monthly_universe(months=180, seed=3):
    """Build a daily panel whose returns are generated from monthly alphas."""

    dates = pd.bdate_range("2008-01-01", periods=months * 21)
    rng = np.random.default_rng(seed)
    market = rng.normal(0.006, 0.04 / np.sqrt(21), size=len(dates))
    panel = {}
    for index, name in enumerate(["BETA", "ALPHA", "DOWNTREND"]):
        idio = rng.normal(0.0, 0.004, size=len(dates))
        if name == "BETA":
            series = 1.5 * market + idio
        elif name == "ALPHA":
            series = market + 0.0006 + idio
        else:
            series = market - 0.0007 + idio
        panel[name] = 100.0 * np.exp(np.cumsum(series))
    return pd.DataFrame(panel, index=dates)


def test_residual_momentum_prefers_idiosyncratic_strength_over_high_beta():
    panel = _monthly_universe()
    weights = residual_momentum_weights(
        panel,
        market_asset="BETA",
        regression_window=24,
        signal_window=6,
        top_n=1,
        bottom_n=0,
    )
    live = weights.loc[weights.sum(axis=1) > 0]
    assert len(live) > 0
    # ALPHA has the same market exposure as the benchmark plus a positive drift;
    # BETA has more market exposure but no drift. Residual momentum must prefer
    # ALPHA despite BETA's larger raw trailing return.
    assert (live["ALPHA"] > 0).mean() > 0.9
    assert (live["ALPHA"] == 1.0).mean() > 0.9


def test_residual_momentum_long_short_does_not_exceed_full_investment():
    panel = _monthly_universe()
    weights = residual_momentum_weights(
        panel,
        market_asset="BETA",
        regression_window=24,
        signal_window=6,
        top_n=1,
        bottom_n=1,
        long_share=0.5,
        short_share=0.5,
    )
    gross = weights.abs().sum(axis=1)
    assert (gross <= 1.0 + 1e-9).all()
    live = weights.loc[gross > 0]
    assert (live.max(axis=1) > 0).all()
    assert (live.min(axis=1) < 0).all()


def test_residual_momentum_is_invariant_to_future_prices():
    panel = _monthly_universe()
    cutoff = panel.index[len(panel) // 2]
    full = residual_momentum_weights(panel, market_asset="BETA", regression_window=24, signal_window=6, top_n=2)
    truncated = residual_momentum_weights(panel.loc[:cutoff], market_asset="BETA", regression_window=24, signal_window=6, top_n=2)
    pd.testing.assert_frame_equal(full.loc[:cutoff], truncated)


def test_long_term_reversal_buys_the_loser():
    dates = pd.bdate_range("2005-01-01", periods=1_600)
    panel = pd.DataFrame(
        {
            "WINNER": np.linspace(100.0, 400.0, len(dates)),
            "LOSER": np.linspace(100.0, 40.0, len(dates)),
            "FLAT": np.full(len(dates), 100.0),
        },
        index=dates,
    )
    weights = long_term_reversal_weights(panel, lookback=756, skip_recent=21, top_n=1)
    live = weights.loc[weights.sum(axis=1) > 0]
    assert len(live) > 0
    assert (live["LOSER"] == 1.0).all()


def test_long_term_reversal_is_invariant_to_future_prices():
    dates = pd.bdate_range("2005-01-01", periods=1_600)
    rng = np.random.default_rng(2)
    panel = pd.DataFrame(
        100.0 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, size=(len(dates), 4)), axis=0)),
        index=dates,
        columns=list("ABCD"),
    )
    cutoff = dates[1_200]
    full = long_term_reversal_weights(panel, lookback=756, top_n=2)
    truncated = long_term_reversal_weights(panel.loc[:cutoff], lookback=756, top_n=2)
    pd.testing.assert_frame_equal(full.loc[:cutoff], truncated)


def test_quality_composite_scales_legs_by_inverse_volatility():
    rng = np.random.default_rng(7)
    factors = pd.DataFrame(
        {
            "RMW": rng.normal(0.002, 0.010, 400),
            "CMA": rng.normal(0.001, 0.030, 400),
        },
        index=pd.period_range("1990-01", periods=400, freq="M").to_timestamp("M"),
    )
    composite = quality_composite_returns(factors, legs={"RMW": 1.0, "CMA": -1.0}, volatility_window=36)
    live = composite.dropna()
    assert len(live) > 0

    volatility_rmw = factors["RMW"].rolling(36).std().shift(1)
    volatility_cma = factors["CMA"].rolling(36).std().shift(1)
    inverse_rmw, inverse_cma = 1.0 / volatility_rmw, 1.0 / volatility_cma
    total = inverse_rmw + inverse_cma
    expected = factors["RMW"] * (inverse_rmw / total) - factors["CMA"] * (inverse_cma / total)
    assert np.allclose(live.to_numpy(), expected.loc[live.index].to_numpy(), atol=1e-12)
    # The lower-volatility leg must receive the larger share of the budget.
    assert (volatility_rmw.loc[live.index] < volatility_cma.loc[live.index]).all()
    assert ((inverse_rmw / total).loc[live.index] > 0.5).all()

    # An equal-volatility pair must split the budget evenly regardless of sign.
    equal = factors.assign(CMA=factors["RMW"])
    even = quality_composite_returns(equal, legs={"RMW": 1.0, "CMA": -1.0}, volatility_window=36).dropna()
    assert np.allclose(even.to_numpy(), 0.0, atol=1e-12)


def test_equity_factor_builders_reject_invalid_parameters():
    panel = _monthly_universe(months=60)
    for call in (
        lambda: residual_momentum_weights(panel, market_asset="MISSING"),
        lambda: residual_momentum_weights(panel, market_asset="BETA", regression_window=2),
        lambda: residual_momentum_weights(panel, market_asset="BETA", top_n=5),
        lambda: residual_momentum_weights(panel, market_asset="BETA", long_share=0.8, short_share=0.8),
        lambda: long_term_reversal_weights(panel, lookback=10),
        lambda: long_term_reversal_weights(panel, top_n=0),
        lambda: quality_composite_returns(panel, legs={}),
    ):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError("Expected a ValueError for an invalid parameter")


def test_residual_momentum_score_drives_the_weights():
    from src.equity_factors import residual_momentum_score

    panel = _monthly_universe()
    score = residual_momentum_score(panel, market_asset="BETA", regression_window=24, signal_window=6)
    weights = residual_momentum_weights(panel, market_asset="BETA", regression_window=24, signal_window=6, top_n=2)

    assert "BETA" not in score.columns
    # At every month-start decision the held assets must be the score's top two.
    decisions = weights.index[weights.diff().abs().sum(axis=1) > 1e-9]
    matched = 0
    for timestamp in decisions:
        month_end = score.index[score.index <= timestamp]
        if len(month_end) == 0:
            continue
        top = score.loc[month_end[-1]].dropna().nlargest(2).index
        held = weights.loc[timestamp][weights.loc[timestamp] > 0].index
        matched += int(set(top) == set(held))
    assert matched >= 0.8 * len(decisions)
