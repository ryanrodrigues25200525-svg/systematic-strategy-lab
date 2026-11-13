# 🌐 Macro regime findings

This batch tests three macro regime rules built from ETF price ratios: a credit-risk appetite filter, an inflation-versus-deflation rotation, and a term-structure tilt. Each rule is measured against **the same rule with its macro filter removed**, which is the only way to see whether the macro signal contributed anything.

> Educational research only. Not financial advice. Historical results are not guarantees of future performance.

## 📊 Results at a glance

Test period 2022-03-30 to 2025-12-31, 14 ETFs, 10 bps costs, monthly decisions, long-only.

| Rule | Test Sharpe | Test return | Test drawdown | Turnover |
| --- | ---: | ---: | ---: | ---: |
| Credit regime (`HYG/IEF` filter) | 0.46 | 6.00% | -24.34% | 5.88 |
| Credit momentum only (no filter) | **0.61** | 10.56% | -25.61% | 4.81 |
| Inflation rotation (trend filter) | 0.33 | 3.96% | -28.87% | 4.54 |
| Inflation momentum only (no filter) | **0.81** | 9.61% | -16.03% | 3.47 |
| Term-structure tilt | 0.25 | 2.72% | -27.75% | 6.68 |
| Always procyclical (no filter) | **0.74** | 11.95% | -21.73% | 0.00 |
| SPY 200-day trend gate | 0.67 | 7.68% | -20.90% | 10.69 |
| 60/40 static | 0.73 | 7.97% | -17.09% | 0.00 |
| SPY buy and hold | 0.75 | 12.56% | -21.61% | 0.00 |

## 🕰️ The result that matters: subperiod behaviour

| Strategy | 2007–2014 | 2015–2021 | 2022–2025 |
| --- | ---: | ---: | ---: |
| Credit regime | **0.95** | 0.88 | 0.08 |
| Credit momentum only (no filter) | 0.31 | 0.87 | 0.51 |
| Inflation rotation | 0.50 | 0.87 | 0.54 |
| Inflation momentum only (no filter) | -0.04 | 0.61 | **0.94** |
| Term-structure tilt | 0.53 | 0.68 | -0.02 |
| Always procyclical (no filter) | 0.32 | 0.75 | 0.68 |
| SPY 200-day trend gate | 0.80 | 0.86 | 0.35 |
| 60/40 static | 0.65 | 1.05 | 0.59 |

Sharpe differences (filter minus its own control): credit **+0.64 / +0.01 / -0.43**; inflation **+0.54 / +0.26 / -0.40**; term structure **+0.21 / -0.07 / -0.71**.

## 🧠 What the results suggest

- **The credit filter is a crisis instrument, not an allocation rule.** It added 0.64 Sharpe in 2007–2014 by stepping aside when credit broke, and *subtracted* 0.43 in 2022–2025. It sat in defensive assets 40.4% of months, which is a permanent insurance premium, not a tactical overlay.
- **It missed the 2022 drawdown for a structural reason.** That sell-off was driven by duration and inflation, not by credit deterioration; `HYG/IEF` never broke the way it did in 2008. A credit-spread state variable cannot see a rate shock.
- **Inflation rotation had the best claim of the three** — it added 0.54, 0.26 and lost 0.40 rescaled to the recent period — but its bare momentum control still beat it recently (0.94 vs 0.54). The trend filter mostly removed the exposure the story wanted.
- **The term-structure proxy has no equity-timing power.** -0.02 Sharpe in 2022–2025, i.e. the filter is worse than doing nothing (0.68 unfiltered). This matches AQR's evidence that the slope forecasts growth far better than equity returns.
- **A 200-day moving average beat all three filters recently.** 0.35 versus 0.08 for the credit rule in 2022–2025. Complexity needs to beat the simplest regime rule, and here it did not.

## 🧩 Implementation

New module [`src/macro_regimes.py`](src/macro_regimes.py):

- `credit_regime_weights(close, credit_asset="HYG", safe_asset="IEF", risk_assets=..., defensive_assets=..., trend_window=200, momentum_lookback=126, top_n=2)` — regime from the credit/safe price ratio; risk selection requires positive momentum as a second condition.
- `inflation_rotation_weights(close, inflation_assets=("TIP","GLD","DBC"), deflation_assets=("TLT",), ...)` — trend-filtered momentum across inflation hedges with a duration fallback.
- `term_structure_tilt_weights(close, short_asset="SHY", long_asset="TLT", duration_assets=..., procyclical_assets=..., ...)` — duration trend interpreted as a curve-slope proxy.

All three decide at the first trading day of each month, hold until the next, and never exceed 100% gross.

## 📓 Notebook

- [52 — Macro regime signals](notebooks/52_macro_regime_signals.ipynb)

## ✅ Validation standards

- 6 new tests in `tests/test_macro_regimes.py`: the credit rule must go defensive when credit breaks and stay risk-on when credit leads; the inflation rule must hold trending inflation assets and fall back to duration when none trend; the term tilt must rotate with the duration trend; all three are truncation-invariant (decisions identical with or without later prices) and long-only normalised.
- Every rule is compared with its unfiltered control, plus static 60/40, SPY, and a SPY 200-day trend gate.
- Occupancy diagnostics: time in defensive assets, monthly switches, average assets held.
- Cost sensitivity at 0 / 10 / 25 / 50 bps, a 3 x 3 parameter grid for the credit rule, and three stress windows.
- Negative results kept: all three filters lost to their own controls in the recent period.

## ⚠️ Limitations

- **No actual macro series.** No credit spread, no yield curve, no inflation print. Every regime variable is a price ratio contaminated by duration, coupon and fund-flow effects. `HYG/IEF` is not an OAS spread and `TLT/SHY` is not a 10s-2s slope.
- Monthly decisions only; macro overlays are often evaluated weekly.
- Long-only and unlevered, so risk balancing across regimes (the Bridgewater construction) is out of scope.
- Fourteen ETFs with a four-asset risk basket makes the selection inside each regime very coarse.
- 2022–2025 is a single inflation shock; "credit filters do not handle inflation shocks" rests on one episode.
