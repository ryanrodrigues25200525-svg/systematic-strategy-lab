# 💬 Reddit strategy audit findings

This report records two Reddit-sourced strategy hypotheses tested in separate, beginner-friendly notebooks. The purpose is to audit reproducibility—not to validate a headline Sharpe ratio.

> Educational research only. Not financial advice. Results are historical, sample-specific, and based on simplified execution assumptions.

## 🔎 Results at a glance

| Strategy | Reddit claim | Reproduced untouched-test result | Main interpretation |
| --- | --- | --- | --- |
| IBS lower-band mean reversion | 2.11 Sharpe; 13.0% annualized return; −20.3% drawdown; 414 trades; 69% win rate | 5.81% annualized return; **0.53 Sharpe**; −13.57% drawdown; 159 trades; 56.23% win rate after 10 bps costs | The original rule is interesting, but the post’s headline used an improved dynamic-stop version and is not a clean replication target. |
| Global dual momentum | 17.26% CAGR; 0.58 Sharpe; −45% drawdown | 3.27% annualized return; **0.29 Sharpe**; −38.81% drawdown after 10 bps costs | The allocation idea remains testable, but the observed ETF implementation is much weaker in the later test period and is sensitive to sample and proxy choices. |

The IBS strategy’s full-sample daily portfolio Sharpe was 0.65. Its active-days Sharpe was 1.82, but that statistic excludes cash days and therefore is not comparable to the standard portfolio Sharpe. The gap is an important example of why a Sharpe number needs a definition.

## 📓 Notebooks

- [36 — Reddit IBS mean reversion](notebooks/36_reddit_ibs_mean_reversion.ipynb)
- [37 — Reddit dual momentum](notebooks/37_reddit_dual_momentum.ipynb)

Each notebook includes the exact rule, the source claim, a no-lookahead test, chronological train/validation/test results, cost sensitivity, parameter sensitivity, charts, and a “what went well / what went wrong” review.

## 🧪 What the checks found

### IBS mean reversion

- The rule produced lower volatility and a shallower full-sample drawdown than SPY buy and hold in the common data run.
- It also produced about 24× annualized turnover and 798 full-sample trades, so costs and execution quality matter.
- On the untouched test period, the original Reddit parameters remained positive but fell to a 0.53 Sharpe after 10 bps costs. At 50 bps, the test Sharpe became negative in this run.
- The validation grid showed nearby parameters with similar results, which is more encouraging than one isolated optimum; however, the grid still creates multiple-testing risk.
- The post explicitly reported an improved dynamic-stop strategy, so reproducing the four original rules cannot reproduce its displayed equity curve exactly.

### Dual momentum

- The monthly rotation reduced the SPY buy-and-hold drawdown in the common sample, but it did not eliminate large losses: the test drawdown was −38.81%.
- The untouched test Sharpe was 0.29 after 10 bps costs, versus 0.33 with zero costs. At 50 bps it fell to 0.14.
- Validation-selected windows did not create a large test improvement: the best validation combination shown was 126-day absolute and 252-day relative momentum, but its test Sharpe was only 0.32.
- TLT is not a universal crisis hedge. Rising-rate episodes can hurt the defensive sleeve at the same time equities are weak.

## ⚖️ Why high-Sharpe Reddit posts deserve skepticism

The separate Reddit quant discussion on Sharpe realism argues that robust, after-cost Sharpe around 1.5 can already be strong, while Sharpe above 3 often reflects capacity, high-frequency execution, survivorship, or selection effects. That is a useful prior, not a law. The notebooks therefore report the headline claim, the exact tested implementation, and the failure modes side by side.

Sources:

- [Reddit mean-reversion post](https://www.reddit.com/r/algotrading/comments/1cwsco8/a_mean_reversion_strategy_with_211_sharpe/)
- [Reddit dual-momentum post](https://www.reddit.com/r/LETFs/comments/1jj4tad/leveraged_dual_momentum_backtest/)
- [Reddit discussion on realistic Sharpe ratios](https://www.reddit.com/r/quant/comments/1u16w3p/are_longterm_sharpe_ratios_above_3_and_30_annual/)

## ✅ Reproducibility standards used

- Adjusted Yahoo Finance data, with deterministic offline fallback in the notebooks.
- Signals use information available through the close and are delayed before returns are applied.
- Costs are charged on absolute exposure changes.
- The final test period is chronological and untouched during parameter inspection.
- Results are not treated as investment advice or proof of future performance.
