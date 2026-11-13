"""Calendar-effect masks for turn-of-month, holiday, weekday and FOMC research.

Each helper returns a **return mask**: a boolean series that is True on the
calendar days whose close-to-close return belongs to the effect. Turn a mask into
a target position with :func:`positions_from_return_mask`, which shifts it one
bar earlier because ``run_backtest`` already delays execution by one bar.

Calendar information is known years in advance, so setting a position one bar
before the event is not look-ahead. It is the only way to own the asset *during*
the event day, which is what every one of these studies measures.

References
----------
- Ariel (1987), *A monthly effect in stock returns*: returns concentrate around
  the turn of the month.
- Lakonishok and Smidt (1988), *Are seasonal anomalies real?*: turn-of-month
  evidence over 90 years of DJIA data.
- McConnell and Xu (2008), *Equity returns at the turn of the month*: the window
  is the last trading day of the month plus the first three of the next.
- Ariel (1990), *High stock returns before holidays*: the pre-holiday effect.
- Lucca and Moench (2015), *The pre-FOMC announcement drift*: about half a
  percentage point in the 24 hours before scheduled FOMC announcements.
- Chen, Chua and Others (2011), *The turn-of-the-month anomaly in the age of
  ETFs*: the window has migrated toward the first day of the month.

FOMC announcement dates in ``FOMC_ANNOUNCEMENT_DATES`` were extracted from the
Federal Reserve's own FOMC calendar and historical-materials pages and then
frozen here, so the notebook never depends on scraping a live page. Dates listed
in ``UNSCHEDULED_STATEMENTS`` are emergency or notation-vote statements rather
than scheduled meetings and are excluded by default.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FOMC_ANNOUNCEMENT_DATES: tuple[str, ...] = (
    "2011-01-26", "2011-03-15", "2011-04-27", "2011-06-22", "2011-08-09", "2011-09-21", "2011-11-02", "2011-12-13",
    "2012-01-25", "2012-03-13", "2012-04-25", "2012-06-20", "2012-08-01", "2012-09-13", "2012-10-24", "2012-12-12",
    "2013-01-30", "2013-03-20", "2013-05-01", "2013-06-19", "2013-07-31", "2013-09-18", "2013-10-30", "2013-12-18",
    "2014-01-29", "2014-03-19", "2014-04-30", "2014-06-18", "2014-07-30", "2014-09-17", "2014-10-29", "2014-12-17",
    "2015-01-28", "2015-03-18", "2015-04-29", "2015-06-17", "2015-07-29", "2015-09-17", "2015-10-28", "2015-12-16",
    "2016-01-27", "2016-03-16", "2016-04-27", "2016-06-15", "2016-07-27", "2016-09-21", "2016-11-02", "2016-12-14",
    "2017-02-01", "2017-03-15", "2017-05-03", "2017-06-14", "2017-07-26", "2017-09-20", "2017-11-01", "2017-12-13",
    "2018-01-31", "2018-03-21", "2018-05-02", "2018-06-13", "2018-08-01", "2018-09-26", "2018-11-08", "2018-12-19",
    "2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19", "2019-07-31", "2019-09-18", "2019-10-11", "2019-10-30", "2019-12-11",
    "2020-01-29", "2020-03-03", "2020-03-15", "2020-03-23", "2020-03-31", "2020-04-29", "2020-06-10", "2020-07-29", "2020-08-27", "2020-09-16", "2020-11-05", "2020-12-16",
    "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16", "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
    "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15", "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14", "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-08-22", "2025-09-17", "2025-10-29", "2025-12-10",
)

# Emergency actions, notation votes, and special meetings. The pre-FOMC drift is
# an *anticipated* event effect, so unscheduled statements are excluded by default.
UNSCHEDULED_STATEMENTS: frozenset[str] = frozenset({
    "2019-10-11",  # unscheduled statement on reserve-management purchases
    "2020-03-03",  # emergency inter-meeting rate cut
    "2020-03-15",  # emergency Sunday action
    "2020-03-23",  # emergency open-ended purchase announcement
    "2020-03-31",  # repo facility announcement
    "2025-08-22",  # special meeting
})


def _validate_index(index: pd.Index) -> pd.DatetimeIndex:
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError("Calendar helpers require a pandas DatetimeIndex of trading days")
    if index.empty:
        raise ValueError("Trading-day index cannot be empty")
    if not index.is_unique or not index.is_monotonic_increasing:
        raise ValueError("Trading-day index must be unique and increasing")
    return index


def turn_of_month_mask(
    index: pd.DatetimeIndex,
    *,
    days_before: int = 1,
    days_after: int = 3,
) -> pd.Series:
    """Mark the trading days in the turn-of-month return window.

    The classic window is the last ``days_before`` trading day of each month plus
    the first ``days_after`` trading days of the next: one plus three days, about
    19% of the calendar. Because the window is defined on trading days, a month
    that starts on a weekend is handled correctly.
    """

    index = _validate_index(index)
    if days_before < 1 or days_after < 0:
        raise ValueError("days_before must be at least 1 and days_after non-negative")

    period = pd.Series(index.to_period("M"), index=index)
    forward_position = period.groupby(period).cumcount()
    backward_position = period.groupby(period).cumcount(ascending=False)

    mask = (backward_position < days_before) | (forward_position < days_after)
    return pd.Series(mask.to_numpy(), index=index, name="turn_of_month")


def day_of_week_mask(index: pd.DatetimeIndex, *, weekday: int = 2) -> pd.Series:
    """Mark every trading day that falls on ``weekday`` (0 = Monday)."""

    index = _validate_index(index)
    if not 0 <= weekday <= 6:
        raise ValueError("weekday must be between 0 (Monday) and 6 (Sunday)")
    return pd.Series(_weekday_numbers(index) == weekday, index=index, name=f"weekday_{weekday}")


def _weekday_numbers(values) -> np.ndarray:
    """Return weekday numbers (0 = Monday) across pandas versions.

    pandas 3 renamed ``dayofweek`` to ``day_of_week``; the fallback keeps this
    module importable on pandas 2 without emitting a deprecation warning.
    """

    attribute = "day_of_week" if hasattr(values, "day_of_week") else "dayofweek"
    return np.asarray(getattr(values, attribute))


def _easter_sunday(year: int) -> pd.Timestamp:
    """Anonymous Gregorian algorithm for the date of Easter Sunday."""

    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return pd.Timestamp(year=year, month=month, day=day + 1)


def _nth_weekday(year: int, month: int, weekday: int, count: int) -> pd.Timestamp:
    """N-th occurrence of ``weekday`` in a month (count=1 is the first)."""

    first = pd.Timestamp(year=year, month=month, day=1)
    offset = (weekday - int(_weekday_numbers(first))) % 7
    return first + pd.Timedelta(days=offset + 7 * (count - 1))


def _last_weekday(year: int, month: int, weekday: int) -> pd.Timestamp:
    end = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthBegin(1) - pd.Timedelta(days=1)
    offset = (int(_weekday_numbers(end)) - weekday) % 7
    return end - pd.Timedelta(days=offset)


def _observed_holiday(month: int, day: int, year: int, *, saturday_closure: bool = True) -> pd.Timestamp | None:
    """Apply the NYSE weekend observance rule to a fixed-date holiday."""

    timestamp = pd.Timestamp(year=year, month=month, day=day)
    weekday = int(_weekday_numbers(timestamp))
    if weekday == 5:  # Saturday
        if not saturday_closure:
            return None
        return timestamp - pd.Timedelta(days=1)
    if weekday == 6:  # Sunday
        return timestamp + pd.Timedelta(days=1)
    return timestamp


def nyse_holidays(start_year: int, end_year: int) -> pd.DatetimeIndex:
    """Return the NYSE closure dates for a range of years.

    The rule set is the one the exchange publishes: New Year's Day, Martin Luther
    King Day, Washington's Birthday, Good Friday, Memorial Day, Juneteenth (from
    2022), Independence Day, Labor Day, Thanksgiving and Christmas. Federal
    holidays that are *not* market closures — Columbus Day and Veterans Day —
    are deliberately excluded.
    """

    if start_year > end_year:
        raise ValueError("start_year cannot exceed end_year")
    dates: list[pd.Timestamp] = []
    for year in range(start_year, end_year + 1):
        # NYSE does not observe New Year's Day when it falls on a Saturday.
        new_year = _observed_holiday(1, 1, year, saturday_closure=False)
        if new_year is not None:
            dates.append(new_year)
        dates.append(_nth_weekday(year, 1, 0, 3))  # MLK Day
        dates.append(_nth_weekday(year, 2, 0, 3))  # Washington's Birthday
        dates.append(_easter_sunday(year) - pd.Timedelta(days=2))  # Good Friday
        dates.append(_last_weekday(year, 5, 0))  # Memorial Day
        if year >= 2022:
            juneteenth = _observed_holiday(6, 19, year)
            if juneteenth is not None:
                dates.append(juneteenth)
        independence = _observed_holiday(7, 4, year)
        if independence is not None:
            dates.append(independence)
        dates.append(_nth_weekday(year, 9, 0, 1))  # Labor Day
        dates.append(_nth_weekday(year, 11, 3, 4))  # Thanksgiving
        christmas = _observed_holiday(12, 25, year)
        if christmas is not None:
            dates.append(christmas)
    return pd.DatetimeIndex(sorted(set(dates)))


def pre_holiday_mask(index: pd.DatetimeIndex) -> pd.Series:
    """Mark the last trading day before each NYSE holiday.

    Ariel (1990) documents unusually high returns on the day before a market
    holiday. The mask marks the trading day whose close-to-close return is that
    pre-holiday session.
    """

    index = _validate_index(index)
    holidays = nyse_holidays(index[0].year - 1, index[-1].year + 1)
    holiday_positions = index.searchsorted(holidays)
    previous = holiday_positions - 1
    valid = (holiday_positions > 0) & (previous < len(index))
    mask = np.zeros(len(index), dtype=bool)
    mask[previous[valid]] = True
    # A "holiday" that is not preceded by any trading day in range is ignored.
    holiday_positions = holiday_positions[holiday_positions > 0]
    return pd.Series(mask, index=index, name="pre_holiday")


def scheduled_fomc_dates() -> pd.DatetimeIndex:
    """Scheduled FOMC announcement dates only, in ascending order."""

    dates = [stamp for stamp in FOMC_ANNOUNCEMENT_DATES if stamp not in UNSCHEDULED_STATEMENTS]
    return pd.DatetimeIndex(sorted(dates))


def pre_fomc_mask(
    index: pd.DatetimeIndex,
    *,
    dates: pd.DatetimeIndex | None = None,
    include_unscheduled: bool = False,
) -> pd.Series:
    """Mark the trading days whose return is the pre-announcement session.

    The pre-FOMC drift is measured from the close before the announcement to the
    announcement-day close, which is exactly the announcement day's close-to-close
    return. Announcements that fall on a non-trading day are dropped, and
    emergency statements are excluded unless ``include_unscheduled`` is set.
    """

    index = _validate_index(index)
    if dates is None:
        dates = pd.DatetimeIndex(sorted(FOMC_ANNOUNCEMENT_DATES if include_unscheduled else scheduled_fomc_dates()))
    else:
        dates = pd.DatetimeIndex(dates)
        if dates.empty:
            raise ValueError("dates cannot be empty")
    mask = index.isin(dates)
    return pd.Series(mask, index=index, name="pre_fomc")


def positions_from_return_mask(mask: pd.Series) -> pd.Series:
    """Convert a return mask into a target position for ``run_backtest``.

    ``run_backtest`` applies a target set at ``t`` to the return from ``t`` to
    ``t + 1``. To earn the return of a masked day, the position must therefore be
    set on the previous bar. Calendar events are known in advance, so this shift
    is not look-ahead; it is the difference between owning the asset during the
    event and buying at its closing print.
    """

    if not isinstance(mask, pd.Series) or not isinstance(mask.index, pd.DatetimeIndex):
        raise ValueError("mask must be a pandas Series indexed by a DatetimeIndex")
    if not mask.index.is_monotonic_increasing or not mask.index.is_unique:
        raise ValueError("mask index must be unique and increasing")
    shifted = mask.astype(bool).shift(-1).fillna(False)
    return pd.Series(shifted.to_numpy(dtype=float), index=mask.index, name="target_position")
