"""Tests for the factor-audit helpers: bootstrap, beta adjustment, deflation."""

import numpy as np
import pandas as pd

from src.factor_audit import (
    alpha_beta,
    beta_adjusted_returns,
    bootstrap_pvalue,
    deflated_sharpe_ratio,
    stationary_block_bootstrap,
)


def _panel(periods=600, assets=5, seed=4):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2015-01-01", periods=periods)
    factors = rng.normal(0.0, 0.01, size=(periods, 2))
    returns = factors @ rng.normal(1.0, 0.3, size=(2, assets)) + rng.normal(0.0, 0.004, size=(periods, assets))
    return pd.DataFrame(returns, index=dates, columns=[f"A{i}" for i in range(assets)])


def test_block_bootstrap_preserves_shape_and_reuses_observed_rows():
    returns = _panel()
    resampled = stationary_block_bootstrap(returns, block_length=21, seed=0)

    assert resampled.shape == returns.shape
    assert list(resampled.columns) == list(returns.columns)
    assert resampled.index.equals(returns.index)

    # Every resampled row must be an observed row, untouched.
    observed = {tuple(row) for row in returns.to_numpy()}
    assert all(tuple(row) in observed for row in resampled.to_numpy())


def test_block_bootstrap_preserves_local_dependence_but_changes_global_order():
    returns = _panel()
    block_length = 21
    resampled = stationary_block_bootstrap(returns, block_length=block_length, seed=7)

    source_rows = {tuple(row): position for position, row in enumerate(returns.to_numpy())}
    positions = np.array([source_rows[tuple(row)] for row in resampled.to_numpy()])
    contiguous = np.mean(np.diff(positions) == 1)
    # Stationary bootstrap restarts a block with probability 1 / block_length.
    assert contiguous > 1.0 - 2.0 / block_length
    assert not np.array_equal(positions, np.arange(len(returns)))


def test_block_bootstrap_is_reproducible_and_validates_input():
    returns = _panel()
    first = stationary_block_bootstrap(returns, block_length=21, seed=11)
    second = stationary_block_bootstrap(returns, block_length=21, seed=11)
    pd.testing.assert_frame_equal(first, second)

    for call in (
        lambda: stationary_block_bootstrap(returns, block_length=0),
        lambda: stationary_block_bootstrap(returns.iloc[:1], block_length=10),
        lambda: stationary_block_bootstrap(returns.rename(columns={"A0": "A1"}), block_length=10),
    ):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError("Expected invalid bootstrap inputs to fail")


def test_beta_adjusted_returns_removes_a_pure_market_beta():
    rng = np.random.default_rng(2)
    dates = pd.bdate_range("2018-01-01", periods=800)
    market = pd.Series(rng.normal(0.0004, 0.01, size=len(dates)), index=dates, name="SPY")
    leveraged = (2.0 * market).rename("two_beta")

    adjusted = beta_adjusted_returns(leveraged, market, lookback=200)
    live = adjusted.dropna()
    assert len(live) > 0
    assert np.abs(live).max() < 5e-3  # only estimation error remains
    assert live.std() < 0.2 * leveraged.std()


def test_alpha_beta_recovers_known_coefficients():
    rng = np.random.default_rng(5)
    dates = pd.bdate_range("2018-01-01", periods=1_200)
    market = pd.Series(rng.normal(0.0003, 0.01, size=len(dates)), index=dates)
    strategy = 0.0010 + 0.6 * market + pd.Series(rng.normal(0.0, 0.002, size=len(dates)), index=dates)

    result = alpha_beta(strategy, market, annualization=252)
    assert abs(result["beta"] - 0.6) < 0.05
    assert abs(result["alpha"] - 0.0010 * 252) < 0.05
    assert result["alpha_t_stat"] > 3.0


def test_bootstrap_pvalue_counts_tail_mass_including_the_observation():
    null = np.array([0.1, 0.2, 0.3, 0.4])
    assert np.isclose(bootstrap_pvalue(1.0, null), 1.0 / 5.0)
    assert np.isclose(bootstrap_pvalue(0.0, null), 1.0)
    assert np.isclose(bootstrap_pvalue(0.25, null), 3.0 / 5.0)


def test_deflated_sharpe_falls_with_more_trials_and_matches_the_closed_form():
    common = dict(n_observations=1_000, annualization=252, skewness=0.0, excess_kurtosis=0.0, sharpe_variance=0.3)
    single = deflated_sharpe_ratio(1.0, trials=1, **common)
    many = deflated_sharpe_ratio(1.0, trials=100, **common)
    assert 0.0 <= many < single <= 1.0

    # With one trial and Gaussian returns the benchmark is zero, so the answer is
    # the normal CDF of the standardised Sharpe ratio.
    from statistics import NormalDist

    per_observation = 1.0 / np.sqrt(252)
    expected = NormalDist().cdf(per_observation * np.sqrt(999) / np.sqrt(1.0 + (3.0 - 1.0) / 4.0 * per_observation**2))
    assert np.isclose(single, expected)

    try:
        deflated_sharpe_ratio(1.0, trials=0, **common)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected trials=0 to fail")


def test_deflated_sharpe_benchmark_matches_a_simulated_expected_maximum():
    # The closed-form benchmark is the expected maximum of `trials` standard
    # normals. Check it against the thing it approximates.
    rng = np.random.default_rng(0)
    trials, n_observations = 200, 1_000
    simulated = rng.standard_normal(size=(20_000, trials)).max(axis=1).mean()
    implied_benchmark = simulated / np.sqrt(n_observations) * np.sqrt(252)  # annualised

    # At the benchmark Sharpe ratio the deflated statistic is zero, so the answer
    # must be 0.5 by construction.
    probability = deflated_sharpe_ratio(implied_benchmark, trials=trials, n_observations=n_observations, annualization=252)
    assert abs(probability - 0.5) < 0.01

    # A plausible-looking 1.0 Sharpe over 3 years with 200 trials is not enough.
    assert deflated_sharpe_ratio(1.0, trials=200, n_observations=756, annualization=252) < 0.95
    # The same Sharpe with 2 trials and 10 years of data is.
    assert deflated_sharpe_ratio(1.0, trials=2, n_observations=2_520, annualization=252) > 0.95


def test_alpha_beta_with_extra_factors_removes_a_second_beta():
    rng = np.random.default_rng(9)
    dates = pd.bdate_range("2010-01-01", periods=1_500)
    equity = pd.Series(rng.normal(0.0003, 0.01, size=len(dates)), index=dates)
    duration = pd.Series(rng.normal(0.0002, 0.006, size=len(dates)), index=dates)
    strategy = 0.0001 + 0.3 * equity + 0.8 * duration + pd.Series(rng.normal(0.0, 0.001, size=len(dates)), index=dates)

    single = alpha_beta(strategy, equity)
    two_factor = alpha_beta(strategy, equity, extra_factors=duration.to_frame("TLT"))

    # Single-market alpha is polluted by the duration exposure; the two-factor
    # model must recover both betas and shrink the alpha towards its true value.
    assert abs(two_factor["beta"] - 0.3) < 0.05
    assert abs(two_factor["beta_TLT"] - 0.8) < 0.05
    assert abs(two_factor["alpha"] - 0.0001 * 252) < 0.06
    assert abs(two_factor["alpha"]) < abs(single["alpha"])


def test_deflated_sharpe_requires_the_observation_frequency():
    import inspect

    signature = inspect.signature(deflated_sharpe_ratio)
    assert signature.parameters["annualization"].default is inspect.Parameter.empty

    # A monthly series must be annualised with 12, not 252: the wrong choice
    # divides the Sharpe ratio by 15.9 instead of 3.46 and hides the result.
    monthly = deflated_sharpe_ratio(0.50, trials=1, n_observations=1_197, annualization=12)
    wrong = deflated_sharpe_ratio(0.50, trials=1, n_observations=1_197, annualization=252)
    assert monthly > 0.99
    assert wrong < 0.90


def test_deflated_sharpe_treats_kurtosis_as_excess():
    # Passing excess kurtosis (pandas .kurt()) must penalise the same as the
    # equivalent raw kurtosis (excess + 3).
    excess_route = deflated_sharpe_ratio(0.9, trials=1, n_observations=500, annualization=252, excess_kurtosis=7.0)
    raw_equivalent = deflated_sharpe_ratio(0.9, trials=1, n_observations=500, annualization=252, excess_kurtosis=7.0)
    assert np.isclose(excess_route, raw_equivalent)
    fat_tails = deflated_sharpe_ratio(0.9, trials=1, n_observations=500, annualization=252, excess_kurtosis=40.0)
    assert fat_tails < excess_route


def test_minimum_detectable_sharpe_matches_the_normal_approximation():
    from src.factor_audit import minimum_detectable_sharpe

    # One year of daily data: (1.96 + 0.84) / 1 = 2.80.
    assert np.isclose(minimum_detectable_sharpe(252, annualization=252), 2.802, atol=0.01)
    # A median test has 50% power, so only the alpha threshold remains.
    assert np.isclose(minimum_detectable_sharpe(252, annualization=252, power=0.5), 1.960, atol=0.01)
    # More data lowers the bar; the square-root law is explicit.
    assert minimum_detectable_sharpe(2_520, annualization=252) < minimum_detectable_sharpe(252, annualization=252)
    assert np.isclose(
        minimum_detectable_sharpe(1_008, annualization=252),
        minimum_detectable_sharpe(252, annualization=252) / 2.0,
        atol=0.01,
    )
    # Monthly data uses the same rule with twelve observations per year.
    assert np.isclose(minimum_detectable_sharpe(120, annualization=12), minimum_detectable_sharpe(2_520, annualization=252), atol=0.02)
    for bad in ({"n_observations": 1, "annualization": 252}, {"n_observations": 100, "annualization": 0}):
        try:
            minimum_detectable_sharpe(**bad)
        except ValueError:
            continue
        raise AssertionError("Expected invalid power inputs to fail")
