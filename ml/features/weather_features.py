"""
SolarCast AI — Weather-Derived Feature Engineering.

Computes features derived from raw weather observations (GHI, temperature,
humidity, etc.) for solar power forecasting.

Functions
---------
add_ghi_features           : GHI ratio, daylight flag, squared GHI
add_weather_interactions   : pairwise interaction terms
add_clearness_proxy        : estimated clearness index from solar geometry
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
_SOLAR_CONSTANT: Final[float] = 1361.0  # W/m² — TSI at top of atmosphere
_MIN_CLEARSKY_GHI: Final[float] = 1.0   # floor to avoid division by zero


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_datetime_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    """Return the DatetimeIndex of *df*, raising if it isn't one."""
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError(
            f"DataFrame index must be a DatetimeIndex, got {type(df.index).__name__}."
        )
    return df.index


def _estimate_clear_sky_ghi(dt_index: pd.DatetimeIndex) -> pd.Series:
    """Estimate clear-sky GHI via simplified solar geometry.

    Uses the day-of-year to compute the solar declination and approximates
    the hour angle from the hour / minute of the timestamp.  The result is
    a *rough* extraterrestrial horizontal irradiance that serves as a
    denominator for the clearness index.

    .. note::
       This is intentionally simple — a more accurate model (e.g. Ineichen–
       Perez) can replace this later without changing the interface.

    Parameters
    ----------
    dt_index : pd.DatetimeIndex
        Timestamps for which to compute clear-sky GHI.

    Returns
    -------
    pd.Series
        Estimated clear-sky GHI (W/m²), floored at ``_MIN_CLEARSKY_GHI``.
    """
    day_of_year = dt_index.dayofyear.to_numpy(dtype=np.float64)
    hour_decimal = (
        dt_index.hour.to_numpy(dtype=np.float64)
        + dt_index.minute.to_numpy(dtype=np.float64) / 60.0
    )

    # Solar declination (radians) — Spencer (1971) simplified
    gamma = 2.0 * np.pi * (day_of_year - 1) / 365.0
    declination = (
        0.006918
        - 0.399912 * np.cos(gamma)
        + 0.070257 * np.sin(gamma)
        - 0.006758 * np.cos(2.0 * gamma)
        + 0.000907 * np.sin(2.0 * gamma)
        - 0.002697 * np.cos(3.0 * gamma)
        + 0.00148 * np.sin(3.0 * gamma)
    )

    # Hour angle (radians) — solar noon ≈ 12:00 local time
    hour_angle = np.radians(15.0 * (hour_decimal - 12.0))

    # Assume a mid-latitude location (~35°N) when lat is unknown
    latitude_rad = np.radians(35.0)

    cos_zenith = (
        np.sin(latitude_rad) * np.sin(declination)
        + np.cos(latitude_rad) * np.cos(declination) * np.cos(hour_angle)
    )
    cos_zenith = np.clip(cos_zenith, 0.0, 1.0)

    # Extraterrestrial horizontal irradiance
    clear_sky = _SOLAR_CONSTANT * cos_zenith

    # Atmospheric transmittance factor (~0.75 for clear sky at sea level)
    clear_sky *= 0.75

    return pd.Series(
        np.maximum(clear_sky, _MIN_CLEARSKY_GHI),
        index=dt_index,
        name="clear_sky_ghi",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_ghi_features(
    df: pd.DataFrame,
    ghi_col: str = "ghi",
    max_ghi: float | None = None,
) -> tuple[pd.DataFrame, float]:
    """Derive features from the Global Horizontal Irradiance column.

    Created columns:

    * ``ghi_ratio`` — GHI normalised by the observed maximum (0–1 range).
    * ``is_daylight`` — binary flag: 1 when GHI > 0, else 0.
    * ``ghi_squared`` — GHI² to capture non-linear effects.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame containing a GHI column.
    ghi_col : str, default ``"ghi"``
        Name of the GHI column.
    max_ghi : float | None
        Pre-computed maximum GHI (e.g. from training set).  When ``None``
        the maximum is computed from the data — use this only for training.
        For inference pass the training max to avoid data leakage.

    Returns
    -------
    tuple[pd.DataFrame, float]
        (transformed DataFrame, max_ghi used for normalisation).

    Raises
    ------
    KeyError
        If *ghi_col* is not in the DataFrame.
    """
    if ghi_col not in df.columns:
        raise KeyError(f"GHI column '{ghi_col}' not found in DataFrame.")

    df = df.copy()

    if max_ghi is None:
        max_ghi = float(df[ghi_col].max())
        logger.info("Computed max GHI from data: %.2f", max_ghi)
    else:
        logger.info("Using pre-computed max GHI: %.2f", max_ghi)

    safe_max = max_ghi if max_ghi > 0 else 1.0  # prevent division by zero
    df["ghi_ratio"] = df[ghi_col] / safe_max
    df["is_daylight"] = (df[ghi_col] > 0).astype(int)
    df["ghi_squared"] = df[ghi_col] ** 2

    logger.info(
        "Added GHI features: ghi_ratio (max=%.2f), is_daylight, ghi_squared.",
        max_ghi,
    )
    return df, max_ghi


def add_weather_interactions(df: pd.DataFrame) -> pd.DataFrame:
    """Create pairwise interaction features from weather columns.

    Created columns:

    * ``ghi_temp_interaction`` — GHI × temperature
    * ``temp_humidity_interaction`` — temperature × humidity

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns whose names include *ghi*, *temperature*
        (or *temp*), and *humidity*.

    Returns
    -------
    pd.DataFrame
        A copy of *df* with interaction columns appended.

    Raises
    ------
    KeyError
        If required source columns are missing.
    """
    # Flexible column resolution ------------------------------------------------
    def _find(candidates: list[str], label: str) -> str:
        for c in candidates:
            if c in df.columns:
                return c
        raise KeyError(
            f"Cannot find a '{label}' column. Tried: {candidates}. "
            f"Available: {list(df.columns)}"
        )

    ghi_col = _find(["ghi", "GHI", "Ghi"], "GHI")
    temp_col = _find(
        ["temperature", "temp", "Temperature", "Temp", "air_temperature"],
        "temperature",
    )
    hum_col = _find(
        ["humidity", "Humidity", "relative_humidity", "RelativeHumidity"],
        "humidity",
    )

    df = df.copy()
    df["ghi_temp_interaction"] = df[ghi_col] * df[temp_col]
    df["temp_humidity_interaction"] = df[temp_col] * df[hum_col]

    logger.info(
        "Added interaction features: ghi_temp_interaction (%s × %s), "
        "temp_humidity_interaction (%s × %s).",
        ghi_col,
        temp_col,
        temp_col,
        hum_col,
    )
    return df


def add_clearness_proxy(
    df: pd.DataFrame,
    ghi_col: str = "ghi",
) -> pd.DataFrame:
    """Estimate a clearness index as a proxy for cloud cover.

    The *clearness index* is defined as the ratio of actual GHI to the
    estimated clear-sky GHI.  Values near 1.0 indicate clear skies; lower
    values suggest cloud cover.

    The clear-sky GHI is estimated from simple solar geometry (hour angle
    + solar declination) — see :func:`_estimate_clear_sky_ghi`.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with a ``DatetimeIndex`` and a GHI column.
    ghi_col : str, default ``"ghi"``
        Name of the GHI column.

    Returns
    -------
    pd.DataFrame
        A copy of *df* with ``clearness_index`` appended (capped at 1.0).
    """
    idx = _ensure_datetime_index(df)

    if ghi_col not in df.columns:
        raise KeyError(f"GHI column '{ghi_col}' not found in DataFrame.")

    df = df.copy()

    clear_sky = _estimate_clear_sky_ghi(idx)
    raw_index = df[ghi_col] / clear_sky
    df["clearness_index"] = raw_index.clip(upper=1.0)

    logger.info(
        "Added clearness_index (mean=%.3f, median=%.3f).",
        df["clearness_index"].mean(),
        df["clearness_index"].median(),
    )
    return df
