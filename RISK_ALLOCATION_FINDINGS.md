# ⚖️ Risk-based allocation findings

This batch adds the covariance-aware side of portfolio construction: shrinkage estimation, equal risk contribution, hierarchical risk parity, and maximum diversification. All four are monthly, long-only, charged 10 bps per unit of turnover, and tested on a ten-ETF multi-asset panel from 2007 to 2025 with an untouched test period from 2022-03-30.

> Educational research only. Not financial advice. Historical results are not guarantees of future performance.

## 📊 Results at a glance

Test period: 2022-03-30 to 2025-12-31, 10 ETFs, 10 bps costs, 252-day covariance lookback.

| Allocation | Test Sharpe | Annualised return | Max drawdown | Turnover | Effective N | Largest risk contribution |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Equal weight | **0.75** | 7.37% | -18.06% | 0.00 | 10.0 | 21.1% |
| Inverse volatility | 0.69 | 5.91% | -16.78% | 0.27 | 8.7 | 13.8% |
| Equal risk contribution (ERC) | 0.65 | 5.56% | -16.66% | 0.33 | 8.9 | **10.8%** |
| Hierarchical risk parity (HRP) | 0.63 | 4.93% | -16.02% | 1.42 | 6.4 | 23.9% |
| Minimum variance (sample) | 0.48 | 3.19% | -13.00% | 1.11 | 2.2 | 46.5% |
| Minimum variance (OAS shrinkage) | 0.46 | 3.09% | -13.40% | 0.89 | 2.9 | 43.1% |
| Maximum diversification | 0.32 | 2.63% | -19.17% | 1.29 | 5.0 | 34.1% |
| SPY buy and hold | **0.75** | 12.56% | -21.61% | 0.00 | — | — |

*Effective N is `1 / sum(w^2)`; the largest risk contribution is the biggest single share of portfolio variance at the end of the test period.*

## 🧠 What the results suggest

- **Equal weight is the benchmark to beat, and it won.** It matched SPY's Sharpe ratio (0.75) with roughly half the volatility and beat every covariance-based method in this batch. This is the DeMiguel–Garlappi–Uppal result arriving in a small ETF panel: with noisy estimates, "don't optimise" is a real strategy.
- **Diversification is measurable, and the label is not the measurement.** Maximum diversification produced the highest diversification ratio (1.823) and the lowest Sharpe ratio (0.32), because the ratio is maximised by loading on low-volatility, low-correlation assets — it held 54.8% in intermediate Treasuries. ERC held all ten assets with a 10.8% largest risk contribution. HRP sat in between.
- **ERC is the honest version of risk parity.** Risk contributions come out equal to solver tolerance by construction, and turnover is a third of HRP's because ERC barely reacts to correlation noise.
- **HRP trades drawdown for turnover.** Effective N of 6.4 versus 2.2 for sample minimum variance, at 4x ERC's turnover. Its drawdown (-16.0%) is worse than minimum variance (-13.0%) precisely because it does not abandon equities after they fall.
- **Shrinkage is a stability tool, not a return tool.** A 60-day sample covariance on ten ETFs has a condition number of 840; the OAS matrix has 60 and the Ledoit-Wolf matrix 34, using intensities of 7.7% and 13.3%. On ten assets that did not improve Sharpe (0.46 vs 0.48). On eighteen assets with a 252-day window it did: 1.27 versus 1.11, and it cut concentration (effective N 1.9 vs 1.4).

## 🧯 Stress behaviour

| Strategy | 2008 return | 2008 drawdown | 2020 shock | 2022 inflation |
| --- | ---: | ---: | ---: | ---: |
| ERC | 0.81% | -19.11% | 1.45% | -13.93% |
| HRP | 0.85% | -14.94% | -0.76% | -14.25% |
| Minimum variance (sample) | 1.70% | -10.94% | 5.06% | -14.22% |
| Maximum diversification | 4.08% | -18.88% | 6.90% | -17.36% |
| SPY buy and hold | -20.14% | -51.87% | -3.17% | -18.18% |

2022 is the informative column: in an inflation shock where stocks and bonds fell together, every correlation-aware method behaved like a 100% risky portfolio. Diversification across two risk factors is not diversification across four economic regimes.

## 🧩 Implementation

New module [`src/risk.py`](src/risk.py):

- `shrink_covariance(returns, method="oas" | "ledoit-wolf" | "none", return_intensity=...)` — closed-form linear shrinkage toward `mu * I`; no scikit-learn dependency.
- `erc_weights(covariance, budget=None)` — Spinu's convex program (`min y'Σy - Σ b_i log y_i`) solved by damped Newton, so singular covariance matrices are fine.
- `hierarchical_risk_parity_weights_from_cov(covariance)` — correlation distance, single-linkage dendrogram (implemented in NumPy), quasi-diagonalisation, recursive bisection.
- `max_diversification_weights_from_cov(covariance)` — long-only `Σ⁻¹σ` with negative entries clipped and renormalised.
- `risk_contributions(...)` and `diversification_ratio(...)` — the diagnostics the notebook reports.

Monthly builders in [`src/portfolio.py`](src/portfolio.py): `equal_risk_contribution_weights`, `hierarchical_risk_parity_weights`, `max_diversification_weights`, `shrunk_minimum_variance_weights`.

## 📓 Notebook

- [50 — Risk-based allocation](notebooks/50_risk_based_allocation.ipynb)

## ✅ Validation standards

- 11 new tests in `tests/test_risk.py`; the OAS implementation was cross-checked against scikit-learn during development and matches to ~1e-6 on random matrices.
- Risk contributions are verified to sum to one and to be equal under ERC (to 1e-10).
- Every monthly builder is tested for truncation invariance: a decision at date `t` is byte-identical whether or not later prices exist in the input.
- One-bar execution delay, chronological train/validation/test split, cost sensitivity at 0/10/25/50 bps, and lookback sensitivity at 63/126/252/504 days.
- Negative results are kept: sample minimum variance beat the shrunk version at ten assets, and maximum diversification had the worst Sharpe ratio of the batch.

## ⚠️ Limitations

- Ten to eighteen liquid ETFs is a small universe with heavy shared equity beta; these methods are designed for hundreds of assets.
- Long-only, no leverage, no borrow, no financing. The papers study unconstrained and levered versions.
- Only trailing-window covariance estimation: no factor model, no exponentially weighted estimator, no regime-switching covariance.
- Maximum diversification is solved by clipping rather than an exact quadratic program; it is the right economics but not necessarily the exact optimum.
- Single-linkage HRP can reorder clusters after a correlation shift, which is the source of its turnover.
