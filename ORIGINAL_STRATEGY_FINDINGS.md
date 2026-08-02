# 🧠 Original strategy findings

These three notebooks are original combinations built from patterns observed in the existing paper, hedge-fund, Reddit, and X/Twitter research. They are hypotheses created for this repository—not established academic factors and not investment recommendations.

> Educational research only. Not financial advice. Historical backtests are not guarantees of future performance.

## 📊 Results at a glance

| Original strategy | Design | Untouched-test result after 10 bps costs | What it contributed |
| --- | --- | --- | --- |
| Adaptive regime ensemble | 12–1 momentum + 52-week-high proximity + 200-day trend gate + inverse-volatility weights + defensive fallback | **0.61 Sharpe**, 7.34% annualized return, −18.31% drawdown | Strong 2008 protection, but it lagged plain momentum in the later test period. |
| Crisis-aware IBS mean reversion | Reddit IBS/lower-band entries filtered by 200-day trend and VIX circuit breakers | **0.23 Sharpe**, 1.16% annualized return, −9.92% drawdown | Reduced drawdown and turnover, but gave up too much return and missed rebounds. |
| Signal-consensus target-risk allocation | Fast/slow trend agreement + 63-day momentum + stricter selection in high volatility + defensive fallback | **0.43 Sharpe**, 5.01% annualized return, −16.00% drawdown | Excellent 2008 protection, but plain momentum was stronger in the later test period. |

## 📓 Notebooks

- [44 — Adaptive regime ensemble](notebooks/44_adaptive_regime_ensemble.ipynb)
- [45 — Crisis-aware IBS mean reversion](notebooks/45_crisis_aware_ibs_mean_reversion.ipynb)
- [46 — Signal-consensus target-risk allocation](notebooks/46_signal_consensus_target_risk.ipynb)

## 🔎 What went well and what went wrong

### Adaptive regime ensemble

The strategy was long risk-on assets about 86.7% of the time and used the defensive fallback about 13.3% of the time. It improved the 2008 crisis result to 22.20% with a −12.37% drawdown, versus 4.14% and −26.98% for 12–1 momentum.

The later test was less impressive: 0.61 Sharpe versus 1.04 for plain 12–1 momentum. The ensemble’s extra trend and high-proximity filters caused it to miss some of the strong risk-on performance in the test period. The main lesson is that smoother crisis behavior can come with opportunity cost.

### Crisis-aware IBS mean reversion

The filter reduced test turnover from 24.17 to 15.35 annualized units and reduced maximum drawdown from −13.57% to −9.92%. In the 2008 window, it reduced drawdown to −0.67%, but in the 2020 shock and 2022 inflation windows it missed profitable mean-reversion opportunities and produced negative returns.

The full test Sharpe fell from 0.53 for the original IBS rule to 0.23 for the filtered version. This is a useful failure: a risk filter can protect against one crisis while making the overall strategy less attractive.

### Signal-consensus target-risk allocation

The strategy used its consensus risk-on state about 89.6% of the time, fell back defensively 10.4% of the time, and identified high-volatility observations about 11.9% of the time. In 2008 it returned 35.01% with a −14.44% drawdown, compared with 4.14% and −26.98% for plain momentum and −20.14% and −51.87% for SPY.

But its later test Sharpe was only 0.43, compared with 1.04 for plain momentum. Signal agreement is interpretable, but it can become a delayed confirmation rule. The result is promising as a crisis-aware sleeve, not as a demonstrated replacement for momentum.

## 🧭 Research judgment

The strongest general insight is not that one hybrid “won.” It is that each combination changes the distribution of outcomes:

- regime filters can improve crisis behavior while missing rebounds;
- mean-reversion filters can reduce drawdown while reducing expectancy;
- signal consensus can make a portfolio more explainable while adding confirmation lag.

These strategies should be treated as candidates for further walk-forward research, not as finished trading systems. The next credible test would use a frozen specification on new data and a larger, survivorship-controlled universe.

## 🔗 Research influences

- [Clare, Seaton, Smith, and Thomas — The Trend Is Our Friend](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2265693)
- [Goulding, Harvey, and Mazzoleni — Momentum Turning Points](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3489539)
- [Daniel and Moskowitz — Momentum Crashes](https://www.nber.org/papers/w20439)
- [Liu, Liu, and Ma — 52-week-high momentum](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1364566)
- [Reddit IBS strategy audit](REDDIT_STRATEGY_FINDINGS.md)
- [X/Twitter volatility-risk-premium audit](TWITTER_STRATEGY_FINDINGS.md)

## ✅ Validation standards

- All three notebooks executed top-to-bottom with no stored execution errors.
- Signals use a one-bar execution delay.
- Costs, chronological splits, parameter checks, and stress windows are included.
- Original rules are fixed before reading the final test results.
- Results are compared with simple baselines and unsuccessful findings are preserved.
