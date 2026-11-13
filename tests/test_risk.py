"""Tests for covariance shrinkage and risk-based allocation methods.

These tests pin down three things that are easy to get wrong and hard to see in
a chart: the covariance estimator must be well conditioned, the risk-parity
solver must actually equalise risk contributions, and every monthly builder must
be invariant to data that arrives after the decision date.
"""

import numpy as np
import pandas as pd

from src.portfolio import (
    equal_risk_contribution_weights,
    hierarchical_risk_parity_weights,
    max_diversification_weights,
    shrunk_minimum_variance_weights,
)
from src.risk import (
    erc_weights,
    hierarchical_risk_parity_weights_from_cov,
    max_diversification_weights_from_cov,
    risk_contributions,
    shrink_covariance,
)


def _panel(periods=900, assets=6, seed=11):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2018-01-01", periods=periods)
    factors = rng.normal(0.0, 0.01, size=(periods, 2))
    loadings = rng.normal(1.0, 0.3, size=(2, assets))
    returns = factors @ loadings + rng.normal(0.0, 0.004, size=(periods, assets))
    prices = 100.0 * np.exp(np.cumsum(returns, axis=0))
    columns = [f"A{i}" for i in range(assets)]
    return pd.DataFrame(prices, index=dates, columns=columns)


def test_shrinkage_is_bounded_and_well_conditioned():
    panel = _panel()
    sample = panel.pct_change().dropna()
    shrunk = shrink_covariance(sample, method="oas")

    eigenvalues = np.linalg.eigvalsh(shrunk.to_numpy())
    assert eigenvalues.min() > 0.0
    # The target is mu * I with mu = trace(S) / n, so shrinkage preserves total
    # variance. The estimator uses the maximum-likelihood scaling (1 / T).
    assert np.isclose(np.trace(shrunk.to_numpy()), np.trace(sample.cov(ddof=0).to_numpy()))

    # A wide matrix (more assets than observations) is singular without shrinkage.
    narrow = panel.pct_change().dropna().iloc[:3]
    assert not np.isfinite(np.linalg.cond(narrow.cov().to_numpy())) or np.linalg.cond(narrow.cov().to_numpy()) > 1e10
    assert np.isfinite(np.linalg.cond(shrink_covariance(narrow, method="oas").to_numpy()))


def test_shrinkage_moves_toward_identity_average_variance_for_noise():
    rng = np.random.default_rng(5)
    noise = pd.DataFrame(rng.normal(0.0, 0.01, size=(40, 8)), columns=list("ABCDEFGH"))
    shrunk = shrink_covariance(noise, method="oas").to_numpy()
    raw = noise.cov().to_numpy()
    off_diagonal = ~np.eye(len(raw), dtype=bool)
    # Shrinkage must pull the spurious off-diagonal noise toward zero.
    assert np.abs(shrunk[off_diagonal]).mean() < np.abs(raw[off_diagonal]).mean()


def test_erc_equalises_risk_contributions():
    covariance = pd.DataFrame(
        [[0.0400, 0.0100, 0.0000], [0.0100, 0.0900, 0.0200], [0.0000, 0.0200, 0.0100]],
        index=list("ABC"),
        columns=list("ABC"),
    )
    weights = erc_weights(covariance)
    assert np.isclose(weights.sum(), 1.0)
    assert (weights > 0.0).all()

    contributions = risk_contributions(weights, covariance)
    assert np.allclose(contributions.to_numpy(), np.full(3, 1.0 / 3.0), atol=1e-10)


def test_erc_with_diagonal_covariance_is_inverse_volatility():
    volatility = np.array([0.10, 0.20, 0.40])
    covariance = pd.DataFrame(np.diag(volatility**2), index=list("ABC"), columns=list("ABC"))
    weights = erc_weights(covariance)
    inverse = 1.0 / volatility
    assert np.allclose(weights.to_numpy(), inverse / inverse.sum(), atol=1e-10)


def test_erc_survives_a_singular_covariance_matrix():
    # Two perfectly duplicated assets: unconstrained quadratic optimisers break.
    covariance = pd.DataFrame(
        [[0.04, 0.04, 0.00], [0.04, 0.04, 0.00], [0.00, 0.00, 0.01]],
        index=list("ABC"),
        columns=list("ABC"),
    )
    weights = erc_weights(covariance)
    assert np.isfinite(weights.to_numpy()).all()
    assert np.isclose(weights.sum(), 1.0)


def test_hrp_allocates_between_clusters_not_within_redundancy():
    # Two near-duplicate pairs plus two independent assets. HRP should give the
    # two members of each pair roughly half the cluster's budget, and each
    # cluster a meaningful share.
    correlation = pd.DataFrame(
        [
            [1.00, 0.95, 0.05, 0.05],
            [0.95, 1.00, 0.05, 0.05],
            [0.05, 0.05, 1.00, -0.05],
            [0.05, 0.05, -0.05, 1.00],
        ],
        index=list("ABCD"),
        columns=list("ABCD"),
    )
    covariance = correlation * 0.04
    weights = hierarchical_risk_parity_weights_from_cov(covariance)

    assert np.isclose(weights.sum(), 1.0)
    assert (weights >= 0.0).all()
    assert np.isclose(weights["A"], weights["B"], rtol=0.2)
    # A duplicated pair is down-weighted relative to a genuinely independent asset.
    assert weights["C"] > weights["A"]
    assert weights["D"] > weights["A"]


def test_max_diversification_beats_equal_weight_on_the_pairs_universe():
    covariance = pd.DataFrame(
        [
            [0.04, 0.030, 0.002, 0.002],
            [0.030, 0.04, 0.002, 0.002],
            [0.002, 0.002, 0.04, -0.004],
            [0.002, 0.002, -0.004, 0.04],
        ],
        index=list("ABCD"),
        columns=list("ABCD"),
    )
    weights = max_diversification_weights_from_cov(covariance)
    volatility = np.sqrt(np.diag(covariance))
    equal = np.full(4, 0.25)

    def diversification_ratio(w):
        return float(w @ volatility / np.sqrt(w @ covariance.to_numpy() @ w))

    assert np.isclose(weights.sum(), 1.0)
    assert diversification_ratio(weights.to_numpy()) > diversification_ratio(equal)


def test_monthly_risk_builders_are_long_only_normalised_and_lookahead_free():
    panel = _panel(periods=800, assets=5)
    builders = {
        "erc": lambda data: equal_risk_contribution_weights(data, lookback=120),
        "hrp": lambda data: hierarchical_risk_parity_weights(data, lookback=120),
        "mdp": lambda data: max_diversification_weights(data, lookback=120),
        "shrunk_minvar": lambda data: shrunk_minimum_variance_weights(data, lookback=120),
    }
    for name, builder in builders.items():
        weights = builder(panel)
        assert list(weights.columns) == list(panel.columns), name
        assert (weights.to_numpy() >= -1e-12).all(), name
        row_sums = weights.sum(axis=1)
        live = row_sums[row_sums > 0.0]
        assert len(live) > 0, name
        assert np.allclose(live.to_numpy(), 1.0, atol=1e-9), name

        # Truncation invariance: a decision cannot depend on later prices.
        cutoff = panel.index[600]
        truncated = builder(panel.loc[:cutoff])
        pd.testing.assert_frame_equal(weights.loc[:cutoff], truncated)


def test_risk_builders_reject_invalid_parameters():
    panel = _panel(periods=300, assets=4)
    for call in (
        lambda: equal_risk_contribution_weights(panel, lookback=1),
        lambda: hierarchical_risk_parity_weights(panel, lookback=1),
        lambda: max_diversification_weights(panel, lookback=1),
        lambda: shrunk_minimum_variance_weights(panel, lookback=1),
        lambda: shrink_covariance(panel.pct_change().dropna(), method="not-a-method"),
    ):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError("Expected a ValueError for an invalid parameter")


def test_shrinkage_intensity_reflects_available_information():
    panel = _panel(periods=1_500, assets=6)
    returns = panel.pct_change().dropna()

    _, short_intensity = shrink_covariance(returns.tail(30), method="oas", return_intensity=True)
    _, long_intensity = shrink_covariance(returns.tail(1_000), method="oas", return_intensity=True)
    _, none_intensity = shrink_covariance(returns.tail(30), method="none", return_intensity=True)

    assert 0.0 <= long_intensity < short_intensity <= 1.0
    assert none_intensity == 0.0


def test_shrinkage_rejects_non_finite_returns_and_singular_inputs():
    returns = pd.DataFrame({"A": [0.01, 0.02, 0.03], "B": [0.01, 0.02, np.inf]})
    try:
        shrink_covariance(returns, method="oas")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected non-finite returns to be rejected")

    single = pd.DataFrame({"A": [0.01, 0.02, 0.03]})
    covariance, intensity = shrink_covariance(single, method="oas", return_intensity=True)
    assert covariance.shape == (1, 1) and intensity == 0.0
