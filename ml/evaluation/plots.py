"""
Evaluation visualizations for SolarCast AI models.

Every function saves the figure to *output_path*, closes it to free
memory, and returns the path for downstream logging / report generation.
Figures are **not** displayed interactively (``plt.show()`` is never
called).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — must precede pyplot import

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Shared style defaults ────────────────────────────────────────────
_STYLE = "seaborn-v0_8-whitegrid"
_DPI = 150
_SCATTER_ALPHA = 0.25
_SCATTER_SIZE = 4


def _apply_style() -> None:
    """Apply a clean shared style if available, else fall back."""
    try:
        plt.style.use(_STYLE)
    except OSError:
        plt.style.use("ggplot")


# ──────────────────────────────────────────────────────────────────────
# 1. Actual vs Predicted scatter
# ──────────────────────────────────────────────────────────────────────


def plot_actual_vs_predicted(
    y_true: Any,
    y_pred: Any,
    model_name: str,
    output_path: Path,
) -> Path:
    """Scatter plot of actual vs predicted values with a 45° reference.

    Args:
        y_true: Ground-truth values.
        y_pred: Predicted values.
        model_name: Name used in the title.
        output_path: File path to save the figure.

    Returns:
        The *output_path* after the figure has been written.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _apply_style()

    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(y_true_arr, y_pred_arr, alpha=_SCATTER_ALPHA, s=_SCATTER_SIZE, edgecolors="none")

    # 45-degree perfect-prediction line
    lo = min(y_true_arr.min(), y_pred_arr.min())
    hi = max(y_true_arr.max(), y_pred_arr.max())
    ax.plot([lo, hi], [lo, hi], "r--", linewidth=1.5, label="Perfect prediction")

    ax.set_xlabel("Actual Energy [Wh]")
    ax.set_ylabel("Predicted Energy [Wh]")
    ax.set_title(f"Actual vs Predicted — {model_name}")
    ax.legend(loc="upper left")

    fig.tight_layout()
    fig.savefig(output_path, dpi=_DPI)
    plt.close(fig)

    logger.info("Saved actual-vs-predicted plot → %s", output_path)
    return output_path


# ──────────────────────────────────────────────────────────────────────
# 2. Residual distribution
# ──────────────────────────────────────────────────────────────────────


def plot_residuals(
    y_true: Any,
    y_pred: Any,
    model_name: str,
    output_path: Path,
) -> Path:
    """Histogram + KDE of prediction residuals (actual − predicted).

    Args:
        y_true: Ground-truth values.
        y_pred: Predicted values.
        model_name: Name used in the title.
        output_path: File path to save the figure.

    Returns:
        The *output_path* after the figure has been written.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _apply_style()

    residuals = np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Histogram
    axes[0].hist(residuals, bins=100, edgecolor="black", alpha=0.7)
    axes[0].axvline(0, color="red", linestyle="--", linewidth=1.5)
    axes[0].set_xlabel("Residual [Wh]")
    axes[0].set_ylabel("Frequency")
    axes[0].set_title(f"Residual Distribution — {model_name}")

    # Residual vs predicted
    y_pred_arr = np.asarray(y_pred, dtype=float)
    axes[1].scatter(y_pred_arr, residuals, alpha=_SCATTER_ALPHA, s=_SCATTER_SIZE, edgecolors="none")
    axes[1].axhline(0, color="red", linestyle="--", linewidth=1.5)
    axes[1].set_xlabel("Predicted Energy [Wh]")
    axes[1].set_ylabel("Residual [Wh]")
    axes[1].set_title(f"Residuals vs Predicted — {model_name}")

    fig.tight_layout()
    fig.savefig(output_path, dpi=_DPI)
    plt.close(fig)

    logger.info("Saved residuals plot → %s", output_path)
    return output_path


# ──────────────────────────────────────────────────────────────────────
# 3. Prediction error over time
# ──────────────────────────────────────────────────────────────────────


def plot_prediction_error_over_time(
    y_true: Any,
    y_pred: Any,
    timestamps: Any,
    model_name: str,
    output_path: Path,
) -> Path:
    """Time-series plot of absolute prediction error.

    Args:
        y_true: Ground-truth values.
        y_pred: Predicted values.
        timestamps: Datetime-like sequence aligned with *y_true*.
        model_name: Name used in the title.
        output_path: File path to save the figure.

    Returns:
        The *output_path* after the figure has been written.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _apply_style()

    error = np.abs(np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float))
    ts = pd.to_datetime(timestamps)

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(ts, error, linewidth=0.5, alpha=0.6)

    # Rolling daily mean for readability
    window = min(96, len(error))  # 96 × 15 min = 1 day
    if window > 1:
        rolling_mean = pd.Series(error).rolling(window=window, min_periods=1).mean()
        ax.plot(ts, rolling_mean, color="red", linewidth=1.5, label=f"Rolling mean (w={window})")
        ax.legend()

    ax.set_xlabel("Time")
    ax.set_ylabel("Absolute Error [Wh]")
    ax.set_title(f"Prediction Error Over Time — {model_name}")

    fig.tight_layout()
    fig.savefig(output_path, dpi=_DPI)
    plt.close(fig)

    logger.info("Saved error-over-time plot → %s", output_path)
    return output_path


# ──────────────────────────────────────────────────────────────────────
# 4. Model comparison bar chart
# ──────────────────────────────────────────────────────────────────────


def plot_model_comparison(
    comparison_df: pd.DataFrame,
    output_path: Path,
) -> Path:
    """Grouped bar chart comparing models across MAE, RMSE, and R².

    Args:
        comparison_df: DataFrame with columns ``model_name``, ``mae``,
            ``rmse``, ``r2`` (and optionally ``safe_mape``).
        output_path: File path to save the figure.

    Returns:
        The *output_path* after the figure has been written.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _apply_style()

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    models = comparison_df["model_name"].values

    # MAE
    axes[0].barh(models, comparison_df["mae"], color="steelblue")
    axes[0].set_xlabel("MAE [Wh]")
    axes[0].set_title("Mean Absolute Error")
    axes[0].invert_yaxis()

    # RMSE
    axes[1].barh(models, comparison_df["rmse"], color="coral")
    axes[1].set_xlabel("RMSE [Wh]")
    axes[1].set_title("Root Mean Squared Error")
    axes[1].invert_yaxis()

    # R²
    axes[2].barh(models, comparison_df["r2"], color="seagreen")
    axes[2].set_xlabel("R²")
    axes[2].set_title("R² Score")
    axes[2].invert_yaxis()

    fig.suptitle("Model Comparison", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(output_path, dpi=_DPI)
    plt.close(fig)

    logger.info("Saved model comparison plot → %s", output_path)
    return output_path


# ──────────────────────────────────────────────────────────────────────
# 5. Feature importance (tree-based models)
# ──────────────────────────────────────────────────────────────────────


def plot_feature_importance(
    model: Any,
    feature_names: list[str],
    model_name: str,
    output_path: Path,
    top_n: int = 25,
) -> Path:
    """Horizontal bar chart of feature importances for tree-based models.

    If *model* is a :class:`~sklearn.pipeline.Pipeline`, the last step
    is inspected for ``feature_importances_``.

    Args:
        model: A fitted model with a ``feature_importances_`` attribute.
        feature_names: Names corresponding to each importance value.
        model_name: Name used in the title.
        output_path: File path to save the figure.
        top_n: Number of top features to display (default 25).

    Returns:
        The *output_path* after the figure has been written.

    Raises:
        AttributeError: If the model does not expose
            ``feature_importances_``.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _apply_style()

    # Unwrap pipeline if necessary
    estimator = model
    if hasattr(model, "named_steps"):
        # Get the last step in the pipeline
        estimator = list(model.named_steps.values())[-1]

    if not hasattr(estimator, "feature_importances_"):
        raise AttributeError(
            f"Model '{model_name}' ({type(estimator).__name__}) does not "
            "have feature_importances_. This plot is only for tree-based models."
        )

    importances = estimator.feature_importances_
    indices = np.argsort(importances)[::-1][:top_n]

    sorted_names = [feature_names[i] for i in indices]
    sorted_importances = importances[indices]

    fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.35)))
    ax.barh(range(len(sorted_names)), sorted_importances[::-1], color="teal", edgecolor="black", linewidth=0.3)
    ax.set_yticks(range(len(sorted_names)))
    ax.set_yticklabels(sorted_names[::-1])
    ax.set_xlabel("Importance")
    ax.set_title(f"Top {len(sorted_names)} Feature Importances — {model_name}")

    fig.tight_layout()
    fig.savefig(output_path, dpi=_DPI)
    plt.close(fig)

    logger.info("Saved feature importance plot → %s", output_path)
    return output_path
