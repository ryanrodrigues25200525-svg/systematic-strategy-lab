# 📚 New research-paper strategy findings

This report covers three new paper-inspired notebooks added to the Strategy Lab. Each implementation uses liquid ETFs and the project’s shared one-bar-delay backtester, so the results are proxies rather than exact stock-level replications.

> Educational research only. Not financial advice. Historical proxy results are not guarantees of future performance.

## 📊 Results at a glance

| Paper strategy | Implementation | Untouched-test result after 10 bps costs | Main lesson |
| --- | --- | --- | --- |
| Barroso–Santa-Clara / Daniel–Moskowitz risk-managed momentum | Long top three and short bottom three ETFs by 12–1 momentum; scale toward 12% volatility | Plain: **0.83 Sharpe**, 6.74% return, −11.00% drawdown. Managed: **0.83 Sharpe**, 6.69% return, −11.00% drawdown | Risk scaling substantially helped the 2008 stress window, but did not improve the later test-period Sharpe in this small ETF universe. |
| George–Hwang 52-week-high momentum | Buy the three ETFs closest to their prior 252-day highs | **0.27 Sharpe**, 3.02% return, −26.25% drawdown | The signal was positive in the test but weaker than ordinary 12–1 momentum, which reached 1.19 Sharpe in the same sample. |
| Moskowitz–Grinblatt industry momentum | Long top three and short bottom three sector ETFs by prior six-month return | **−0.17 Sharpe**, −1.54% return, −15.52% drawdown | A sector ETF proxy did not reproduce the paper’s strong result; universe construction, stock-level breadth, and costs matter. |

## 📓 Notebooks

- [41 — Risk-managed momentum](notebooks/41_paper_risk_managed_momentum.ipynb)
- [42 — 52-week-high momentum](notebooks/42_paper_52_week_high_momentum.ipynb)
- [43 — Industry momentum](notebooks/43_paper_industry_momentum.ipynb)

## 🔎 What the checks found

### Risk-managed momentum

The plain ETF momentum sleeve had 0.83 test Sharpe, 6.74% annualized return, and −11.00% drawdown. The volatility-managed sleeve had the same rounded test Sharpe and a similar return, but it behaved differently during stress: in the 2008 window, plain momentum lost 11.54% with a −32.39% drawdown, while the managed version returned 2.13% with an −11.88% drawdown.

That is a useful distinction: risk management can improve the path without improving every full-sample performance statistic. The implementation is conservative because the shared portfolio engine caps exposure at one; the original papers also study leverage in low-volatility states.

### 52-week-high momentum

The signal’s full sample was stronger than its later test: 0.77 train Sharpe, 0.82 validation Sharpe, and 0.27 test Sharpe. Ordinary 12–1 momentum had 1.19 test Sharpe, so closeness to the high did not add value in this ETF sample.

The 52-week-high signal also had higher test turnover than the 12–1 control, making cost assumptions relevant: at 50 bps, test Sharpe fell to −0.05.

### Industry momentum

The sector ETF implementation had a negative test result: −1.54% annualized return and −0.17 Sharpe after 10 bps costs. The equal-weight sector control had 0.69 Sharpe, while XLY buy and hold had 0.42 Sharpe.

This is not evidence that the paper is wrong. It shows how a stock-level factor can fail when compressed into ten ETFs, exposed to coarse rankings, shorting costs, sector concentration, and a different sample.

## ⚖️ Research judgment

The most important conclusion is that paper replication is an implementation problem. A paper’s signal, universe, weighting, timing, financing, and sample all matter. These notebooks make those choices explicit and preserve unsuccessful outcomes instead of selecting only the most attractive result.

## 🔗 Primary sources

- [Barroso and Santa-Clara — Momentum Has Its Moments](https://doi.org/10.1016/j.jfineco.2014.11.010)
- [Daniel and Moskowitz — Momentum Crashes](https://www.nber.org/papers/w20439)
- [Liu, Liu, and Ma — The 52-Week High Momentum Strategy in International Stock Markets](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1364566)
- [Moskowitz and Grinblatt — Do Industries Explain Momentum?](https://doi.org/10.1111/0022-1082.00146)

## ✅ Validation standards

- All three notebooks executed top-to-bottom with no stored execution errors.
- Yahoo Finance adjusted ETF prices were used where available, with deterministic fallback code inside the notebooks.
- Signals and target weights are delayed before returns are applied.
- Chronological train/validation/test splits, transaction-cost sensitivity, and robustness grids are included.
- Stock-level paper claims and ETF proxies are clearly separated.
