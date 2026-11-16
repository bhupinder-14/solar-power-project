"""
SolarCast AI — Temporal Feature Engineering.

Extracts calendar-based and cyclical time features from a datetime-indexed
DataFrame for solar power forecasting.

Functions
---------
add_time_features      : basic calendar features (hour, day-of-week, …)
add_cyclical_encoding  : sin/cos encoding for periodic features
add_season             : meteorological season label
"""

from __future__ import annotations

import logging
from typing import Final

import numpy as np
import pandas as pd

logger: Final = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_HOUR_PERIOD: Final[float] = 24.0
_MONTH_PERIOD: Final[float] = 12.0
_DOY_PERIOD: Final[float] = 365.25

_SEASON_MAP: Final[dict[int, str]] = {
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "autumn",
    10: "autumn",
    11: "autumn",
    12: "winter",
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def _ensure_datetime_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    """Return the DatetimeIndex of *df*, raising if it is not datetime-typed.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame whose index should be a ``DatetimeIndex``.

    Returns
    -------
    pd.DatetimeIndex

    Raises
    ------
    TypeError
        If the index is not a ``DatetimeIndex``.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError(
            f"DataFrame index must be a DatetimeIndex, got {type(df.index).__name__}."
        )
    return df.index


# ---------------------------------------------------------------------------
# Feature functions
# ---------------------------------------------------------------------------

def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract basic calendar features from the datetime index.

    Creates the following columns:

    * **hour** – hour of day (0–23)
    * **day_of_week** – ISO day of the week (0 = Monday … 6 = Sunday)
    * **day_of_year** – ordinal day within the year (1–366)
    * **month** – month number (1–12)
    * **is_weekend** – boolean flag (``True`` for Saturday / Sunday)

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame with a ``DatetimeIndex``.

    Returns
    -------
    pd.DataFrame
        A copy of *df* with the new columns appended.
    """
    idx = _ensure_datetime_index(df)
    df = df.copy()

    df["hour"] = idx.hour
    df["day_of_week"] = idx.dayofweek  # 0=Mon … 6=Sun
    df["day_of_year"] = idx.dayofyear
    df["month"] = idx.month
    df["is_weekend"] = idx.dayofweek >= 5

    logger.info(
        "Added time features: hour, day_of_week, day_of_year, month, is_weekend "
        "(%d rows).",
        len(df),
    )
    return df


def add_cyclical_encoding(df: pd.DataFrame) -> pd.DataFrame:
    """Encode periodic time features with sin / cos pairs.

    Assumes that :func:`add_time_features` has already been called so that
    ``hour``, ``month``, and ``day_of_year`` columns exist.

    Created columns:

    * ``hour_sin``, ``hour_cos`` — period 24
    * ``month_sin``, ``month_cos`` — period 12
    * ``day_of_year_sin``, ``day_of_year_cos`` — period 365.25

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing ``hour``, ``month``, and ``day_of_year`` columns.

    Returns
    -------
    pd.DataFrame
        A copy of *df* with the six new cyclical columns appended.

    Raises
    ------
    KeyError
        If any prerequisite column is missing.
    """
    required = {"hour", "month", "day_of_year"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(
            f"Missing columns for cyclical encoding: {missing}. "
            "Call add_time_features() first."
        )

    df = df.copy()

    for col, period in [
        ("hour", _HOUR_PERIOD),
        ("month", _MONTH_PERIOD),
        ("day_of_year", _DOY_PERIOD),
    ]:
        angle = 2.0 * np.pi * df[col] / period
        df[f"{col}_sin"] = np.sin(angle)
        df[f"{col}_cos"] = np.cos(angle)

    logger.info(
        "Added cyclical encodings for hour (T=%s), month (T=%s), "
        "day_of_year (T=%s).",
        _HOUR_PERIOD,
        _MONTH_PERIOD,
        _DOY_PERIOD,
    )
    return df


def add_season(df: pd.DataFrame) -> pd.DataFrame:
    """Assign a meteorological season label based on month.

    Mapping (Northern Hemisphere):

    * **winter** — Dec, Jan, Feb
    * **spring** — Mar, Apr, May
    * **summer** — Jun, Jul, Aug
    * **autumn** — Sep, Oct, Nov

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing a ``month`` column (1–12).

    Returns
    -------
    pd.DataFrame
        A copy of *df* with a ``season`` column added (categorical dtype).

    Raises
    ------
    KeyError
        If the ``month`` column is absent.
    """
    if "month" not in df.columns:
        raise KeyError("Column 'month' is required. Call add_time_features() first.")

    df = df.copy()
    df["season"] = (
        df["month"]
        .map(_SEASON_MAP)
        .astype(pd.CategoricalDtype(categories=["spring", "summer", "autumn", "winter"]))
    )

    logger.info("Added season column — distribution:\n%s", df["season"].value_counts().to_string())
    return df
