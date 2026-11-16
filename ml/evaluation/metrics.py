"""
Evaluation metrics for solar power forecasting models.

All functions accept array-like inputs (numpy arrays or pandas Series)
and return plain Python floats for easy serialization.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Individual metrics
# ──────────────────────────────────────────────────────────────────────


def calculate_mae(y_true: Any, y_pred: Any) -> float:
    """Compute Mean Absolute Error.

    Args:
        y_true: Ground-truth values.
        y_pred: Predicted values.

    Returns:
        MAE as a Python float.
    """
    return float(mean_absolute_error(y_true, y_pred))


def calculate_rmse(y_true: Any, y_pred: Any) -> float:
    """Compute Root Mean Squared Error.

    Args:
        y_true: Ground-truth values.
        y_pred: Predicted values.

    Returns:
        RMSE as a Python float.
    """
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def calculate_r2(y_true: Any, y_pred: Any) -> float:
    """Compute R² (coefficient of determination).

    Args:
        y_true: Ground-truth values.
        y_pred: Predicted values.

    Returns:
        R² score as a Python float.
    """
    return float(r2_score(y_true, y_pred))


def calculate_safe_mape(
    y_true: Any,
    y_pred: Any,
    epsilon: float = 1.0,
) -> float:
    """Compute a safe variant of Mean Absolute Percentage Error.

    Only daytime observations where ``y_true > epsilon`` are included
    in the calculation, avoiding division-by-zero issues for nighttime
    rows with near-zero generation.

    The formula per sample is::

        |y_true - y_pred| / (|y_true| + epsilon) * 100

    Args:
        y_true: Ground-truth values.
        y_pred: Predicted values.
        epsilon: Minimum absolute value threshold.  Observations with
            ``|y_true| <= epsilon`` are excluded (default 1.0).

    Returns:
        Safe MAPE (percentage) as a Python float.  Returns ``float('nan')``
        if no qualifying observations remain.
    """
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)

    mask = np.abs(y_true_arr) > epsilon
    n_valid = int(mask.sum())

    if n_valid == 0:
        logger.warning(
            "No observations with |y_true| > %.2f; returning NaN for MAPE.",
            epsilon,
        )
        return float("nan")

    yt = y_true_arr[mask]
    yp = y_pred_arr[mask]

    mape = float(np.mean(np.abs(yt - yp) / (np.abs(yt) + epsilon)) * 100.0)
    logger.debug(
        "Safe MAPE computed on %d / %d qualifying samples.", n_valid, len(y_true_arr)
    )
    return mape


# ──────────────────────────────────────────────────────────────────────
# Aggregate evaluation
# ──────────────────────────────────────────────────────────────────────


def evaluate_model(
    y_true: Any,
    y_pred: Any,
    model_name: str,
) -> dict[str, float | str]:
    """Calculate all standard metrics for a single model.

    Args:
        y_true: Ground-truth values.
        y_pred: Predicted values.
        model_name: Human-readable identifier (included in the
            returned dict and log messages).

    Returns:
        Dictionary with keys ``model_name``, ``mae``, ``rmse``, ``r2``,
        and ``safe_mape``.
    """
    mae = calculate_mae(y_true, y_pred)
    rmse = calculate_rmse(y_true, y_pred)
    r2 = calculate_r2(y_true, y_pred)
    safe_mape = calculate_safe_mape(y_true, y_pred)

    logger.info(
        "Evaluation '%s' — MAE: %.2f | RMSE: %.2f | R²: %.4f | MAPE: %.2f%%",
        model_name,
        mae,
        rmse,
        r2,
        safe_mape,
    )

    return {
        "model_name": model_name,
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "safe_mape": safe_mape,
    }


# ──────────────────────────────────────────────────────────────────────
# Model comparison
# ──────────────────────────────────────────────────────────────────────


def compare_models(results: dict[str, dict[str, Any]]) -> pd.DataFrame:
    """Build a sorted comparison table from per-model evaluation dicts.

    Args:
        results: Mapping of ``{model_name: metrics_dict}``.  Each
            *metrics_dict* must contain at least ``mae``, ``rmse``,
            ``r2``, and ``safe_mape`` keys.

    Returns:
        A :class:`~pandas.DataFrame` with one row per model, sorted
        by ascending RMSE (best first).
    """
    rows: list[dict[str, Any]] = []
    for name, metrics in results.items():
        row = {"model_name": name}
        row.update(metrics)
        rows.append(row)

    comparison_df = (
        pd.DataFrame(rows)
        .sort_values("rmse", ascending=True)
        .reset_index(drop=True)
    )

    logger.info(
        "Model comparison table (%d models, sorted by RMSE):\n%s",
        len(comparison_df),
        comparison_df.to_string(index=False),
    )
    return comparison_df
