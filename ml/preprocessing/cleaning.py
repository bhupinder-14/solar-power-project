"""
ml.preprocessing.cleaning
=========================

Data-cleaning utilities for the *Renewable Power Generation and Weather
Conditions* dataset.  Every public function returns a **new** DataFrame
(no in-place mutation) and logs what it changed.

Typical usage
-------------
>>> from ml.preprocessing.cleaning import clean_dataset
>>> df_clean, report = clean_dataset(df)
"""

from __future__ import annotations

import logging
from typing import Any, Final

import numpy as np
import pandas as pd

logger: logging.Logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — plausible physical ranges (used for clipping)
# ---------------------------------------------------------------------------

_CLIP_RULES: Final[dict[str, dict[str, float]]] = {
    "energy_delta_wh": {"min": 0.0},
    "energy_delta": {"min": 0.0},
    "ghi": {"min": 0.0, "max": 1400.0},
    "temperature": {"min": -50.0, "max": 70.0},
    "temp": {"min": -50.0, "max": 70.0},
    "humidity": {"min": 0.0, "max": 100.0},
}
"""Column-name substring → clip bounds.  Matched via *substring* of the
lowered column name so that ``ghi_w_m2`` still matches ``ghi``."""

_DEFAULT_MISSING_STRATEGY: Final[dict[str, str]] = {
    "ghi": "interpolate",
    "temperature": "interpolate",
    "temp": "interpolate",
    "humidity": "interpolate",
    "precipitation": "ffill",
    "daylength": "ffill",
    "day_length": "ffill",
    "sunlighttime": "ffill",
    "sunlight_time": "ffill",
    "energy_delta_wh": "interpolate",
    "energy_delta": "interpolate",
}
"""Fallback per-column missing-value strategy when none is supplied."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def remove_duplicate_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with duplicate timestamps, keeping the first occurrence.

    Both *exact* duplicates (all columns identical) and *near-duplicates*
    (same timestamp, different values) are handled — in each case the first
    row is retained.

    Parameters
    ----------
    df:
        DataFrame with a ``DatetimeIndex``.

    Returns
    -------
    pd.DataFrame
        De-duplicated DataFrame.
    """
    n_before: int = len(df)

    # Exact duplicates (all columns + index)
    exact_dups: int = int(df.duplicated(keep="first").sum())

    # Index-level duplicates (same timestamp regardless of values)
    idx_dups: int = int(df.index.duplicated(keep="first").sum())

    df = df[~df.index.duplicated(keep="first")].copy()

    n_removed: int = n_before - len(df)
    logger.info(
        "Duplicate removal: %d exact dupes, %d index dupes → removed %d row(s).",
        exact_dups,
        idx_dups,
        n_removed,
    )
    return df


def handle_missing_values(
    df: pd.DataFrame,
    strategy: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Fill or interpolate missing values according to a per-column strategy.

    Supported strategy values
    -------------------------
    - ``'ffill'``       — forward fill.
    - ``'bfill'``       — backward fill.
    - ``'interpolate'`` — linear interpolation (time-aware when possible).
    - ``'zero'``        — fill with 0.
    - ``'mean'``        — fill with column mean.
    - ``'median'``      — fill with column median.
    - ``'drop'``        — drop rows with NaN in that column.

    Columns not mentioned in *strategy* are left unchanged unless a matching
    key exists in :data:`_DEFAULT_MISSING_STRATEGY`.

    Parameters
    ----------
    df:
        Input DataFrame (not modified in-place).
    strategy:
        Mapping of column name (or column-name substring) → strategy string.
        ``None`` falls back to :data:`_DEFAULT_MISSING_STRATEGY`.

    Returns
    -------
    pd.DataFrame
        DataFrame with missing values handled.
    """
    df = df.copy()
    effective: dict[str, str] = dict(_DEFAULT_MISSING_STRATEGY)
    if strategy is not None:
        effective.update(strategy)

    total_filled: int = 0

    for col in df.columns:
        n_missing: int = int(df[col].isna().sum())
        if n_missing == 0:
            continue

        # Resolve strategy for this column
        strat: str | None = effective.get(col)
        if strat is None:
            # Try substring match
            col_lower: str = col.lower()
            for key, val in effective.items():
                if key in col_lower:
                    strat = val
                    break

        if strat is None:
            # Ultimate fallback for numeric columns
            if pd.api.types.is_numeric_dtype(df[col]):
                strat = "interpolate"
            else:
                strat = "ffill"

        before_na: int = n_missing

        if strat == "ffill":
            df[col] = df[col].ffill()
        elif strat == "bfill":
            df[col] = df[col].bfill()
        elif strat == "interpolate":
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].interpolate(method="time")
            else:
                df[col] = df[col].ffill()
        elif strat == "zero":
            df[col] = df[col].fillna(0)
        elif strat == "mean":
            df[col] = df[col].fillna(df[col].mean())
        elif strat == "median":
            df[col] = df[col].fillna(df[col].median())
        elif strat == "drop":
            df = df.dropna(subset=[col])
        else:
            logger.warning(
                "Unknown strategy '%s' for column '%s'; skipping.", strat, col
            )
            continue

        # Back-fill any remaining leading NaNs (e.g. if ffill left them)
        remaining: int = int(df[col].isna().sum())
        if remaining and strat in ("ffill", "interpolate"):
            df[col] = df[col].bfill()
            remaining = int(df[col].isna().sum())

        filled: int = before_na - remaining
        total_filled += filled
        logger.debug(
            "Column '%s': strategy='%s', filled %d/%d missing.", col, strat, filled, before_na
        )

    logger.info("Missing-value handling: filled %d value(s) total.", total_filled)
    return df


def clip_implausible_values(df: pd.DataFrame) -> pd.DataFrame:
    """Clip numeric columns to physically plausible ranges.

    Uses :data:`_CLIP_RULES`.  A column is matched when a rule key is a
    substring of the lowered column name.

    Parameters
    ----------
    df:
        Input DataFrame.

    Returns
    -------
    pd.DataFrame
        DataFrame with clipped values.
    """
    df = df.copy()
    total_clipped: int = 0

    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue

        col_lower: str = col.lower()
        for rule_key, bounds in _CLIP_RULES.items():
            if rule_key not in col_lower:
                continue

            lo: float | None = bounds.get("min")
            hi: float | None = bounds.get("max")

            out_of_range: int = 0
            if lo is not None:
                out_of_range += int((df[col] < lo).sum())
            if hi is not None:
                out_of_range += int((df[col] > hi).sum())

            if out_of_range:
                df[col] = df[col].clip(lower=lo, upper=hi)
                total_clipped += out_of_range
                logger.info(
                    "Clipped %d value(s) in '%s' to [%s, %s].",
                    out_of_range,
                    col,
                    lo,
                    hi,
                )

            break  # first matching rule only

    if total_clipped == 0:
        logger.info("Clipping: no implausible values found.")
    else:
        logger.info("Clipping: %d value(s) clipped in total.", total_clipped)

    return df


def detect_outliers_iqr(
    df: pd.DataFrame,
    columns: list[str],
    k: float = 3.0,
) -> pd.DataFrame:
    """Flag outliers using the IQR method.

    For each column in *columns* the inter-quartile range (IQR) is computed and
    values outside ``[Q1 - k*IQR, Q3 + k*IQR]`` are flagged.

    Parameters
    ----------
    df:
        Input DataFrame.
    columns:
        Numeric columns to check.
    k:
        IQR multiplier (default ``3.0`` — intentionally wide to avoid
        false positives).

    Returns
    -------
    pd.DataFrame
        A Boolean DataFrame of the same shape as ``df[columns]`` where
        ``True`` indicates an outlier.
    """
    outlier_flags: pd.DataFrame = pd.DataFrame(
        False, index=df.index, columns=columns
    )

    for col in columns:
        if col not in df.columns:
            logger.warning("Outlier detection: column '%s' not found; skipping.", col)
            continue

        if not pd.api.types.is_numeric_dtype(df[col]):
            logger.warning(
                "Outlier detection: column '%s' is not numeric; skipping.", col
            )
            continue

        q1: float = float(df[col].quantile(0.25))
        q3: float = float(df[col].quantile(0.75))
        iqr: float = q3 - q1
        lower: float = q1 - k * iqr
        upper: float = q3 + k * iqr

        mask: pd.Series = (df[col] < lower) | (df[col] > upper)
        outlier_flags[col] = mask
        n_outliers: int = int(mask.sum())

        if n_outliers:
            logger.info(
                "Outliers in '%s': %d flagged  (IQR=%.2f, bounds=[%.2f, %.2f], k=%.1f).",
                col,
                n_outliers,
                iqr,
                lower,
                upper,
                k,
            )

    total: int = int(outlier_flags.sum().sum())
    logger.info("IQR outlier detection complete: %d total flags.", total)
    return outlier_flags


def enforce_nighttime_zero_generation(
    df: pd.DataFrame,
    ghi_col: str = "ghi",
) -> pd.DataFrame:
    """Set energy generation to zero when GHI is zero (nighttime).

    Solar panels cannot produce energy without sunlight.  When *ghi_col*
    equals zero the energy-generation column(s) are forced to zero.

    Parameters
    ----------
    df:
        Input DataFrame.
    ghi_col:
        Name of the GHI column.

    Returns
    -------
    pd.DataFrame
        Adjusted DataFrame.
    """
    df = df.copy()

    if ghi_col not in df.columns:
        logger.warning(
            "GHI column '%s' not found; skipping nighttime enforcement.", ghi_col
        )
        return df

    night_mask: pd.Series = df[ghi_col] == 0

    energy_cols: list[str] = [
        c
        for c in df.columns
        if "energy" in c.lower() or "delta" in c.lower() or "generation" in c.lower()
    ]

    total_zeroed: int = 0
    for col in energy_cols:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        non_zero_at_night: int = int((night_mask & (df[col] != 0)).sum())
        if non_zero_at_night:
            df.loc[night_mask, col] = 0.0
            total_zeroed += non_zero_at_night
            logger.info(
                "Nighttime enforcement: zeroed %d non-zero value(s) in '%s'.",
                non_zero_at_night,
                col,
            )

    if total_zeroed == 0:
        logger.info("Nighttime enforcement: no corrections needed.")

    return df


# ---------------------------------------------------------------------------
# Full cleaning pipeline
# ---------------------------------------------------------------------------


def clean_dataset(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run the complete cleaning pipeline.

    Steps executed in order:

    1. Remove duplicate timestamps.
    2. Handle missing values (default strategies).
    3. Clip implausible values.
    4. Enforce nighttime zero generation.

    Outlier detection is **not** applied automatically — call
    :func:`detect_outliers_iqr` separately if you want outlier flags.

    Parameters
    ----------
    df:
        Input DataFrame (expected to have a ``DatetimeIndex`` and
        standardised column names).

    Returns
    -------
    tuple[pd.DataFrame, dict]
        ``(cleaned_df, report)`` where *report* summarises what was done.
    """
    logger.info("=== Cleaning pipeline START ===")
    report: dict[str, Any] = {"rows_before": len(df)}

    # 1. Duplicates
    df = remove_duplicate_timestamps(df)
    report["rows_after_dedup"] = len(df)
    report["duplicates_removed"] = report["rows_before"] - report["rows_after_dedup"]

    # 2. Missing values
    missing_before: int = int(df.isna().sum().sum())
    df = handle_missing_values(df)
    missing_after: int = int(df.isna().sum().sum())
    report["missing_filled"] = missing_before - missing_after
    report["missing_remaining"] = missing_after

    # 3. Clipping
    df = clip_implausible_values(df)

    # 4. Nighttime enforcement
    df = enforce_nighttime_zero_generation(df)

    report["rows_after"] = len(df)
    report["columns"] = list(df.columns)

    logger.info(
        "=== Cleaning pipeline DONE  ===  %d → %d rows, %d missing filled, "
        "%d still missing.",
        report["rows_before"],
        report["rows_after"],
        report["missing_filled"],
        report["missing_remaining"],
    )

    return df, report
