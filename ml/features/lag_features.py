"""
SolarCast AI — Lag & Rolling Feature Engineering.

Provides functions that create lagged and rolling-window features for the
target variable and weather columns.

**Leakage-Prevention Strategy**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Every function in this module relies exclusively on *past* information.

* **Lag features** use ``pd.Series.shift(lag)`` with ``lag ≥ 1``, which
  moves each value forward in time so that row *t* only sees values from
  row *t − lag* or earlier.
* **Rolling features** apply ``.shift(1)`` *before* ``.rolling()`` so
  that the rolling window never includes the current row's value.
* The caller is responsible for sorting the DataFrame chronologically
  **before** calling these functions.  Functions verify monotonic order
  and raise if the index is not sorted.

Functions
---------
add_lag_features          : lagged copies of the target column
add_rolling_features      : rolling mean / std of the target column
add_weather_lag_features  : lagged copies of weather columns
drop_leakage_unsafe_rows  : remove leading NaN rows created by lagging
"""

from __future__ import annotations

import logging
from typing import Final

import pandas as pd

logger: Final = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
_DEFAULT_TARGET_LAGS: Final[list[int]] = [1, 2, 3, 4, 96, 672]
"""Default lag steps (15-min cadence):
1–4  → previous 15 min to 1 h
96   → same time yesterday (24 h × 4)
672  → same time last week  (7 d × 96)
"""

_DEFAULT_ROLLING_WINDOWS: Final[list[int]] = [4, 8, 96]
"""Default rolling-window sizes (15-min cadence):
4   → 1 h
8   → 2 h
96  → 24 h
"""

_DEFAULT_WEATHER_LAGS: Final[list[int]] = [1, 4, 96]
"""Default weather lags (15-min cadence):
1  → previous 15 min
4  → previous 1 h
96 → same time yesterday
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _assert_sorted(df: pd.DataFrame) -> None:
    """Raise ``ValueError`` if the index is not monotonically increasing."""
    if not df.index.is_monotonic_increasing:
        raise ValueError(
            "DataFrame index must be sorted in ascending chronological order "
            "before computing lag / rolling features."
        )


def _assert_column_exists(df: pd.DataFrame, col: str) -> None:
    """Raise ``KeyError`` if *col* is not in *df*."""
    if col not in df.columns:
        raise KeyError(f"Column '{col}' not found in DataFrame.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_lag_features(
    df: pd.DataFrame,
    target_col: str,
    lags: list[int] | None = None,
) -> pd.DataFrame:
    """Create lagged copies of the target column.

    **Leakage prevention:** Uses ``pd.Series.shift(lag)`` with ``lag ≥ 1``,
    which guarantees that row *t* only accesses values from row *t − lag*
    (strictly in the past).

    Parameters
    ----------
    df : pd.DataFrame
        Chronologically sorted DataFrame.
    target_col : str
        Name of the target column to lag.
    lags : list[int] | None
        Positive integers specifying how many rows to shift.  Defaults to
        ``[1, 2, 3, 4, 96, 672]`` (15-min resolution).

    Returns
    -------
    pd.DataFrame
        A copy of *df* with ``{target_col}_lag_{lag}`` columns appended.

    Raises
    ------
    ValueError
        If the index is not sorted or any lag value is ≤ 0.
    KeyError
        If *target_col* is missing.
    """
    _assert_sorted(df)
    _assert_column_exists(df, target_col)

    if lags is None:
        lags = _DEFAULT_TARGET_LAGS

    if any(lag <= 0 for lag in lags):
        raise ValueError("All lag values must be > 0 to avoid future-data leakage.")

    df = df.copy()
    for lag in lags:
        col_name = f"{target_col}_lag_{lag}"
        df[col_name] = df[target_col].shift(lag)
        logger.debug("Created lag feature '%s' (shift=%d).", col_name, lag)

    logger.info(
        "Added %d lag features for '%s': %s.",
        len(lags),
        target_col,
        lags,
    )
    return df


def add_rolling_features(
    df: pd.DataFrame,
    target_col: str,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """Compute rolling mean and standard deviation of the target column.

    **Leakage prevention:** The series is shifted by 1 step *before* the
    rolling window is applied (``df[target_col].shift(1).rolling(...)``).
    This ensures the current row's own value is never included in the
    window — only strictly past values contribute.

    ``min_periods=1`` is used to avoid excessive ``NaN`` values at the
    beginning of the series.

    Parameters
    ----------
    df : pd.DataFrame
        Chronologically sorted DataFrame.
    target_col : str
        Name of the target column.
    windows : list[int] | None
        Window sizes (in number of rows).  Defaults to
        ``[4, 8, 96]`` (1 h, 2 h, 24 h at 15-min resolution).

    Returns
    -------
    pd.DataFrame
        A copy of *df* with ``{target_col}_rolling_mean_{w}`` and
        ``{target_col}_rolling_std_{w}`` columns appended for each window *w*.

    Raises
    ------
    ValueError
        If the index is not sorted or any window is ≤ 0.
    KeyError
        If *target_col* is missing.
    """
    _assert_sorted(df)
    _assert_column_exists(df, target_col)

    if windows is None:
        windows = _DEFAULT_ROLLING_WINDOWS

    if any(w <= 0 for w in windows):
        raise ValueError("All window sizes must be > 0.")

    df = df.copy()
    # Shift FIRST to exclude the current row — critical for leakage prevention.
    shifted = df[target_col].shift(1)

    for w in windows:
        rolling = shifted.rolling(window=w, min_periods=1)

        mean_col = f"{target_col}_rolling_mean_{w}"
        std_col = f"{target_col}_rolling_std_{w}"

        df[mean_col] = rolling.mean()
        df[std_col] = rolling.std()

        logger.debug(
            "Created rolling features '%s', '%s' (window=%d, shift=1).",
            mean_col,
            std_col,
            w,
        )

    logger.info(
        "Added rolling features for '%s' with windows %s (shift(1) applied first).",
        target_col,
        windows,
    )
    return df


def add_weather_lag_features(
    df: pd.DataFrame,
    weather_cols: list[str],
    lags: list[int] | None = None,
) -> pd.DataFrame:
    """Create lagged versions of weather columns.

    **Leakage prevention:** Identical strategy to :func:`add_lag_features` —
    ``pd.Series.shift(lag)`` with ``lag ≥ 1`` ensures only past values are
    used.

    Parameters
    ----------
    df : pd.DataFrame
        Chronologically sorted DataFrame.
    weather_cols : list[str]
        Weather column names to lag.
    lags : list[int] | None
        Positive integers specifying shift amounts.  Defaults to
        ``[1, 4, 96]``.

    Returns
    -------
    pd.DataFrame
        A copy of *df* with ``{col}_lag_{lag}`` columns for each
        weather column and lag combination.

    Raises
    ------
    ValueError
        If the index is not sorted or any lag ≤ 0.
    KeyError
        If any column in *weather_cols* is missing.
    """
    _assert_sorted(df)

    if lags is None:
        lags = _DEFAULT_WEATHER_LAGS

    if any(lag <= 0 for lag in lags):
        raise ValueError("All lag values must be > 0 to avoid future-data leakage.")

    missing_cols = set(weather_cols) - set(df.columns)
    if missing_cols:
        raise KeyError(f"Weather columns not found in DataFrame: {missing_cols}")

    df = df.copy()
    created: list[str] = []
    for col in weather_cols:
        for lag in lags:
            new_col = f"{col}_lag_{lag}"
            df[new_col] = df[col].shift(lag)
            created.append(new_col)

    logger.info(
        "Added %d weather lag features for columns %s with lags %s.",
        len(created),
        weather_cols,
        lags,
    )
    return df


def drop_leakage_unsafe_rows(
    df: pd.DataFrame,
    max_lag: int,
) -> pd.DataFrame:
    """Drop the first *max_lag* rows where lag features contain ``NaN``.

    After creating lag and rolling features the first rows of the
    DataFrame inevitably contain ``NaN`` values because there is no prior
    history to draw from.  Keeping these rows during training would force
    the model to learn from incomplete feature vectors.  This helper
    removes them cleanly.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with lag / rolling features.
    max_lag : int
        Number of leading rows to drop (should equal the largest lag used).

    Returns
    -------
    pd.DataFrame
        A copy of *df* with the first *max_lag* rows removed.

    Raises
    ------
    ValueError
        If *max_lag* is negative or exceeds the number of rows.
    """
    n_rows = len(df)

    if max_lag < 0:
        raise ValueError(f"max_lag must be ≥ 0, got {max_lag}.")
    if max_lag >= n_rows:
        raise ValueError(
            f"max_lag ({max_lag}) must be less than the number of rows ({n_rows})."
        )

    df_clean = df.iloc[max_lag:].copy()
    dropped = n_rows - len(df_clean)

    logger.info(
        "Dropped %d leading rows (max_lag=%d). Remaining rows: %d.",
        dropped,
        max_lag,
        len(df_clean),
    )
    return df_clean
