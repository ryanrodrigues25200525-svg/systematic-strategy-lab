from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks"


def md(text):
    return nbf.v4.new_markdown_cell(text)


def code(text):
    return nbf.v4.new_code_cell(text)


common_imports = r'''
from pathlib import Path
import sys
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown

ROOT = Path.cwd()
if not (ROOT / "src").exists():
    if (ROOT.parent / "src").exists():
        ROOT = ROOT.parent
    elif "__file__" in globals():
        ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backtest import run_backtest, split_time_series
from src.data import load_price_data, load_price_panel, make_demo_ohlcv
from src.metrics import calculate_metrics
from src.portfolio import run_portfolio_backtest
from src.research import metrics_for_period

plt.rcParams.update({
    "figure.figsize": (12, 5),
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
})
'''


ibs_notebook = nbf.v4.new_notebook(metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}})
ibs_notebook.cells = [
    md("""# 🔎 Reddit strategy audit: IBS lower-band mean reversion

## 🧭 tl;dr

This notebook audits a Reddit post that reported a **2.11 Sharpe ratio** for a long-only SPY mean-reversion strategy. The setup combines a range-based lower band with the Internal Bar Strength (IBS) indicator. The post’s headline result came from an improved version with a dynamic stop, so we test the **published original rules first** and label the gap clearly.

> Educational research only. This is not financial advice. A high backtest Sharpe is a hypothesis to investigate, not evidence of a reliable live edge.

<div style="border-left: 5px solid #F59E0B; padding: 0.85em 1em; margin: 1em 0 1.4em; background: #FFFBEB; border-radius: 8px;"><strong>🧑‍🏫 Reader guide</strong><br>Start with the exact rules, then inspect the formal test, the cost curve, and the parameter sensitivity. The final section explains what survived and what did not.</div>
"""),
    md("""## 📚 Source and research question

The Reddit post describes a strategy with four parameters: a 25-day average range, a 10-day rolling high, a 2.5× range band, and an IBS threshold of 0.30. It reported 13.0% annualized return, 20.3% maximum drawdown, 414 trades, and a 69% win rate over roughly 25 years. The post also says the displayed result used an **improved strategy with a dynamic stop**, which means the headline cannot be treated as a clean reproduction target.

Source: [Reddit mean-reversion post](https://www.reddit.com/r/algotrading/comments/1cwsco8/a_mean_reversion_strategy_with_211_sharpe/).

Research question: does the simple published rule still produce attractive, net-of-cost risk-adjusted performance when signals are shifted to the next bar and tested on an untouched period?
"""),
    code(common_imports),
    code(r'''
def load_spy_ohlcv():
    try:
        data = load_price_data("SPY", "1993-01-01", "2026-01-01")
        source = "Yahoo Finance adjusted daily SPY data"
    except Exception as exc:
        data = make_demo_ohlcv(periods=8_000, seed=303, start="1993-01-01")
        source = f"deterministic demo OHLCV fallback ({type(exc).__name__})"
    return data, source


ohlcv, data_source = load_spy_ohlcv()
print(f"Data source: {data_source}")
print(f"Observations: {len(ohlcv):,} | {ohlcv.index.min().date()} to {ohlcv.index.max().date()}")
display(ohlcv.head())
'''),
    md("""## 📜 Exact rules being tested

At each closing price:

1. Compute the 25-day average of the daily high–low range.
2. Compute IBS = `(close − low) / (high − low)`.
3. Compute the lower band = 10-day rolling high − 2.5 × average range.
4. Enter long when `close < lower_band` **and** `IBS < 0.30`.
5. Exit when `close > yesterday’s high`.
6. Hold cash otherwise.

The shared backtester applies a one-bar delay: a signal observed at today’s close is held for the next session’s return. That is conservative and avoids same-close look-ahead. The Reddit post’s reported result used an improved dynamic-stop variant, so the comparison below is intentionally “claim versus original-rule audit,” not “claim versus claimed implementation.”
"""),
    code(r'''
def reddit_ibs_signal(ohlcv, range_window=25, high_window=10, band_multiplier=2.5, ibs_threshold=0.30):
    high = ohlcv["high"]
    low = ohlcv["low"]
    close = ohlcv["close"]
    average_range = (high - low).rolling(range_window, min_periods=range_window).mean()
    rolling_high = high.rolling(high_window, min_periods=high_window).max()
    lower_band = rolling_high - band_multiplier * average_range
    ibs = ((close - low) / (high - low).replace(0.0, np.nan)).fillna(0.5)

    target = pd.Series(0.0, index=close.index, name="target_position")
    state = 0.0
    for timestamp in close.index:
        if state == 0.0 and close.loc[timestamp] < lower_band.loc[timestamp] and ibs.loc[timestamp] < ibs_threshold:
            state = 1.0
        elif state == 1.0 and close.loc[timestamp] > high.shift(1).loc[timestamp]:
            state = 0.0
        target.loc[timestamp] = state
    diagnostics = pd.DataFrame({"close": close, "lower_band": lower_band, "ibs": ibs, "target_position": target})
    return target, diagnostics


target, diagnostics = reddit_ibs_signal(ohlcv)
result = run_backtest(ohlcv["close"], target, transaction_cost_bps=10.0, benchmark_returns=ohlcv["close"].pct_change().fillna(0.0))
benchmark = run_backtest(ohlcv["close"], pd.Series(1.0, index=ohlcv.index), transaction_cost_bps=10.0)
splits = split_time_series(ohlcv[["close"]])
periods = {name: frame.index for name, frame in splits.items()}

def pretty_metrics(result, period_index):
    metrics = metrics_for_period(result, period_index)
    keys = ["annualized_return", "annualized_volatility", "sharpe_ratio", "sortino_ratio", "max_drawdown", "calmar_ratio", "win_rate", "annualized_turnover", "number_of_trades", "total_return_after_costs", "benchmark_relative_return"]
    return pd.Series({key: metrics.get(key, np.nan) for key in keys})

summary = pd.DataFrame({"IBS lower-band": pretty_metrics(result, ohlcv.index), "SPY buy & hold": pretty_metrics(benchmark, ohlcv.index)})
summary.style.format({k: ("{:.2%}" if k in ["annualized_return", "annualized_volatility", "max_drawdown", "win_rate", "total_return_after_costs", "benchmark_relative_return"] else "{:.2f}") for k in summary.index})
'''),
    md("""## 📈 Formal results: gross versus net of costs

The default run charges 10 basis points per unit of turnover. For a low-frequency strategy this may be conservative; the purpose is to make the assumption visible. The table includes the full sample and the untouched chronological test period. Metrics use daily returns including cash days, which is the standard portfolio-level Sharpe convention.
"""),
    code(r'''
rows = []
for name, test_result in [("IBS lower-band", result), ("SPY buy & hold", benchmark)]:
    for period_name, period_index in periods.items():
        metrics = metrics_for_period(test_result, period_index)
        rows.append({"strategy": name, "period": period_name, **metrics})
results_table = pd.DataFrame(rows).set_index(["strategy", "period"])
display(results_table[["annualized_return", "annualized_volatility", "sharpe_ratio", "sortino_ratio", "max_drawdown", "calmar_ratio", "win_rate", "annualized_turnover", "number_of_trades", "total_return_after_costs"]].style.format({"annualized_return": "{:.2%}", "annualized_volatility": "{:.2%}", "sharpe_ratio": "{:.2f}", "sortino_ratio": "{:.2f}", "max_drawdown": "{:.2%}", "calmar_ratio": "{:.2f}", "win_rate": "{:.2%}", "annualized_turnover": "{:.2f}", "number_of_trades": "{:.0f}", "total_return_after_costs": "{:.2%}"}))

active = result.frame.loc[result.frame["held_position"] != 0.0, "net_returns"]
active_sharpe = active.mean() / active.std(ddof=1) * np.sqrt(252) if len(active) > 1 and active.std(ddof=1) else 0.0
print(f"Active-days Sharpe (not comparable with daily portfolio Sharpe): {active_sharpe:.2f}")
'''),
    code(r'''
fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
axes[0].plot(result.frame.index, result.equity / result.equity.iloc[0], label="IBS strategy", color="#2563EB")
axes[0].plot(benchmark.frame.index, benchmark.equity / benchmark.equity.iloc[0], label="SPY buy & hold", color="#64748B", alpha=0.8)
axes[0].set_title("Equity curve: Reddit IBS rule vs buy & hold")
axes[0].set_ylabel("Growth of $1")
axes[0].legend()
axes[1].fill_between(result.frame.index, result.drawdown, 0, color="#DC2626", alpha=0.25)
axes[1].set_title("IBS strategy drawdown")
axes[1].set_ylabel("Drawdown")
plt.tight_layout()
'''),
    md("""## 🧪 Robustness checks

The parameter grid is descriptive rather than a license to pick the best result. It ranks combinations on the validation period, then shows how the original Reddit parameters behave on the untouched test period. This separation matters because selecting the best Sharpe after looking at the test period converts the test into training data.
"""),
    code(r'''
grid_rows = []
for range_window, high_window, band_multiplier, ibs_threshold in itertools.product([21, 25, 30], [5, 10, 15], [2.0, 2.5, 3.0], [0.25, 0.30, 0.40]):
    candidate, _ = reddit_ibs_signal(ohlcv, range_window, high_window, band_multiplier, ibs_threshold)
    candidate_result = run_backtest(ohlcv["close"], candidate, transaction_cost_bps=10.0, benchmark_returns=ohlcv["close"].pct_change().fillna(0.0))
    validation_metrics = metrics_for_period(candidate_result, periods["validation"])
    test_metrics = metrics_for_period(candidate_result, periods["test"])
    grid_rows.append({"range_window": range_window, "high_window": high_window, "band_multiplier": band_multiplier, "ibs_threshold": ibs_threshold, "validation_sharpe": validation_metrics["sharpe_ratio"], "validation_return": validation_metrics["annualized_return"], "test_sharpe": test_metrics["sharpe_ratio"], "test_return": test_metrics["annualized_return"], "test_drawdown": test_metrics["max_drawdown"]})
sensitivity = pd.DataFrame(grid_rows).sort_values("validation_sharpe", ascending=False)
display(sensitivity.head(10).style.format({"validation_sharpe": "{:.2f}", "validation_return": "{:.2%}", "test_sharpe": "{:.2f}", "test_return": "{:.2%}", "test_drawdown": "{:.2%}"}))
original_row = sensitivity.loc[(sensitivity.range_window == 25) & (sensitivity.high_window == 10) & (sensitivity.band_multiplier == 2.5) & (sensitivity.ibs_threshold == 0.30)].iloc[0]
print("Original Reddit parameters:", original_row.to_dict())
'''),
    code(r'''
cost_rows = []
for cost_bps in [0, 5, 10, 25, 50]:
    cost_result = run_backtest(ohlcv["close"], target, transaction_cost_bps=cost_bps, benchmark_returns=ohlcv["close"].pct_change().fillna(0.0))
    m = metrics_for_period(cost_result, periods["test"])
    cost_rows.append({"transaction_cost_bps": cost_bps, "test_return": m["annualized_return"], "test_sharpe": m["sharpe_ratio"], "test_drawdown": m["max_drawdown"], "test_turnover": m["annualized_turnover"]})
cost_table = pd.DataFrame(cost_rows)
display(cost_table.style.format({"test_return": "{:.2%}", "test_sharpe": "{:.2f}", "test_drawdown": "{:.2%}", "test_turnover": "{:.2f}"}))
'''),
    md("""## ⚖️ What went well / what went wrong

### ✅ What went well

- The rules are specific enough to audit: entry, exit, indicators, and parameters are all explicit.
- The one-bar delay removes the most obvious same-close look-ahead problem.
- IBS adds information about where the close sits inside the day’s range, which is economically plausible for short-term exhaustion.
- The cost table and active-days Sharpe show why a headline Sharpe needs a definition and a trading-cost context.

### ⚠️ What went wrong or remains uncertain

- The post’s reported 2.11 Sharpe came from an improved dynamic-stop version, not necessarily the original four-rule setup tested here.
- A 48-combination parameter grid can create a strong-looking result by chance. The Reddit comments also raised overfitting and trade-count concerns.
- SPY’s long history, adjusted prices, execution at the next bar, and data vendor choices may differ from the original test.
- A short-horizon edge can be sensitive to spreads, fills, market-hours conventions, and whether “close” means an executable closing auction price.
- The result is not evidence that the strategy will preserve its Sharpe out of sample or live.

**Bottom line:** treat the Reddit Sharpe as an interesting hypothesis. The reproducible evidence is the cost-aware, untouched-test result above—not the number in the post title.
"""),
]


dual_notebook = nbf.v4.new_notebook(metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}})
dual_notebook.cells = [
    md("""# 🌍 Reddit strategy audit: global dual momentum rotation

## 🧭 tl;dr

This notebook tests a Reddit-style dual-momentum rotation: use an absolute trend filter, compare trailing performance of US equities and developed ex-US equities, and rotate to long-duration bonds when the equity filter is off. The Reddit post reported **17.26% CAGR, −45% maximum drawdown, and 0.58 Sharpe**. We reproduce the idea with liquid ETF proxies and make the sample, rebalance schedule, and costs explicit.

> Educational research only. This is not financial advice. The goal is to understand a rule, not to promise a return.

<div style="border-left: 5px solid #10B981; padding: 0.85em 1em; margin: 1em 0 1.4em; background: #ECFDF5; border-radius: 8px;"><strong>🧑‍🏫 Reader guide</strong><br>Follow the signal construction first. Then compare monthly rotation with a buy-and-hold benchmark, inspect the test split, and read the sensitivity results before drawing conclusions.</div>
"""),
    md("""## 📚 Source and research question

The Reddit post describes a leveraged dual-momentum backtest using a 200-day trend filter and relative momentum between US and international stocks, with bonds as the defensive asset. It reports 17.26% CAGR, −45% drawdown, and 0.58 Sharpe. Discussion in the thread points out that start dates, recent-period performance, and daily-checking/churn assumptions can materially change the result.

Source: [Reddit dual-momentum post](https://www.reddit.com/r/LETFs/comments/1jj4tad/leveraged_dual_momentum_backtest/).

This notebook uses SPY, EFA, and TLT as liquid, unlevered proxies. EFA begins after SPY, so the common sample is shorter than a backtest using index histories. That is a deliberate data-availability limitation, not something to hide.
"""),
    code(common_imports),
    code(r'''
def load_dual_momentum_panel():
    try:
        panel = load_price_panel(["SPY", "EFA", "TLT"], "2003-01-01", "2026-01-01")
        source = "Yahoo Finance adjusted daily closes"
    except Exception as exc:
        demo = make_demo_ohlcv(periods=5_800, seed=404, start="2003-01-01")["close"]
        panel = pd.DataFrame({"SPY": demo, "EFA": demo * 0.92, "TLT": demo * 1.08}, index=demo.index)
        source = f"deterministic demo close panel fallback ({type(exc).__name__})"
    return panel.dropna(), source


close, data_source = load_dual_momentum_panel()
print(f"Data source: {data_source}")
print(f"Observations: {len(close):,} | {close.index.min().date()} to {close.index.max().date()}")
display(close.head())
'''),
    md("""## 📜 Exact test rule

At the first trading day of each month:

1. **Absolute momentum filter:** if SPY is above its trailing 200-day simple moving average, the equity sleeve is eligible; otherwise use TLT.
2. **Relative momentum:** compare the prior 252-trading-day return of SPY and EFA.
3. If the filter is on, allocate 100% to whichever equity has the higher 252-day return.
4. If the filter is off, allocate 100% to TLT.
5. Hold the chosen asset until the next monthly rebalance.

All scores are shifted by one trading day before the decision and the portfolio backtester shifts the target weights one further bar before applying returns. This keeps the signal from using a return that has not yet been observed.
"""),
    code(r'''
def reddit_dual_momentum_weights(close, absolute_window=200, relative_window=252):
    close = close[["SPY", "EFA", "TLT"]].astype(float)
    sma = close["SPY"].rolling(absolute_window, min_periods=absolute_window).mean().shift(1)
    relative_score = close[["SPY", "EFA"]].pct_change(relative_window).shift(1)
    month = close.index.to_period("M")
    month_start = pd.Series(month, index=close.index).ne(pd.Series(month, index=close.index).shift(1))
    candidates = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    for timestamp in close.index[month_start.to_numpy()]:
        if pd.isna(sma.loc[timestamp]) or relative_score.loc[timestamp].isna().any():
            continue
        if close.loc[timestamp, "SPY"] <= sma.loc[timestamp]:
            candidates.loc[timestamp, "TLT"] = 1.0
        else:
            winner = relative_score.loc[timestamp].idxmax()
            candidates.loc[timestamp, winner] = 1.0
    monthly = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
    monthly.loc[month_start] = candidates.loc[month_start]
    return monthly.ffill().fillna(0.0)


weights = reddit_dual_momentum_weights(close)
portfolio = run_portfolio_backtest(close, weights, transaction_cost_bps=10.0, benchmark_returns=close["SPY"].pct_change().fillna(0.0))
buy_hold = run_portfolio_backtest(close, pd.DataFrame({"SPY": 1.0, "EFA": 0.0, "TLT": 0.0}, index=close.index), transaction_cost_bps=10.0, benchmark_returns=close["SPY"].pct_change().fillna(0.0))
splits = split_time_series(close)
periods = {name: frame.index for name, frame in splits.items()}
'''),
    md("""## 📈 Formal results

The table reports net returns after 10 basis points per unit of portfolio turnover. The benchmark is SPY buy and hold over the same common sample. Because the Reddit post may use different underlying indexes, leverage, and start dates, a numerical mismatch is expected; the useful comparison is whether the economic behavior survives under a transparent ETF implementation.
"""),
    code(r'''
rows = []
for name, test_result in [("Reddit-style dual momentum", portfolio), ("SPY buy & hold", buy_hold)]:
    for period_name, period_index in periods.items():
        metrics = metrics_for_period(test_result, period_index)
        rows.append({"strategy": name, "period": period_name, **metrics})
results_table = pd.DataFrame(rows).set_index(["strategy", "period"])
display(results_table[["annualized_return", "annualized_volatility", "sharpe_ratio", "sortino_ratio", "max_drawdown", "calmar_ratio", "win_rate", "annualized_turnover", "number_of_trades", "total_return_after_costs"]].style.format({"annualized_return": "{:.2%}", "annualized_volatility": "{:.2%}", "sharpe_ratio": "{:.2f}", "sortino_ratio": "{:.2f}", "max_drawdown": "{:.2%}", "calmar_ratio": "{:.2f}", "win_rate": "{:.2%}", "annualized_turnover": "{:.2f}", "number_of_trades": "{:.0f}", "total_return_after_costs": "{:.2%}"}))
'''),
    code(r'''
fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
axes[0].plot(portfolio.frame.index, portfolio.frame.equity / portfolio.frame.equity.iloc[0], label="Dual momentum", color="#059669")
axes[0].plot(buy_hold.frame.index, buy_hold.frame.equity / buy_hold.frame.equity.iloc[0], label="SPY buy & hold", color="#64748B", alpha=0.8)
axes[0].set_title("Equity curve: Reddit-style dual momentum vs SPY")
axes[0].set_ylabel("Growth of $1")
axes[0].legend()
axes[1].fill_between(portfolio.frame.index, portfolio.frame.drawdown, 0, color="#DC2626", alpha=0.25)
axes[1].set_title("Dual momentum drawdown")
axes[1].set_ylabel("Drawdown")
plt.tight_layout()
'''),
    md("""## 🛡️ Regime and parameter checks

The most important fragility tests here are not just the best Sharpe. We check whether the result changes with the trend window, momentum lookback, transaction cost, and chronological period. Parameter combinations are ranked on validation only; the original 200/252 rule is evaluated on the untouched test period without retuning.
"""),
    code(r'''
grid_rows = []
for absolute_window, relative_window in itertools.product([126, 200, 252], [126, 189, 252]):
    candidate_weights = reddit_dual_momentum_weights(close, absolute_window, relative_window)
    candidate = run_portfolio_backtest(close, candidate_weights, transaction_cost_bps=10.0, benchmark_returns=close["SPY"].pct_change().fillna(0.0))
    validation_metrics = metrics_for_period(candidate, periods["validation"])
    test_metrics = metrics_for_period(candidate, periods["test"])
    grid_rows.append({"absolute_window": absolute_window, "relative_window": relative_window, "validation_sharpe": validation_metrics["sharpe_ratio"], "validation_return": validation_metrics["annualized_return"], "test_sharpe": test_metrics["sharpe_ratio"], "test_return": test_metrics["annualized_return"], "test_drawdown": test_metrics["max_drawdown"]})
sensitivity = pd.DataFrame(grid_rows).sort_values("validation_sharpe", ascending=False)
display(sensitivity.style.format({"validation_sharpe": "{:.2f}", "validation_return": "{:.2%}", "test_sharpe": "{:.2f}", "test_return": "{:.2%}", "test_drawdown": "{:.2%}"}))
'''),
    code(r'''
cost_rows = []
for cost_bps in [0, 5, 10, 25, 50]:
    cost_result = run_portfolio_backtest(close, weights, transaction_cost_bps=cost_bps, benchmark_returns=close["SPY"].pct_change().fillna(0.0))
    m = metrics_for_period(cost_result, periods["test"])
    cost_rows.append({"transaction_cost_bps": cost_bps, "test_return": m["annualized_return"], "test_sharpe": m["sharpe_ratio"], "test_drawdown": m["max_drawdown"], "test_turnover": m["annualized_turnover"]})
display(pd.DataFrame(cost_rows).style.format({"test_return": "{:.2%}", "test_sharpe": "{:.2f}", "test_drawdown": "{:.2%}", "test_turnover": "{:.2f}"}))
'''),
    code(r'''
held_weights = portfolio.held_weights
allocation = held_weights.groupby(held_weights.index.to_period("Y")).mean().round(2)
display(allocation.tail(10))
allocation.plot.area(figsize=(12, 4), title="Average annual held weights")
plt.ylabel("Weight")
plt.tight_layout()
'''),
    md("""## ⚖️ What went well / what went wrong

### ✅ What went well

- The economic story is intuitive: momentum selects the stronger equity market while the trend filter attempts to reduce equity exposure during prolonged weakness.
- Monthly rebalancing keeps turnover and implementation complexity visible.
- The strategy can diversify a pure equity benchmark by holding TLT during some equity drawdowns.
- A common-sample ETF test makes the data limitation explicit instead of silently filling missing history with an index proxy.

### ⚠️ What went wrong or remains uncertain

- The Reddit headline is not an apples-to-apples benchmark: underlying indexes, leverage, start date, and execution rules may differ.
- Trend filters can exit late, whipsaw in sideways markets, and miss sharp rebounds.
- Bond exposure is not a guaranteed crisis hedge; rising-rate shocks can hurt both stocks and long-duration bonds.
- Selecting a window after seeing the full sensitivity table would overfit. The test-period result must remain tied to the pre-specified 200/252 rule.
- The thread itself highlights start-date dependence and recent underperformance. A high CAGR in one sample is not a stable expected return.

**Bottom line:** dual momentum is a credible, testable allocation rule, but the Reddit post’s return and Sharpe are sample-specific claims. The robust takeaway is the behavior across periods and costs, not the headline CAGR.
"""),
]


for path, notebook in [
    (OUT / "36_reddit_ibs_mean_reversion.ipynb", ibs_notebook),
    (OUT / "37_reddit_dual_momentum.ipynb", dual_notebook),
]:
    nbf.write(notebook, path)
    print(path)
