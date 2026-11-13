# 🧬 Equity factor findings

This batch adds three equity-factor rules that are distinct from the 12–1 momentum already covered: residual momentum, long-horizon reversal, and a quality composite built from published Fama–French factor returns.

> Educational research only. Not financial advice. Historical results are not guarantees of future performance.

> ## ⚠️ Correction (added after publication)
>
> The residual-momentum result below did **not** survive a follow-up stress test. [Notebook 54](notebooks/54_residual_momentum_stress_test.ipynb) shows that its 0.99 test Sharpe is the best of five subperiods, that its full-sample return is market beta (alpha t = 1.12, beta-adjusted Sharpe -0.08), that its rank information coefficient is -0.016, that dropping the three best-performing assets removes the edge (0.84 vs 0.86), and that the best of the 12-configuration grid is unremarkable against a bootstrap null (p = 0.25; deflated Sharpe 0.60 at 12 trials). Read the table below as the *initial* result and [RM_STRESS_TEST_FINDINGS.md](RM_STRESS_TEST_FINDINGS.md) as the verdict. The holding-overlap finding (49% of holdings differ) stands; the return claim does not.

## 📊 Results at a glance

Test period 2022-03-30 to 2025-12-31, 18-asset ETF panel, 10 bps costs, monthly rebalancing.

| Rule | Test Sharpe | Test return | Test drawdown | Turnover | Market beta | Note |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Momentum 12–1 (top 3) | 0.61 | 8.72% | -15.16% | 6.95 | 0.71 | control |
| **Residual momentum (top 3)** | **0.99** | 14.61% | -13.85% | 5.88 | 0.63 | 49% holding overlap with the control |
| Momentum 12–1 long/short | -0.13 | -1.24% | -17.85% | 6.77 | 0.08 | short leg loses money |
| Residual momentum long/short | -0.05 | -0.61% | -14.95% | 6.68 | -0.04 | short leg loses money |
| Reversal 3y (top 3 prior losers) | 0.19 | 1.49% | -20.25% | 3.74 | 0.31 | does not survive in ETFs |
| Reversal 3y long/short | -0.71 | -6.07% | -27.27% | 4.01 | -0.29 | worst result in the batch |
| SPY buy and hold | 0.75 | 12.56% | -21.61% | 0.00 | 1.00 | benchmark |

Quality composite (Fama–French monthly factors, 1963-07 to 2026-09, gross):

| Composite | Gross Sharpe | Monthly skew | Max drawdown | 10 bps x 0.4 turnover | 25 bps x 1.0 turnover |
| --- | ---: | ---: | ---: | ---: | ---: |
| `RMW` only (profitability) | 0.38 | -0.24 | -41.79% | 0.32 | 0.01 |
| **`RMW + CMA` (quality)** | **0.57** | **+0.33** | -29.37% | 0.48 | 0.02 |
| `RMW - CMA` (wrong sign) | -0.04 | -0.55 | -46.18% | -0.13 | -0.61 |

## 🧠 What the results suggest

- **Residual momentum is a different signal, not a relabelled one.** Mean Jaccard overlap with the plain 12–1 book is 0.49, market beta falls from 0.71 to 0.63, and correlation to SPY falls from 0.80 to 0.75. *That part holds under audit — but the conclusion that it therefore earns a better return does not: see the correction above.*
- **The improvement is not stable across splits.** Residual momentum's training-period Sharpe (0.41) was *below* plain momentum's (0.47); the advantage appears in validation and test. All 12 parameter pairs in the grid beat plain momentum, with the 11-month signal window the strongest column — but that grid was read after the test period was known, so it says the result is robust to parameters, not that it is out of sample. Treat it as a hypothesis.
- **Warm-up is not protection.** Residual momentum needs 36 months of regressions plus 12 months of signal, so its first live date is 2011-04-01. Its 0.00% return in the 2008 window is an empty portfolio. The notebook reports a common-start comparison from that date for exactly this reason.
- **Long/short equity momentum lost money in this sample.** Both long/short variants had negative test Sharpe ratios (-0.13 and -0.05), and reversal long/short lost 6.07% a year. Shorting weak sectors through a 2022–2025 bull market costs money regardless of signal quality, and the short leg is where borrow and squeeze risk live.
- **Three-year reversal does not survive at the sector ETF level.** 0.19 test Sharpe. In a 17-ETF cross-section, "loser" is often a structurally declining sector rather than an oversold stock.
- **The quality composite construction works, but the premium decays.** `RMW + CMA` beats `RMW` alone on gross Sharpe (0.57 vs 0.38), drawdown, volatility and skew, and keeps the improvement under realistic costs. Subperiod gross Sharpe: 1.21 (1963–1989), 0.60 (1990–2009), 0.26 (2010–2025) — and in the latest subperiod the plain profitability leg (0.37) beat the composite.

## 🪤 The sign error worth keeping

The first version of the quality composite used `-CMA`, reasoning that "conservative investment" means "low investment". The Fama–French convention is the opposite: `CMA` is *conservative minus aggressive*, so a quality composite needs `+CMA`. With the wrong sign the composite has a gross Sharpe of -0.04 and a drawdown of -46%; with the right sign it is 0.57 and -29%. Two things caught it: the paper's factor-loading table and the presence of a control leg in the same table.

## 🧩 Implementation

New module [`src/equity_factors.py`](src/equity_factors.py):

- `residual_momentum_weights(close, market_asset=..., regression_window=36, signal_window=11, skip_recent=1, top_n=3, bottom_n=0, long_share, short_share)` — monthly regression of each asset on the market, residual momentum standardised by residual volatility.
- `long_term_reversal_weights(close, lookback=756, skip_recent=21, top_n=3, ...)` — buys prior losers.
- `quality_composite_returns(factors, legs={"RMW": 1, "CMA": 1}, volatility_window=36)` — inverse-volatility-weighted factor composite.
- `cross_sectional_momentum_score` / `cross_sectional_momentum_weights_monthly` — the 12–1 control on the same monthly calendar, so comparisons are not distorted by different rebalance timing.

Decisions are made at month end and broadcast onto the following trading days; the shared backtester adds its usual one-bar delay on top.

## 📓 Notebook

- [51 — Equity factors: residual momentum, reversal, quality](notebooks/51_equity_factor_momentum_reversal_quality.ipynb)

## ✅ Validation standards

- 7 new tests in `tests/test_equity_factors.py`. Synthetic panels verify that residual momentum prefers a positive-alpha asset over a higher-beta asset with no alpha, that long/short gross never exceeds 100%, and that both builders are truncation-invariant (a decision at `t` is byte-identical with or without later prices).
- The quality composite is tested against a hand-computed inverse-volatility formula, including the equal-volatility case where the two legs must cancel to zero.
- First-live date reported for every rule; common-start comparison included.
- Cost sensitivity at 0 / 10 / 25 / 50 bps, a 4 x 3 parameter grid, and three stress windows.
- Negative results kept: long/short momentum, reversal, and the decaying quality premium.

## ⚠️ Limitations

- Seventeen liquid ETFs is a coarse cross-section. The paper sorts individual stocks into deciles; "the third-best sector" is a blunt instrument.
- Residual betas use a single market factor, not a three-factor model, because size and value factors are not observable at ETF level here.
- Long/short legs ignore borrow costs, short-sale constraints, and sector concentration limits.
- The quality test uses published Fama–French factor returns: no holdings, no borrow, and turnover is an assumption rather than a measurement.
- No point-in-time survivorship control; ETF closures and index reconstitutions are not modelled.
