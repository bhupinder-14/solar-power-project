"""
ml.preprocessing.validation
============================

Data-quality validation for the *Renewable Power Generation and Weather
Conditions* dataset.  Every function is pure (no side-effects on the input
DataFrame) and logs its findings.

Typical usage
-------------
>>> from ml.preprocessing.validation import generate_validation_report
>>> report = generate_validation_report(df)
"""

from __future__ import annotations

import logging
from typing import Any, Final

import numpy as np
import pandas as pd

logger: logging.Logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — physically plausible ranges
# ---------------------------------------------------------------------------

_RANGE_RULES: Final[dict[str, dict[str, float]]] = {
    "energy_delta_wh": {"min": 0.0, "max": float("inf")},
    "energy_delta": {"min": 0.0, "max": float("inf")},
    "ghi": {"min": 0.0, "max": 1400.0},
    "temperature": {"min": -50.0, "max": 70.0},
    "temp": {"min": -50.0, "max": 70.0},
    "humidity": {"min": 0.0, "max": 100.0},
}
"""Column-name → {min, max} look-up used by :func:`validate_value_ranges`.

Keys are checked via *substring* matching against the lowered column names so
that small naming variations (e.g. ``temperature_c``, ``humidity_%``) are
caught automatically.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_required_columns(
    df: pd.DataFrame,
    required: list[str],
) -> tuple[bool, list[str]]:
    """Check that every column in *required* is present in *df*.

    Parameters
    ----------
    df:
        DataFrame to inspect.
    required:
        List of column names that must exist.

    Returns
    -------
    tuple[bool, list[str]]
        ``(all_present, missing_columns)`` — *all_present* is ``True`` when
        nothing is missing.
    """
    existing: set[str] = set(df.columns)
    missing: list[str] = [c for c in required if c not in existing]

    if missing:
        logger.warning("Missing required columns: %s", missing)
    else:
        logger.info("All %d required columns present.", len(required))

    return len(missing) == 0, missing


def validate_dtypes(
    df: pd.DataFrame,
    expected_numeric: list[str],
) -> dict[str, str]:
    """Check that *expected_numeric* columns are numeric.

    Parameters
    ----------
    df:
        DataFrame to inspect.
    expected_numeric:
        Columns expected to have a numeric dtype.

    Returns
    -------
    dict[str, str]
        Mapping of column name → actual dtype string for **non-numeric**
        columns only.  An empty dict means everything looks correct.
    """
    issues: dict[str, str] = {}

    for col in expected_numeric:
        if col not in df.columns:
            issues[col] = "COLUMN_MISSING"
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            issues[col] = str(df[col].dtype)

    if issues:
        logger.warning("Dtype issues detected: %s", issues)
    else:
        logger.info(
            "All %d expected-numeric columns have numeric dtypes.",
            len(expected_numeric),
        )

    return issues


def validate_value_ranges(df: pd.DataFrame) -> pd.DataFrame:
    """Flag rows containing physically impossible values.

    Uses :data:`_RANGE_RULES` for the ranges.  A column is matched by checking
    whether any rule-key is a *substring* of the column name, so ``ghi`` will
    match ``ghi_w_m2`` etc.

    Parameters
    ----------
    df:
        DataFrame to inspect.

    Returns
    -------
    pd.DataFrame
        A DataFrame with columns ``['column', 'index', 'value', 'reason']``
        listing every flagged observation.  Empty if nothing is flagged.
    """
    records: list[dict[str, Any]] = []

    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue

        col_lower: str = col.lower()

        for rule_key, bounds in _RANGE_RULES.items():
            if rule_key not in col_lower:
                continue

            lo: float = bounds["min"]
            hi: float = bounds["max"]

            below = df[col] < lo
            above = df[col] > hi

            if below.any():
                bad_idx = df.index[below]
                for idx in bad_idx:
                    records.append(
                        {
                            "column": col,
                            "index": idx,
                            "value": df.at[idx, col],
                            "reason": f"Below minimum ({lo})",
                        }
                    )

            if above.any():
                bad_idx = df.index[above]
                for idx in bad_idx:
                    records.append(
                        {
                            "column": col,
                            "index": idx,
                            "value": df.at[idx, col],
                            "reason": f"Above maximum ({hi})",
                        }
                    )

            # Only first matching rule per column
            break

    flagged: pd.DataFrame = pd.DataFrame(
        records, columns=["column", "index", "value", "reason"]
    )

    if len(flagged):
        logger.warning(
            "Value-range validation flagged %d observations across %d column(s).",
            len(flagged),
            flagged["column"].nunique(),
        )
    else:
        logger.info("Value-range validation: no implausible values found.")

    return flagged


def validate_timestamp_continuity(
    df: pd.DataFrame,
    expected_freq: str = "15min",
) -> dict[str, Any]:
    """Check for gaps or irregularities in the time-series index.

    Parameters
    ----------
    df:
        DataFrame with a ``DatetimeIndex``.
    expected_freq:
        Expected constant frequency as a pandas offset alias
        (default ``'15min'``).

    Returns
    -------
    dict
        Keys:

        - ``expected_freq`` — the expected frequency string.
        - ``inferred_freq`` — pandas' inferred frequency (may be ``None``).
        - ``n_gaps`` — number of missing intervals detected.
        - ``total_missing_intervals`` — total count of absent time steps.
        - ``gaps`` — list of ``(start, end, missing_count)`` tuples.
        - ``duplicates`` — number of duplicate index values.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        logger.error(
            "validate_timestamp_continuity expects a DatetimeIndex; "
            "got %s",
            type(df.index).__name__,
        )
        return {
            "expected_freq": expected_freq,
            "inferred_freq": None,
            "n_gaps": -1,
            "total_missing_intervals": -1,
            "gaps": [],
            "duplicates": -1,
        }

    freq: pd.DateOffset = pd.tseries.frequencies.to_offset(expected_freq)
    expected_td: pd.Timedelta = pd.Timedelta(freq.nanos, unit="ns")

    inferred: str | None = pd.infer_freq(df.index)
    n_duplicates: int = int(df.index.duplicated().sum())

    # Compute the actual deltas
    deltas: pd.TimedeltaIndex = df.index.to_series().diff().dropna().index  # type: ignore[assignment]
    diffs: pd.Series = df.index.to_series().diff().dropna()

    gap_mask: pd.Series = diffs > expected_td
    gap_starts: pd.DatetimeIndex = diffs[gap_mask].index  # type: ignore[assignment]

    gaps: list[dict[str, Any]] = []
    total_missing: int = 0

    for ts in gap_starts:
        loc: int = df.index.get_loc(ts)
        prev_ts: pd.Timestamp = df.index[loc - 1]  # type: ignore[index]
        delta: pd.Timedelta = ts - prev_ts  # type: ignore[operator]
        n_missing: int = int(delta / expected_td) - 1
        total_missing += n_missing
        gaps.append(
            {"start": prev_ts, "end": ts, "missing_intervals": n_missing}
        )

    if gaps:
        logger.warning(
            "Found %d gap(s) totalling %d missing intervals (freq=%s).",
            len(gaps),
            total_missing,
            expected_freq,
        )
    else:
        logger.info("No gaps detected at freq=%s.", expected_freq)

    if n_duplicates:
        logger.warning("%d duplicate timestamp(s) found.", n_duplicates)

    return {
        "expected_freq": expected_freq,
        "inferred_freq": inferred,
        "n_gaps": len(gaps),
        "total_missing_intervals": total_missing,
        "gaps": gaps,
        "duplicates": n_duplicates,
    }


def generate_validation_report(df: pd.DataFrame) -> dict[str, Any]:
    """Run all validations and return a single comprehensive report.

    Parameters
    ----------
    df:
        DataFrame to validate (should have a ``DatetimeIndex`` and
        standardised column names).

    Returns
    -------
    dict
        Top-level keys:

        - ``shape`` — ``(rows, cols)``.
        - ``columns`` — list of column names.
        - ``dtypes`` — column → dtype mapping.
        - ``missing_values`` — column → count of NaN/None.
        - ``missing_pct`` — column → percentage of NaN/None.
        - ``dtype_issues`` — output of :func:`validate_dtypes`.
        - ``value_range_flags`` — output of :func:`validate_value_ranges`.
        - ``timestamp_continuity`` — output of :func:`validate_timestamp_continuity`.
        - ``duplicate_rows`` — number of fully duplicated rows.
        - ``index_type`` — string name of the index type.
    """
    logger.info("=== Generating validation report ===")

    # Guess which columns should be numeric
    # (everything except obvious object/category columns)
    expected_numeric: list[str] = [
        c
        for c in df.columns
        if df[c].dtype.kind in ("f", "i", "u")  # already numeric
        or c
        in (
            "energy_delta_wh",
            "energy_delta",
            "ghi",
            "temperature",
            "temp",
            "humidity",
            "precipitation",
            "daylength",
            "sunlighttime",
            "sunlight_time",
            "day_length",
        )
    ]

    missing_counts: pd.Series = df.isna().sum()
    missing_pct: pd.Series = (missing_counts / len(df) * 100).round(2)

    dtype_issues: dict[str, str] = validate_dtypes(df, expected_numeric)
    flagged: pd.DataFrame = validate_value_ranges(df)
    continuity: dict[str, Any] = validate_timestamp_continuity(df)

    report: dict[str, Any] = {
        "shape": df.shape,
        "columns": list(df.columns),
        "dtypes": {c: str(d) for c, d in df.dtypes.items()},
        "missing_values": missing_counts[missing_counts > 0].to_dict(),
        "missing_pct": missing_pct[missing_pct > 0].to_dict(),
        "dtype_issues": dtype_issues,
        "value_range_flags_count": len(flagged),
        "value_range_flags": flagged,
        "timestamp_continuity": continuity,
        "duplicate_rows": int(df.duplicated().sum()),
        "index_type": type(df.index).__name__,
    }

    logger.info(
        "Validation report complete — shape=%s, missing-cols=%d, "
        "range-flags=%d, gaps=%d, dup-rows=%d",
        report["shape"],
        len(report["missing_values"]),
        report["value_range_flags_count"],
        continuity.get("n_gaps", -1),
        report["duplicate_rows"],
    )

    return report
