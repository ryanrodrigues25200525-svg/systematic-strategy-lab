import numpy as np
import pandas as pd

from src.backtest import moving_average_signal, run_backtest, split_time_series
from src.data import make_demo_ohlcv, validate_ohlcv
from src.portfolio import (
    cross_sectional_momentum_weights,
    downside_volatility_momentum_weights,
    dual_momentum_weights,
    fifty_two_week_high_weights,
    inverse_volatility_weights,
    low_volatility_weights,
    low_beta_weights,
    minimum_variance_weights,
    momentum_volatility_scaled_weights,
    run_portfolio_backtest,
    short_term_reversal_weights,
    trend_following_rotation_weights,
    time_series_momentum_portfolio_weights,
    volatility_managed_momentum_weights,
    volatility_managed_weights,
    volatility_regime_rotation_weights,
)
from src.strategies import (
    bollinger_mean_reversion_signal,
    donchian_breakout_signal,
    time_series_momentum_signal,
)


def test_demo_data_is_valid_and_reproducible():
    first = make_demo_ohlcv(periods=100, seed=3)
    second = make_demo_ohlcv(periods=100, seed=3)
    pd.testing.assert_frame_equal(first, second)
    assert list(first.columns) == ["open", "high", "low", "close", "volume"]


def test_ohlcv_validation_allows_rounding_level_vendor_noise():
    dates = pd.bdate_range("2020-01-01", periods=1)
    data = pd.DataFrame(
        {"open": [100.0], "high": [100.0 - 1e-10], "low": [99.0], "close": [100.0], "volume": [1_000_000]},
        index=dates,
    )
    validate_ohlcv(data)


def test_position_is_shifted_before_return_is_applied():
    dates = pd.bdate_range("2020-01-01", periods=4)
    close = pd.Series([100.0, 200.0, 100.0, 100.0], index=dates)
    # The signal turns on only after the first jump. It cannot earn that jump.
    target = pd.Series([0.0, 1.0, 1.0, 1.0], index=dates)
    result = run_backtest(close, target, transaction_cost_bps=0)
    assert result.frame.loc[dates[1], "net_returns"] == 0.0
    assert result.frame.loc[dates[2], "net_returns"] == -0.5


def test_costs_are_charged_on_exposure_changes():
    dates = pd.bdate_range("2020-01-01", periods=4)
    close = pd.Series([100.0, 100.0, 100.0, 100.0], index=dates)
    target = pd.Series([1.0, 0.0, 0.0, 0.0], index=dates)
    result = run_backtest(close, target, transaction_cost_bps=10)
    assert len(result.trades) == 2
    assert np.isclose(result.frame["transaction_cost"].sum(), 0.002)
    assert result.metrics["number_of_trades"] == 2.0


def test_moving_average_rejects_invalid_windows():
    close = pd.Series(np.arange(10.0) + 1)
    try:
        moving_average_signal(close, fast_window=20, slow_window=10)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid moving-average windows to fail")


def test_time_series_split_preserves_order_and_sizes():
    data = pd.DataFrame({"value": range(100)})
    splits = split_time_series(data, train_fraction=0.6, validation_fraction=0.2)
    assert [len(splits[name]) for name in ("train", "validation", "test")] == [60, 20, 20]
    assert splits["train"].iloc[-1, 0] < splits["validation"].iloc[0, 0]
    assert splits["validation"].iloc[-1, 0] < splits["test"].iloc[0, 0]


def test_time_series_momentum_uses_only_completed_lookback_return():
    dates = pd.bdate_range("2020-01-01", periods=6)
    close = pd.Series([100.0, 101.0, 102.0, 98.0, 97.0, 99.0], index=dates)
    signal = time_series_momentum_signal(close, lookback=2)
    assert signal.iloc[0] == 0.0
    assert signal.iloc[2] == 1.0
    assert signal.iloc[3] == 0.0


def test_bollinger_signal_enters_below_band_and_exits_above_middle():
    dates = pd.bdate_range("2020-01-01", periods=9)
    close = pd.Series([100.0, 100.0, 100.0, 100.0, 100.0, 80.0, 80.0, 100.0, 100.0], index=dates)
    signal = bollinger_mean_reversion_signal(close, window=5, num_std=1.0)
    assert signal.iloc[4] == 0.0
    assert signal.iloc[5] == 1.0
    assert signal.iloc[7] == 0.0


def test_donchian_breakout_uses_prior_highs_and_lows():
    dates = pd.bdate_range("2020-01-01", periods=7)
    close = pd.Series([1.0, 2.0, 3.0, 4.0, 3.5, 2.0, 2.0], index=dates)
    signal = donchian_breakout_signal(close, high=close, low=close, entry_window=3, exit_window=2)
    assert signal.iloc[2] == 0.0
    assert signal.iloc[3] == 1.0
    assert signal.iloc[5] == 0.0


def test_portfolio_backtest_shifts_weights_and_charges_turnover_costs():
    dates = pd.bdate_range("2020-01-01", periods=4)
    close = pd.DataFrame(
        {"AAA": [100.0, 110.0, 110.0, 110.0], "BBB": [100.0, 100.0, 100.0, 100.0]},
        index=dates,
    )
    weights = pd.DataFrame({"AAA": [0.0, 1.0, 1.0, 1.0], "BBB": [1.0, 0.0, 0.0, 0.0]}, index=dates)
    result = run_portfolio_backtest(close, weights, transaction_cost_bps=10)
    assert result.frame.loc[dates[1], "gross_returns"] == 0.0
    assert len(result.trades) == 3
    assert np.isclose(result.frame["transaction_cost"].sum(), 0.003)


def test_portfolio_weight_builders_are_monthly_and_sum_to_one_after_warmup():
    dates = pd.bdate_range("2020-01-01", periods=140)
    close = pd.DataFrame(
        {
            "AAA": np.linspace(100.0, 180.0, len(dates)),
            "BBB": np.linspace(100.0, 120.0, len(dates)),
            "CCC": np.linspace(100.0, 90.0, len(dates)),
        },
        index=dates,
    )
    for weights in (
        cross_sectional_momentum_weights(close, lookback=20, top_n=2),
        cross_sectional_momentum_weights(close, lookback=20, skip_recent=5, top_n=2),
        short_term_reversal_weights(close, lookback=20, top_n=2),
        fifty_two_week_high_weights(close, lookback=20, top_n=2),
        downside_volatility_momentum_weights(close, momentum_lookback=20, skip_recent=5, volatility_lookback=10, top_n=2),
        low_volatility_weights(close, lookback=20, top_n=2),
        inverse_volatility_weights(close, lookback=20),
            dual_momentum_weights(close, lookback=20, top_n=1, risk_assets=("AAA", "BBB"), defensive_assets=("CCC",)),
            trend_following_rotation_weights(close, trend_window=20, momentum_lookback=20, top_n=1, risk_assets=("AAA", "BBB"), defensive_assets=("CCC",)),
            volatility_regime_rotation_weights(close, volatility_lookback=10, high_volatility_threshold=0.20, momentum_lookback=20, top_n=1, market_asset="AAA", risk_assets=("AAA", "BBB"), defensive_assets=("CCC",)),
            low_beta_weights(close, lookback=20, top_n=2, market_asset="AAA"),
            minimum_variance_weights(close, lookback=20),
        ):
        row_sums = weights.sum(axis=1)
        assert (row_sums[(row_sums > 0)] <= 1.0000001).all()
        assert (row_sums[(row_sums > 0)] > 0.999999).all()

    for weights in (
        volatility_managed_weights(close, lookback=20, target_volatility=0.15),
        volatility_managed_momentum_weights(close, momentum_lookback=20, top_n=2, volatility_lookback=10),
        time_series_momentum_portfolio_weights(close, lookback=20),
        momentum_volatility_scaled_weights(close, momentum_lookback=20, skip_recent=5, top_n=2, volatility_lookback=10),
    ):
        row_sums = weights.abs().sum(axis=1)
        assert (row_sums <= 1.0000001).all()
        assert (row_sums[(row_sums > 0)] > 0.0).all()


def test_reversal_selects_the_recent_loser():
    dates = pd.bdate_range("2020-01-01", periods=50)
    close = pd.DataFrame(
        {"WINNER": np.linspace(100.0, 200.0, len(dates)), "LOSER": np.linspace(100.0, 50.0, len(dates))},
        index=dates,
    )
    weights = short_term_reversal_weights(close, lookback=10, top_n=1)
    valid = weights[weights.sum(axis=1) > 0]
    assert (valid["LOSER"] == 1.0).all()


def test_dual_momentum_uses_defensive_asset_when_risk_assets_have_negative_momentum():
    dates = pd.bdate_range("2020-01-01", periods=80)
    close = pd.DataFrame(
        {
            "RISK": np.linspace(200.0, 100.0, len(dates)),
            "DEF": np.linspace(100.0, 120.0, len(dates)),
        },
        index=dates,
    )
    weights = dual_momentum_weights(close, lookback=20, risk_assets=("RISK",), defensive_assets=("DEF",))
    valid = weights[weights.sum(axis=1) > 0]
    assert (valid["DEF"] == 1.0).all()


def test_time_series_momentum_portfolio_can_short_downtrending_assets():
    dates = pd.bdate_range("2020-01-01", periods=80)
    close = pd.DataFrame(
        {"UP": np.linspace(100.0, 160.0, len(dates)), "DOWN": np.linspace(100.0, 60.0, len(dates))},
        index=dates,
    )
    weights = time_series_momentum_portfolio_weights(close, lookback=20)
    valid = weights[weights.abs().sum(axis=1) > 0]
    assert (valid["UP"] > 0).all()
    assert (valid["DOWN"] < 0).all()
