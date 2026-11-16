"""
ml.preprocessing.ingestion
==========================

Loads raw CSV data from the *Renewable Power Generation and Weather Conditions*
Kaggle dataset, auto-detects encoding, identifies the datetime column,
parses timestamps and standardises column names.

Typical usage
-------------
>>> from pathlib import Path
>>> from ml.preprocessing.ingestion import load_and_prepare
>>> df = load_and_prepare(Path("ml/data/raw/Renewable.csv"))
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Final

import chardet
import pandas as pd

logger: logging.Logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DATETIME_HINTS: Final[list[str]] = [
    "datetime",
    "timestamp",
    "date_time",
    "date",
    "time",
    "period",
    "interval",
]
"""Sub-strings that commonly appear in datetime column names (lowercase)."""

_MAX_ENCODING_SAMPLE_BYTES: Final[int] = 500_000
"""Number of leading bytes used for charset detection."""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def load_raw_data(filepath: Path) -> pd.DataFrame:
    """Load a CSV file, auto-detecting encoding when the default UTF-8 fails.

    Parameters
    ----------
    filepath:
        Absolute or relative path to the CSV file.

    Returns
    -------
    pd.DataFrame
        Raw data exactly as stored on disk (no transformations).

    Raises
    ------
    FileNotFoundError
        If *filepath* does not exist.
    ValueError
        If the file cannot be decoded with any detected encoding.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")

    # --- Try UTF-8 first (most common) ---
    try:
        df: pd.DataFrame = pd.read_csv(filepath, encoding="utf-8")
        logger.info(
            "Loaded %s with UTF-8 encoding  (%d rows, %d cols)",
            filepath.name,
            len(df),
            len(df.columns),
        )
        return df
    except UnicodeDecodeError:
        logger.debug("UTF-8 failed for %s; attempting charset detection.", filepath.name)

    # --- Fallback: detect encoding via chardet ---
    raw_bytes: bytes = filepath.read_bytes()[:_MAX_ENCODING_SAMPLE_BYTES]
    detection: dict = chardet.detect(raw_bytes)
    detected_encoding: str | None = detection.get("encoding")
    confidence: float = detection.get("confidence", 0.0)

    if detected_encoding is None:
        raise ValueError(
            f"Could not detect encoding for {filepath}. "
            "Please specify encoding manually."
        )

    logger.info(
        "Detected encoding '%s' (confidence %.1f%%) for %s",
        detected_encoding,
        confidence * 100,
        filepath.name,
    )

    try:
        df = pd.read_csv(filepath, encoding=detected_encoding)
        logger.info(
            "Loaded %s with %s encoding  (%d rows, %d cols)",
            filepath.name,
            detected_encoding,
            len(df),
            len(df.columns),
        )
        return df
    except (UnicodeDecodeError, LookupError) as exc:
        raise ValueError(
            f"Failed to read {filepath} with detected encoding "
            f"'{detected_encoding}': {exc}"
        ) from exc


def detect_datetime_column(df: pd.DataFrame) -> str:
    """Heuristically find the column that contains timestamps.

    Strategy
    --------
    1. Check column names against a list of common datetime hints.
    2. Fall back to the first column whose string values successfully parse
       as datetimes.

    Parameters
    ----------
    df:
        DataFrame whose columns are inspected.

    Returns
    -------
    str
        Name of the detected datetime column.

    Raises
    ------
    ValueError
        If no datetime column can be identified.
    """
    lower_cols: dict[str, str] = {c.lower().strip(): c for c in df.columns}

    # 1. Name-based heuristic
    for hint in _DATETIME_HINTS:
        for lower, original in lower_cols.items():
            if hint in lower:
                logger.info("Datetime column detected by name: '%s'", original)
                return original

    # 2. Content-based heuristic — try parsing the first non-null values
    for col in df.columns:
        if df[col].dtype == "object":
            sample: pd.Series = df[col].dropna().head(20)
            if sample.empty:
                continue
            try:
                pd.to_datetime(sample, infer_datetime_format=True)
                logger.info("Datetime column detected by content: '%s'", col)
                return col
            except (ValueError, TypeError):
                continue

    # 3. Already a datetime dtype
    for col in df.select_dtypes(include=["datetime", "datetimetz"]).columns:
        logger.info("Datetime column detected by dtype: '%s'", col)
        return col

    raise ValueError(
        "No datetime column could be identified. "
        f"Columns available: {list(df.columns)}"
    )


def parse_timestamps(
    df: pd.DataFrame,
    datetime_col: str,
) -> pd.DataFrame:
    """Parse *datetime_col* into a ``DatetimeIndex`` and set it as the index.

    Parameters
    ----------
    df:
        Input DataFrame (not modified in-place).
    datetime_col:
        Column name containing date/time strings or objects.

    Returns
    -------
    pd.DataFrame
        A *new* DataFrame with a ``DatetimeIndex`` named ``"timestamp"``,
        sorted chronologically.

    Raises
    ------
    KeyError
        If *datetime_col* is not in *df*.
    ValueError
        If the column cannot be parsed as datetimes.
    """
    if datetime_col not in df.columns:
        raise KeyError(f"Column '{datetime_col}' not found in DataFrame.")

    df = df.copy()

    try:
        df[datetime_col] = pd.to_datetime(df[datetime_col], infer_datetime_format=True)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Could not parse column '{datetime_col}' as datetime: {exc}"
        ) from exc

    df = df.set_index(datetime_col)
    df.index.name = "timestamp"
    df = df.sort_index()

    n_nat: int = int(df.index.isna().sum())
    if n_nat:
        logger.warning(
            "%d NaT values found in timestamp index after parsing.", n_nat
        )

    logger.info(
        "Timestamp index set.  Range: %s  →  %s  (%d rows)",
        df.index.min(),
        df.index.max(),
        len(df),
    )
    return df


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Clean DataFrame column names: lowercase, underscores, no extra spaces.

    Rules applied (in order):
    1. Strip leading/trailing whitespace.
    2. Replace spaces and hyphens with underscores.
    3. Collapse consecutive underscores.
    4. Convert to lowercase.
    5. Strip leading/trailing underscores.

    Parameters
    ----------
    df:
        Input DataFrame (not modified in-place).

    Returns
    -------
    pd.DataFrame
        DataFrame with cleaned column names.
    """
    df = df.copy()
    rename_map: dict[str, str] = {}

    for col in df.columns:
        new: str = col.strip()
        new = re.sub(r"[\s\-]+", "_", new)
        new = re.sub(r"_+", "_", new)
        new = new.lower().strip("_")
        rename_map[col] = new

    df = df.rename(columns=rename_map)

    changed: list[tuple[str, str]] = [
        (old, new) for old, new in rename_map.items() if old != new
    ]
    if changed:
        logger.info(
            "Renamed %d column(s): %s",
            len(changed),
            ", ".join(f"'{o}' → '{n}'" for o, n in changed),
        )
    else:
        logger.debug("No column renames needed.")

    # Also clean the index name if present
    if df.index.name is not None:
        cleaned_idx: str = re.sub(r"[\s\-]+", "_", df.index.name.strip())
        cleaned_idx = re.sub(r"_+", "_", cleaned_idx).lower().strip("_")
        df.index.name = cleaned_idx

    return df


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def load_and_prepare(filepath: Path) -> pd.DataFrame:
    """End-to-end ingestion pipeline.

    Combines :func:`load_raw_data`, :func:`detect_datetime_column`,
    :func:`parse_timestamps`, and :func:`standardize_column_names`
    into a single convenience call.

    Parameters
    ----------
    filepath:
        Path to the raw CSV file.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with a ``DatetimeIndex`` and standardised column
        names, ready for downstream validation and cleaning.
    """
    logger.info("=== Ingestion pipeline START ===")

    df: pd.DataFrame = load_raw_data(filepath)
    dt_col: str = detect_datetime_column(df)
    df = parse_timestamps(df, dt_col)
    df = standardize_column_names(df)

    logger.info(
        "=== Ingestion pipeline DONE  ===  Shape: %s  Columns: %s",
        df.shape,
        list(df.columns),
    )
    return df
