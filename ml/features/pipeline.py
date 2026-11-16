"""
SolarCast AI — Feature Pipeline Assembly.

Orchestrates the full feature-engineering pipeline by composing temporal,
lag/rolling, and weather-derived transformations into a single reproducible
sequence.

Functions
---------
get_feature_columns      : catalogue of feature-column groups
build_feature_pipeline   : train-time pipeline (computes & records metadata)
apply_feature_pipeline   : inference-time pipeline (replays using metadata)
"""

from __future__ import annotations

import logging
from typing import Any, Final

import pandas as pd

from ml.features.lag_features import (
    _DEFAULT_ROLLING_WINDOWS,
    _DEFAULT_TARGET_LAGS,
    _DEFAULT_WEATHER_LAGS,
    add_lag_features,
    add_rolling_features,
    add_weather_lag_features,
    drop_leakage_unsafe_rows,
)
from ml.features.temporal import (
    add_cyclical_encoding,
    add_season,
    add_time_features,
)
from ml.features.weather_features import (
    add_clearness_proxy,
    add_ghi_features,
    add_weather_interactions,
)

logger: Final = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default column lists
# ---------------------------------------------------------------------------
_TEMPORAL_FEATURES: Final[list[str]] = [
    "hour",
    "day_of_week",
    "day_of_year",
    "month",
    "is_weekend",
    "hour_sin",
    "hour_cos",
    "month_sin",
    "month_cos",
    "day_of_year_sin",
    "day_of_year_cos",
    "season",
]

_WEATHER_RAW: Final[list[str]] = [
    "ghi",
    "temperature",
    "humidity",
    "precipitation",
]

_WEATHER_DERIVED: Final[list[str]] = [
    "ghi_ratio",
    "is_daylight",
    "ghi_squared",
    "ghi_temp_interaction",
    "temp_humidity_interaction",
    "clearness_index",
]

# Default target column
_DEFAULT_TARGET: Final[str] = "energy_delta"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_lag_col_names(
    target_col: str,
    lags: list[int],
) -> list[str]:
    """Generate lag column names for a given target and lags."""
    return [f"{target_col}_lag_{lag}" for lag in lags]


def _build_rolling_col_names(
    target_col: str,
    windows: list[int],
) -> list[str]:
    """Generate rolling column names for a given target and windows."""
    cols: list[str] = []
    for w in windows:
        cols.append(f"{target_col}_rolling_mean_{w}")
        cols.append(f"{target_col}_rolling_std_{w}")
    return cols


def _build_weather_lag_col_names(
    weather_cols: list[str],
    lags: list[int],
) -> list[str]:
    """Generate weather-lag column names."""
    return [f"{col}_lag_{lag}" for col in weather_cols for lag in lags]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_feature_columns(
    target_col: str = _DEFAULT_TARGET,
    weather_cols: list[str] | None = None,
    target_lags: list[int] | None = None,
    rolling_windows: list[int] | None = None,
    weather_lags: list[int] | None = None,
) -> dict[str, list[str]]:
    """Return a dictionary of feature-column groups.

    This is useful for downstream model training to know exactly which
    columns to include as input features.

    Parameters
    ----------
    target_col : str
        Name of the target variable.
    weather_cols : list[str] | None
        Raw weather columns.  Defaults to ``_WEATHER_RAW``.
    target_lags : list[int] | None
        Lag steps for the target.  Defaults to ``_DEFAULT_TARGET_LAGS``.
    rolling_windows : list[int] | None
        Rolling-window sizes.  Defaults to ``_DEFAULT_ROLLING_WINDOWS``.
    weather_lags : list[int] | None
        Lag steps for weather columns.  Defaults to ``_DEFAULT_WEATHER_LAGS``.

    Returns
    -------
    dict[str, list[str]]
        Keys: ``temporal_features``, ``lag_features``, ``weather_features``,
        ``all_features``.
    """
    if weather_cols is None:
        weather_cols = list(_WEATHER_RAW)
    if target_lags is None:
        target_lags = list(_DEFAULT_TARGET_LAGS)
    if rolling_windows is None:
        rolling_windows = list(_DEFAULT_ROLLING_WINDOWS)
    if weather_lags is None:
        weather_lags = list(_DEFAULT_WEATHER_LAGS)

    lag_cols = (
        _build_lag_col_names(target_col, target_lags)
        + _build_rolling_col_names(target_col, rolling_windows)
        + _build_weather_lag_col_names(weather_cols, weather_lags)
    )

    weather_feature_cols = list(_WEATHER_RAW) + list(_WEATHER_DERIVED)

    all_features = list(_TEMPORAL_FEATURES) + lag_cols + weather_feature_cols

    result = {
        "temporal_features": list(_TEMPORAL_FEATURES),
        "lag_features": lag_cols,
        "weather_features": weather_feature_cols,
        "all_features": all_features,
    }

    logger.info(
        "Feature columns — temporal: %d, lag: %d, weather: %d, total: %d.",
        len(result["temporal_features"]),
        len(result["lag_features"]),
        len(result["weather_features"]),
        len(result["all_features"]),
    )
    return result


def build_feature_pipeline(
    df_train: pd.DataFrame,
    target_col: str = _DEFAULT_TARGET,
    weather_cols: list[str] | None = None,
    target_lags: list[int] | None = None,
    rolling_windows: list[int] | None = None,
    weather_lags: list[int] | None = None,
    ghi_col: str = "ghi",
    drop_initial_nans: bool = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run the full feature-engineering pipeline on training data.

    Steps executed in order:

    1. Temporal features + cyclical encoding + season
    2. GHI-derived features (ratio, daylight flag, squared)
    3. Weather interaction terms
    4. Clearness index proxy
    5. Target lag features
    6. Target rolling features
    7. Weather lag features
    8. (optional) Drop leading NaN rows caused by lagging

    Parameters
    ----------
    df_train : pd.DataFrame
        Raw training DataFrame (DatetimeIndex, sorted chronologically).
    target_col : str
        Name of the target column.
    weather_cols : list[str] | None
        Raw weather columns to lag.
    target_lags : list[int] | None
        Lag steps for the target.
    rolling_windows : list[int] | None
        Rolling-window sizes.
    weather_lags : list[int] | None
        Weather column lag steps.
    ghi_col : str
        Name of the GHI column.
    drop_initial_nans : bool
        Whether to drop leading rows with NaN lag values.

    Returns
    -------
    tuple[pd.DataFrame, dict[str, Any]]
        (Transformed DataFrame, metadata dict for inference replay).
    """
    if weather_cols is None:
        weather_cols = list(_WEATHER_RAW)
    if target_lags is None:
        target_lags = list(_DEFAULT_TARGET_LAGS)
    if rolling_windows is None:
        rolling_windows = list(_DEFAULT_ROLLING_WINDOWS)
    if weather_lags is None:
        weather_lags = list(_DEFAULT_WEATHER_LAGS)

    logger.info(
        "Building feature pipeline — %d rows, target='%s'.",
        len(df_train),
        target_col,
    )

    # --- 1. Temporal ---------------------------------------------------------
    df = add_time_features(df_train)
    df = add_cyclical_encoding(df)
    df = add_season(df)

    # --- 2. GHI features -----------------------------------------------------
    df, max_ghi = add_ghi_features(df, ghi_col=ghi_col, max_ghi=None)

    # --- 3. Interactions ------------------------------------------------------
    df = add_weather_interactions(df)

    # --- 4. Clearness proxy ---------------------------------------------------
    df = add_clearness_proxy(df, ghi_col=ghi_col)

    # --- 5. Target lags -------------------------------------------------------
    df = add_lag_features(df, target_col=target_col, lags=target_lags)

    # --- 6. Rolling features --------------------------------------------------
    df = add_rolling_features(df, target_col=target_col, windows=rolling_windows)

    # --- 7. Weather lags ------------------------------------------------------
    # Filter to only columns that actually exist in the DataFrame
    available_weather = [c for c in weather_cols if c in df.columns]
    if available_weather:
        df = add_weather_lag_features(df, weather_cols=available_weather, lags=weather_lags)
    else:
        logger.warning("No weather columns found for lagging. Skipping weather lags.")

    # --- 8. Drop leading NaN rows ---------------------------------------------
    max_lag = max(target_lags + weather_lags)
    if drop_initial_nans:
        df = drop_leakage_unsafe_rows(df, max_lag=max_lag)

    # --- Build metadata -------------------------------------------------------
    feature_columns = get_feature_columns(
        target_col=target_col,
        weather_cols=available_weather,
        target_lags=target_lags,
        rolling_windows=rolling_windows,
        weather_lags=weather_lags,
    )

    metadata: dict[str, Any] = {
        "target_col": target_col,
        "ghi_col": ghi_col,
        "max_ghi": max_ghi,
        "weather_cols": available_weather,
        "target_lags": target_lags,
        "rolling_windows": rolling_windows,
        "weather_lags": weather_lags,
        "max_lag": max_lag,
        "feature_columns": feature_columns,
        "n_rows_after_pipeline": len(df),
    }

    logger.info(
        "Feature pipeline complete — %d rows, %d feature columns.",
        len(df),
        len(feature_columns["all_features"]),
    )
    return df, metadata


def apply_feature_pipeline(
    df: pd.DataFrame,
    metadata: dict[str, Any],
    drop_initial_nans: bool = False,
) -> pd.DataFrame:
    """Apply the feature pipeline to new data using saved metadata.

    Replicates exactly the same transformations performed by
    :func:`build_feature_pipeline`, but re-uses training-time constants
    (e.g. ``max_ghi``) stored in *metadata* to avoid data leakage.

    Parameters
    ----------
    df : pd.DataFrame
        New data (DatetimeIndex, sorted chronologically).
    metadata : dict[str, Any]
        Metadata dict produced by :func:`build_feature_pipeline`.
    drop_initial_nans : bool
        Whether to drop leading NaN rows.  Usually ``False`` for
        inference because the caller provides sufficient history.

    Returns
    -------
    pd.DataFrame
        Transformed DataFrame with the same feature columns as training.
    """
    target_col: str = metadata["target_col"]
    ghi_col: str = metadata["ghi_col"]
    max_ghi: float = metadata["max_ghi"]
    weather_cols: list[str] = metadata["weather_cols"]
    target_lags: list[int] = metadata["target_lags"]
    rolling_windows: list[int] = metadata["rolling_windows"]
    weather_lags: list[int] = metadata["weather_lags"]
    max_lag: int = metadata["max_lag"]

    logger.info(
        "Applying saved feature pipeline — %d rows, target='%s'.",
        len(df),
        target_col,
    )

    # 1. Temporal
    df = add_time_features(df)
    df = add_cyclical_encoding(df)
    df = add_season(df)

    # 2. GHI features — use saved max_ghi
    df, _ = add_ghi_features(df, ghi_col=ghi_col, max_ghi=max_ghi)

    # 3. Interactions
    df = add_weather_interactions(df)

    # 4. Clearness proxy
    df = add_clearness_proxy(df, ghi_col=ghi_col)

    # 5. Target lags
    df = add_lag_features(df, target_col=target_col, lags=target_lags)

    # 6. Rolling features
    df = add_rolling_features(df, target_col=target_col, windows=rolling_windows)

    # 7. Weather lags
    available_weather = [c for c in weather_cols if c in df.columns]
    if available_weather:
        df = add_weather_lag_features(df, weather_cols=available_weather, lags=weather_lags)

    # 8. Optionally drop leading NaN rows
    if drop_initial_nans:
        df = drop_leakage_unsafe_rows(df, max_lag=max_lag)

    logger.info(
        "Inference feature pipeline complete — %d rows.",
        len(df),
    )
    return df
