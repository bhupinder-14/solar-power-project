"""
Chronological train/validation/test splitting for time-series data.

Provides functions to split, save, and load time-series datasets
while preserving temporal ordering to prevent future-data leakage.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def chronological_split(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split a time-series DataFrame chronologically into train/val/test sets.

    The DataFrame is sorted by its DatetimeIndex and divided into
    contiguous blocks — no shuffling — so that the model never sees
    future data during training.

    Args:
        df: Input DataFrame with a DatetimeIndex.
        train_ratio: Fraction of data for training (default 0.70).
        val_ratio: Fraction of data for validation (default 0.15).
        test_ratio: Fraction of data for testing (default 0.15).

    Returns:
        A tuple of (train_df, val_df, test_df).

    Raises:
        ValueError: If ratios do not sum to 1.0 (±1e-6) or if any ratio
            is non-positive.
        TypeError: If the DataFrame index is not a DatetimeIndex.
    """
    # --- validate ratios ---------------------------------------------------
    ratio_sum = train_ratio + val_ratio + test_ratio
    if abs(ratio_sum - 1.0) > 1e-6:
        raise ValueError(
            f"Ratios must sum to 1.0, got {ratio_sum:.6f} "
            f"(train={train_ratio}, val={val_ratio}, test={test_ratio})."
        )
    for name, ratio in [("train", train_ratio), ("val", val_ratio), ("test", test_ratio)]:
        if ratio <= 0:
            raise ValueError(f"{name}_ratio must be positive, got {ratio}.")

    # --- validate index ----------------------------------------------------
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError(
            f"DataFrame index must be a DatetimeIndex, got {type(df.index).__name__}."
        )

    # --- sort by time ------------------------------------------------------
    df_sorted = df.sort_index()
    n = len(df_sorted)
    logger.info("Total samples: %d", n)

    # --- compute split boundaries ------------------------------------------
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)

    train_df = df_sorted.iloc[:train_end].copy()
    val_df = df_sorted.iloc[train_end:val_end].copy()
    test_df = df_sorted.iloc[val_end:].copy()

    # --- logging -----------------------------------------------------------
    for split_name, split_df in [("Train", train_df), ("Val", val_df), ("Test", test_df)]:
        logger.info(
            "%s — %d rows | %s → %s",
            split_name,
            len(split_df),
            split_df.index.min(),
            split_df.index.max(),
        )

    return train_df, val_df, test_df


def save_splits(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Persist train/val/test DataFrames to CSV files.

    Files are saved as ``train.csv``, ``val.csv``, and ``test.csv``
    inside *output_dir*.  The directory is created if it does not exist.

    Args:
        train: Training DataFrame.
        val: Validation DataFrame.
        test: Test DataFrame.
        output_dir: Directory to write the CSV files into.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, split_df in [("train", train), ("val", val), ("test", test)]:
        path = output_dir / f"{name}.csv"
        split_df.to_csv(path)
        logger.info("Saved %s split (%d rows) → %s", name, len(split_df), path)


def load_splits(
    splits_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load previously saved train/val/test CSV splits.

    Expects ``train.csv``, ``val.csv``, and ``test.csv`` in *splits_dir*.
    The first column is parsed as a DatetimeIndex.

    Args:
        splits_dir: Directory containing the three CSV files.

    Returns:
        A tuple of (train_df, val_df, test_df).

    Raises:
        FileNotFoundError: If any of the expected CSV files is missing.
    """
    splits_dir = Path(splits_dir)
    dfs: list[pd.DataFrame] = []

    for name in ("train", "val", "test"):
        path = splits_dir / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Expected split file not found: {path}")
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        logger.info("Loaded %s split (%d rows) from %s", name, len(df), path)
        dfs.append(df)

    return dfs[0], dfs[1], dfs[2]
