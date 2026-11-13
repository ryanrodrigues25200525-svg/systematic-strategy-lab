"""Tests for calendar-effect masks: turn-of-month, day-of-week, holidays, FOMC."""

import numpy as np
import pandas as pd

from src.backtest import run_backtest
from src.calendar_effects import (
    FOMC_ANNOUNCEMENT_DATES,
    scheduled_fomc_dates,
    day_of_week_mask,
    nyse_holidays,
    positions_from_return_mask,
    pre_fomc_mask,
    pre_holiday_mask,
    turn_of_month_mask,
)


def _trading_index(start="2019-01-01", end="2021-12-31"):
    return pd.bdate_range(start, end)


def test_turn_of_month_mask_covers_last_day_plus_three():
    index = _trading_index()
    mask = turn_of_month_mask(index, days_before=1, days_after=3)
    assert mask.dtype == bool
    assert np.isclose(mask.mean(), 4.0 / 21.0, atol=0.03)

    first_of_month = ~pd.Series(index.to_period("M"), index=index).duplicated()
    for timestamp in index[first_of_month]:
        position = index.get_loc(timestamp)
        window = index[max(0, position - 1) : position + 3]
        assert mask.loc[window].all(), timestamp


def test_nyse_holidays_match_known_2024_calendar():
    holidays = nyse_holidays(2024, 2024)
    expected = pd.DatetimeIndex([
        "2024-01-01",  # New Year
        "2024-01-15",  # Martin Luther King
        "2024-02-19",  # Washington's birthday
        "2024-03-29",  # Good Friday
        "2024-05-27",  # Memorial Day
        "2024-06-19",  # Juneteenth
        "2024-07-04",  # Independence Day
        "2024-09-02",  # Labor Day
        "2024-11-28",  # Thanksgiving
        "2024-12-25",  # Christmas
    ])
    assert list(holidays) == list(expected)


def test_pre_holiday_mask_excludes_non_market_federal_holidays():
    index = _trading_index()
    mask = pre_holiday_mask(index)
    mask_dates = set(index[mask])
    # Columbus Day and Veterans Day are federal holidays but not NYSE closures.
    assert pd.Timestamp("2020-10-12") not in mask_dates
    assert pd.Timestamp("2020-11-11") not in mask_dates
    # The last trading day before Independence Day must be flagged.
    assert pd.Timestamp("2020-07-02") in mask_dates
    assert pd.Timestamp("2021-04-01") in mask_dates  # day before Good Friday 2021-04-02
    assert 8 <= int(mask.sum()) / 3 <= 11


def test_pre_fomc_mask_uses_scheduled_announcement_days_only():
    index = _trading_index("2019-01-01", "2021-12-31")
    mask = pre_fomc_mask(index)
    mask_dates = set(index[mask])

    assert pd.Timestamp("2021-12-15") in mask_dates
    assert pd.Timestamp("2021-12-16") not in mask_dates
    # Three years of scheduled meetings: eight per year, all on trading days.
    assert int(mask.sum()) == 8 * 3
    # Every scheduled announcement must land on a trading day in the index.
    scheduled = scheduled_fomc_dates()
    in_range = scheduled[(scheduled >= index[0]) & (scheduled <= index[-1])]
    assert len(in_range) == 24
    assert in_range.isin(index).all()


def test_day_of_week_mask_matches_calendar():
    index = _trading_index()
    mask = day_of_week_mask(index, weekday=2)
    assert (np.asarray(index[mask].dayofweek) == 2).all()
    assert np.isclose(mask.mean(), 0.2, atol=0.02)
    try:
        day_of_week_mask(index, weekday=7)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected an invalid weekday to fail")


def test_positions_from_return_mask_earn_exactly_the_masked_days():
    index = _trading_index("2020-01-01", "2020-06-30")
    mask = turn_of_month_mask(index)
    positions = positions_from_return_mask(mask)

    # 1% return on masked days, flat otherwise.
    daily = pd.Series(np.where(mask.to_numpy(), 0.01, 0.0), index=index)
    close = 100.0 * (1.0 + daily).cumprod()
    result = run_backtest(close, positions, transaction_cost_bps=0.0)

    # The first bar of the sample cannot be earned: its position would need a
    # bar before the data starts.
    capturable = int(mask.sum()) - int(bool(mask.iloc[0]))
    expected = float((1.01 ** capturable) - 1.0)
    assert np.isclose(result.metrics["total_return_after_costs"], expected, atol=1e-9)
    # Nothing is earned on unmasked days.
    unmasked = ~mask
    assert np.allclose(result.frame.loc[unmasked, "gross_returns"].to_numpy(), 0.0)


def test_calendar_masks_reject_bad_inputs():
    for call in (
        lambda: turn_of_month_mask(pd.Index(["2020-01-01"]), days_before=0),
        lambda: turn_of_month_mask(_trading_index(), days_after=-1),
        lambda: pre_fomc_mask(_trading_index(), dates=pd.DatetimeIndex([])),
        lambda: positions_from_return_mask(pd.Series([1, 0], index=[1, 2])),
    ):
        try:
            call()
        except (ValueError, TypeError):
            continue
        raise AssertionError("Expected invalid calendar input to fail")
