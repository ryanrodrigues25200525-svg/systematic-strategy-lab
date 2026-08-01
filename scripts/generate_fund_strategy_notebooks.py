"""Generate one reader-facing notebook for each distinct fund strategy proxy."""

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = ROOT / "notebooks"


COMMON_IMPORTS = """from pathlib import Path
import sys
PROJECT_ROOT = Path.cwd()
if not (PROJECT_ROOT / 'src').exists():
    PROJECT_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import pandas as pd

from src.backtest import run_backtest, split_time_series
from src.data import load_price_panel, make_demo_ohlcv
from src.portfolio import (
    inverse_volatility_weights,
    run_portfolio_backtest,
)
from src.fund_strategies import volatility_scaled_time_series_momentum_weights
from src.research import metrics_for_period
"""


SPECS = [
    {
        "file": "12_aqr_value_factor.ipynb",
        "title": "AQR value factor proxy",
        "fund": "AQR",
        "ticker": "VTV",
        "tickers": ["VTV", "SPY"],
        "kind": "single",
        "rule": "Hold VTV, a liquid value-style ETF proxy, with a one-bar execution delay.",
        "source": "https://funds.aqr.com/Insights/Strategies/Understanding-Factor-Investing",
        "went": "The rule is transparent and low turnover, so the reader can see what value exposure means in this proxy.",
        "wrong": "VTV is not a stock-level value sort. Sector tilts, fees, internal rebalancing, and long periods of value underperformance can dominate the result.",
    },
    {
        "file": "13_aqr_momentum_factor.ipynb",
        "title": "AQR momentum factor proxy",
        "fund": "AQR",
        "ticker": "MTUM",
        "tickers": ["MTUM", "SPY"],
        "kind": "single",
        "rule": "Hold MTUM, a liquid momentum-style ETF proxy, with a one-bar execution delay.",
        "source": "https://www.aqr.com/insights/datasets/momentum-indices-monthly",
        "went": "The proxy makes the momentum idea concrete and provides a clean comparison with SPY after costs.",
        "wrong": "Momentum can reverse abruptly, become crowded, and carry more hidden turnover than the outer backtest captures because the ETF rebalances internally.",
    },
    {
        "file": "14_aqr_quality_factor.ipynb",
        "title": "AQR quality factor proxy",
        "fund": "AQR",
        "ticker": "QUAL",
        "tickers": ["QUAL", "SPY"],
        "kind": "single",
        "rule": "Hold QUAL, a quality-style ETF proxy, with a one-bar execution delay.",
        "source": "https://funds.aqr.com/Insights/Strategies/Understanding-Factor-Investing",
        "went": "Quality is easy to explain as a preference for financially stronger companies, and the ETF proxy makes the test reproducible.",
        "wrong": "Quality definitions differ across providers; the proxy may be growth-heavy, can lag speculative bull markets, and is not an exact AQR signal.",
    },
    {
        "file": "15_aqr_defensive_factor.ipynb",
        "title": "AQR defensive factor proxy",
        "fund": "AQR",
        "ticker": "USMV",
        "tickers": ["USMV", "SPY"],
        "kind": "single",
        "rule": "Hold USMV, a low-volatility defensive equity proxy, with a one-bar execution delay.",
        "source": "https://www.aqr.com/Insights/Research/White-Papers/Understanding-Defensive-Equity",
        "went": "The defensive proxy directly tests whether lower-risk equity exposure reduces volatility or drawdown.",
        "wrong": "Defensive funds can lag strong equity rallies, become concentrated in a few sectors, and still lose money in broad selloffs.",
    },
    {
        "file": "16_aqr_multi_style_blend.ipynb",
        "title": "AQR multi-style blend proxy",
        "fund": "AQR",
        "ticker": None,
        "tickers": ["VTV", "MTUM", "QUAL", "USMV", "SPY"],
        "kind": "aqr_blend",
        "rule": "Hold VTV, MTUM, QUAL, and USMV at 25% each; SPY is the benchmark.",
        "source": "https://www.aqr.com/insights/research/journal-article/investing-with-style",
        "went": "The blend tests whether value, momentum, quality, and defensive exposures diversify one another.",
        "wrong": "Equal weighting is arbitrary, the ETFs have their own fees and factor definitions, and the blend does not reproduce AQR's stock-level breadth, shorting, leverage, or optimizer.",
    },
    {
        "file": "17_bridgewater_all_weather_proxy.ipynb",
        "title": "Bridgewater All Weather-style risk balancing",
        "fund": "Bridgewater",
        "ticker": None,
        "tickers": ["SPY", "TLT", "GLD", "DBC"],
        "kind": "inverse_vol",
        "rule": "Monthly inverse-volatility weights across equities, duration, gold, and commodities.",
        "source": "https://www.bridgewater.com/research-and-insights/the-all-weather-story",
        "went": "The proxy forces the reader to connect each asset to a different growth or inflation exposure and makes concentration visible.",
        "wrong": "Inverse volatility is only a rough risk-parity approximation; correlations, leverage, financing, futures rolls, and the actual Bridgewater scenario model are missing.",
    },
    {
        "file": "18_man_ahl_fast_trend.ipynb",
        "title": "Man AHL fast trend proxy",
        "fund": "Man AHL",
        "ticker": None,
        "tickers": ["SPY", "TLT", "GLD", "DBC", "EFA", "EEM"],
        "kind": "tsmom",
        "lookback": 21,
        "rule": "Go long or short each market from its 21-day trailing return, then volatility-scale the portfolio monthly.",
        "source": "https://www.man.com/insights/need-for-speed-trend-following",
        "went": "The fast model can respond earlier when a cross-asset trend changes and demonstrates the benefit of allowing long and short signals.",
        "wrong": "Fast signals are vulnerable to whipsaws and high turnover; the ETF implementation omits futures rolls, financing, borrow, and execution.",
    },
    {
        "file": "19_man_ahl_medium_trend.ipynb",
        "title": "Man AHL medium-speed trend proxy",
        "fund": "Man AHL",
        "ticker": None,
        "tickers": ["SPY", "TLT", "GLD", "DBC", "EFA", "EEM"],
        "kind": "tsmom",
        "lookback": 63,
        "rule": "Go long or short each market from its 63-day trailing return, then volatility-scale the portfolio monthly.",
        "source": "https://www.man.com/insights/need-for-speed-trend-following",
        "went": "The medium speed balances responsiveness and persistence and is easy to compare with fast and slow siblings.",
        "wrong": "A 63-day signal can still miss a sudden reversal, and a single lookback is fragile compared with a genuinely diversified model ensemble.",
    },
    {
        "file": "20_man_ahl_slow_trend.ipynb",
        "title": "Man AHL slow trend proxy",
        "fund": "Man AHL",
        "ticker": None,
        "tickers": ["SPY", "TLT", "GLD", "DBC", "EFA", "EEM"],
        "kind": "tsmom",
        "lookback": 126,
        "rule": "Go long or short each market from its 126-day trailing return, then volatility-scale the portfolio monthly.",
        "source": "https://www.man.com/insights/need-for-speed-trend-following",
        "went": "The slower rule filters more noise and may capture persistent macro trends with less turnover.",
        "wrong": "Slow signals react late, can give back profits before exiting, and may be more correlated with traditional long-only risk.",
    },
    {
        "file": "21_man_ahl_very_slow_trend.ipynb",
        "title": "Man AHL very-slow trend proxy",
        "fund": "Man AHL",
        "ticker": None,
        "tickers": ["SPY", "TLT", "GLD", "DBC", "EFA", "EEM"],
        "kind": "tsmom",
        "lookback": 252,
        "rule": "Go long or short each market from its 252-day trailing return, then volatility-scale the portfolio monthly.",
        "source": "https://www.man.com/insights/need-for-speed-trend-following",
        "went": "The long lookback is interpretable and tests whether the strategy needs a sustained macro trend rather than short-term price movement.",
        "wrong": "The signal is slow to change, can remain wrong through a new regime, and may fail to protect against a fast crisis.",
    },
    {
        "file": "22_man_ahl_multi_speed_blend.ipynb",
        "title": "Man AHL multi-speed trend blend",
        "fund": "Man AHL",
        "ticker": None,
        "tickers": ["SPY", "TLT", "GLD", "DBC", "EFA", "EEM"],
        "kind": "ahl_blend",
        "rule": "Average 21-, 63-, 126-, and 252-day volatility-scaled time-series momentum sleeves.",
        "source": "https://www.man.com/insights/need-for-speed-trend-following",
        "went": "A multi-speed blend reduces dependence on one arbitrary lookback and makes the speed/diversification idea tangible.",
        "wrong": "Averaging four simple ETF sleeves is not the same as Man AHL's market breadth, model family, risk allocation, execution, and crisis overlays.",
    },
    {
        "file": "23_winton_trend_ensemble.ipynb",
        "title": "Winton diversified trend ensemble",
        "fund": "Winton",
        "ticker": None,
        "tickers": ["SPY", "TLT", "GLD", "DBC", "EFA", "EEM"],
        "kind": "winton_trend",
        "rule": "Average 21-, 63-, 126-, and 252-day volatility-scaled trend sleeves across six ETF markets.",
        "source": "https://www.winton.com/news/what-is-trend-following",
        "went": "The ensemble combines multiple trend speeds and multiple asset classes, which is closer to the public description than a single-market moving average.",
        "wrong": "The universe is narrow and ETF-based; currencies, rates, agricultural markets, futures rolls, and proprietary signal research are absent.",
    },
    {
        "file": "24_winton_portable_alpha.ipynb",
        "title": "Winton portable-alpha proxy",
        "fund": "Winton",
        "ticker": None,
        "tickers": ["SPY", "TLT", "GLD", "DBC", "EFA", "EEM"],
        "kind": "portable_alpha",
        "rule": "Combine 50% SPY buy-and-hold with 50% of a multi-speed diversified trend ensemble.",
        "source": "https://www.winton.com/news/winton-portable-alpha-ucits-launches-today",
        "went": "The notebook makes the return-versus-diversification trade-off explicit instead of treating trend as a replacement for equities.",
        "wrong": "Keeping an equity sleeve can dilute crisis protection, while the simple 50/50 mix ignores leverage, collateral, financing, fees, and the fund's actual implementation.",
    },
]


def md(source: str):
    return nbf.v4.new_markdown_cell(source)


def code(source: str):
    return nbf.v4.new_code_cell(source)


def make_data_code(spec: dict) -> str:
    tickers = repr(spec["tickers"])
    seeds = ", ".join(f"make_demo_ohlcv(periods=5_000, seed={i + 70}, start='2006-01-01')['close'].rename(t)" for i, _ in enumerate(spec["tickers"]))
    start = "2013-01-01" if spec["fund"] == "AQR" else "2006-01-01"
    return f"""USE_DEMO_DATA = False
TRANSACTION_COST_BPS = 10
TICKERS = {tickers}

if USE_DEMO_DATA:
    close = pd.concat([{seeds}], axis=1)
else:
    try:
        close = load_price_panel(TICKERS, '{start}', '2026-01-01')
    except Exception as exc:
        print(f'Live download unavailable ({{type(exc).__name__}}: {{exc}}); using deterministic demo data.')
        close = pd.concat([{seeds}], axis=1)

splits = split_time_series(close, train_fraction=0.60, validation_fraction=0.20)
benchmark_returns = close['SPY'].pct_change().fillna(0.0)
print(f'Data: {{close.index.min().date()}} through {{close.index.max().date()}} ({{len(close):,}} common trading days)')
"""


def make_strategy_code(spec: dict) -> str:
    kind = spec["kind"]
    if kind == "single":
        ticker = spec["ticker"]
        return f"""def make_target(panel):
    return pd.Series(1.0, index=panel.index)

def run_candidate(panel, cost_bps):
    return run_backtest(panel['{ticker}'], make_target(panel), transaction_cost_bps=cost_bps, benchmark_returns=panel['SPY'].pct_change().fillna(0.0))
"""
    if kind == "aqr_blend":
        return """def make_target(panel):
    weights = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    weights[['VTV', 'MTUM', 'QUAL', 'USMV']] = 0.25
    return weights

def run_candidate(panel, cost_bps):
    return run_portfolio_backtest(panel, make_target(panel), transaction_cost_bps=cost_bps, benchmark_returns=panel['SPY'].pct_change().fillna(0.0))
"""
    if kind == "inverse_vol":
        return """def make_target(panel):
    return inverse_volatility_weights(panel, lookback=60)

def run_candidate(panel, cost_bps):
    return run_portfolio_backtest(panel, make_target(panel), transaction_cost_bps=cost_bps, benchmark_returns=panel['SPY'].pct_change().fillna(0.0))
"""
    if kind == "tsmom":
        return f"""def make_target(panel):
    return volatility_scaled_time_series_momentum_weights(panel, lookback={spec['lookback']}, volatility_lookback=63, target_volatility=0.10)

def run_candidate(panel, cost_bps):
    return run_portfolio_backtest(panel, make_target(panel), transaction_cost_bps=cost_bps, benchmark_returns=panel['SPY'].pct_change().fillna(0.0))
"""
    if kind in {"ahl_blend", "winton_trend"}:
        return """def make_target(panel):
    sleeves = [
        volatility_scaled_time_series_momentum_weights(panel, lookback=lookback, volatility_lookback=63, target_volatility=0.10)
        for lookback in [21, 63, 126, 252]
    ]
    return sum(sleeves) / len(sleeves)

def run_candidate(panel, cost_bps):
    return run_portfolio_backtest(panel, make_target(panel), transaction_cost_bps=cost_bps, benchmark_returns=panel['SPY'].pct_change().fillna(0.0))
"""
    if kind == "portable_alpha":
        return """def make_target(panel):
    sleeves = [
        volatility_scaled_time_series_momentum_weights(panel, lookback=lookback, volatility_lookback=63, target_volatility=0.10)
        for lookback in [21, 63, 126, 252]
    ]
    trend = sum(sleeves) / len(sleeves)
    portable = trend * 0.50
    portable['SPY'] = portable['SPY'] + 0.50
    return portable

def run_candidate(panel, cost_bps):
    return run_portfolio_backtest(panel, make_target(panel), transaction_cost_bps=cost_bps, benchmark_returns=panel['SPY'].pct_change().fillna(0.0))
"""
    raise ValueError(f"Unknown strategy kind: {kind}")


def make_notebook(spec: dict):
    notebook = nbf.v4.new_notebook()
    notebook["cells"] = [
        md(
            f"# {spec['title']}\n\n"
            "## tl;dr\n\n"
            f"This standalone notebook tests one publicly described {spec['fund']} strategy idea: **{spec['rule']}**\n\n"
            "It is a transparent ETF proxy, not the fund's proprietary implementation.\n\n"
            "> Educational research only. This notebook is not investment advice."
        ),
        md(
            "## Context & methods\n\n"
            "A strategy is a rule for turning information available at time *t* into a position for a later return. "
            "The project shifts positions by one bar, charges transaction costs on exposure changes, and keeps the final 20% of the history untouched.\n\n"
            "### Key assumptions\n\n"
            f"- **Rule:** {spec['rule']}\n"
            "- Adjusted Yahoo Finance closes are used when available; a deterministic demo fallback keeps the notebook runnable offline.\n"
            "- The benchmark is SPY. Stress windows are descriptive diagnostics, not extra test sets.\n"
            "- The proxy omits proprietary data, instruments, leverage, financing, borrow, fees, and execution details."
        ),
        code(COMMON_IMPORTS),
        md(
            "## Data\n\n"
            "The common-price intersection is used so missing assets cannot silently become zero returns. "
            "The data cell prints the actual dates used when the notebook runs."
        ),
        code(make_data_code(spec)),
        md(
            f"## Public source\n\n"
            f"The strategy description is based on this public source: [{spec['fund']} research]({spec['source']}).\n\n"
            "The public description is translated into a simple rule that can be inspected line by line. This should be read as a replication of an idea, not a claim about the fund's live returns."
        ),
        code(make_strategy_code(spec)),
        md(
            "## Formal test results\n\n"
            "The table reports annualized return, volatility, Sharpe, Sortino, drawdown, turnover, and benchmark-relative return. "
            "No parameter is selected using this final test period."
        ),
        code(
            "result = run_candidate(close, TRANSACTION_COST_BPS)\n"
            "test_metrics = metrics_for_period(result, splits['test'].index)\n"
            "test_table = pd.DataFrame([test_metrics], index=[%r])\n"
            "test_table.style.format({\n"
            "    'annualized_return': '{:.2%%}', 'annualized_volatility': '{:.2%%}', 'sharpe_ratio': '{:.2f}',\n"
            "    'sortino_ratio': '{:.2f}', 'max_drawdown': '{:.2%%}', 'calmar_ratio': '{:.2f}',\n"
            "    'win_rate': '{:.2%%}', 'annualized_turnover': '{:.2f}', 'number_of_trades': '{:.0f}',\n"
            "    'total_return_after_costs': '{:.2%%}', 'benchmark_relative_return': '{:.2%%}',\n"
            "})" % spec["title"]
        ),
        code(
            "test_index = splits['test'].index\n"
            "equity = result.frame['equity'].loc[test_index]\n"
            "(equity / equity.iloc[0]).plot(figsize=(13, 5), title=%r)\n"
            "plt.ylabel('Growth of $1')\n"
            "plt.grid(alpha=0.25)\n"
            "plt.show()" % f"{spec['title']}: formal test-period equity curve"
        ),
        md(
            "## Robustness and stress diagnostics\n\n"
            "These checks show whether the result depends on transaction costs or one crisis window. They are interpretation tools, not new training data."
        ),
        code(
            "stress_windows = {'Global Financial Crisis': ('2007-10-01', '2009-03-31'), 'COVID shock': ('2020-02-19', '2020-03-23'), '2022 inflation/rates shock': ('2022-01-03', '2022-10-14')}\n"
            "stress_rows = []\n"
            "for window, (start, end) in stress_windows.items():\n"
            "    index = close.loc[start:end].index\n"
            "    returns = result.frame.loc[index, 'net_returns']\n"
            "    window_equity = (1.0 + returns).cumprod()\n"
            "    stress_rows.append({'window': window, 'return': window_equity.iloc[-1] - 1.0 if len(window_equity) else float('nan'), 'max_drawdown': (window_equity / window_equity.cummax() - 1.0).min() if len(window_equity) else float('nan')})\n"
            "stress_table = pd.DataFrame(stress_rows)\n"
            "display(stress_table.style.format({'return': '{:.2%}', 'max_drawdown': '{:.2%}'}))\n"
            "\n"
            "cost_rows = []\n"
            "for cost_bps in [0, 10, 25, 50]:\n"
            "    cost_result = run_candidate(close, cost_bps)\n"
            "    metrics = metrics_for_period(cost_result, splits['test'].index)\n"
            "    cost_rows.append({'cost_bps': cost_bps, 'test_return': metrics['total_return_after_costs'], 'test_sharpe': metrics['sharpe_ratio']})\n"
            "cost_table = pd.DataFrame(cost_rows)\n"
            "display(cost_table.style.format({'test_return': '{:.2%}', 'test_sharpe': '{:.2f}'}))"
        ),
        code(
            "print('Finding: test Sharpe =', round(float(test_metrics['sharpe_ratio']), 2))\n"
            "print('Finding: test annualized return =', round(float(test_metrics['annualized_return']) * 100, 2), 'percent')\n"
            "print('Finding: test maximum drawdown =', round(float(test_metrics['max_drawdown']) * 100, 2), 'percent')\n"
            "print('Finding: annualized turnover =', round(float(test_metrics['annualized_turnover']), 2))"
        ),
        md(
            "## What went well / what went wrong\n\n"
            f"**What went well:** {spec['went']}\n\n"
            f"**What went wrong:** {spec['wrong']}\n\n"
            "**Beginner takeaway:** A backtest is evidence about a rule under stated assumptions—not proof that the fund, proxy, or strategy will make money in the future."
        ),
    ]
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.13"},
    }
    return notebook


def main():
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    for spec in SPECS:
        path = NOTEBOOK_DIR / spec["file"]
        with path.open("w", encoding="utf-8") as handle:
            nbf.write(make_notebook(spec), handle)
        print(path.name)


if __name__ == "__main__":
    main()
