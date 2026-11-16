"""
Model training orchestrator for SolarCast AI.

Provides utilities to configure, train, persist, and reload regression
models — from a persistence baseline through gradient-boosted trees.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

from ml.training.baseline import PersistenceBaseline

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# 1. Model configuration registry
# ──────────────────────────────────────────────────────────────────────


def get_model_configs() -> dict[str, dict[str, Any]]:
    """Return a registry of model configurations.

    Each entry is a dict with keys:

    * ``"model"`` — an un-fitted estimator instance.
    * ``"use_pipeline"`` — whether to wrap in a StandardScaler pipeline.

    Returns:
        Dictionary keyed by model name.
    """
    configs: dict[str, dict[str, Any]] = {
        "persistence_baseline": {
            "model": PersistenceBaseline(lag_column="energy_delta_wh_lag_96"),
            "use_pipeline": False,
        },
        "linear_regression": {
            "model": LinearRegression(),
            "use_pipeline": True,
        },
        "decision_tree": {
            "model": DecisionTreeRegressor(
                max_depth=15,
                min_samples_leaf=10,
                random_state=42,
            ),
            "use_pipeline": False,
        },
        "random_forest": {
            "model": RandomForestRegressor(
                n_estimators=200,
                max_depth=20,
                min_samples_leaf=5,
                n_jobs=-1,
                random_state=42,
            ),
            "use_pipeline": False,
        },
        "gradient_boosting": {
            "model": GradientBoostingRegressor(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42,
            ),
            "use_pipeline": False,
        },
    }
    logger.info("Registered %d model configurations.", len(configs))
    return configs


# ──────────────────────────────────────────────────────────────────────
# 2. Single-model training
# ──────────────────────────────────────────────────────────────────────


def train_model(
    model: Any,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    model_name: str,
) -> tuple[Any, float]:
    """Train a single model and measure wall-clock time.

    Args:
        model: An unfitted scikit-learn–compatible estimator.
        X_train: Training features.
        y_train: Training target.
        model_name: Human-readable name (used in logs).

    Returns:
        A tuple of (fitted_model, training_time_seconds).
    """
    logger.info(
        "Training '%s' on %d samples with %d features …",
        model_name,
        len(X_train),
        X_train.shape[1],
    )

    start = time.perf_counter()
    model.fit(X_train, y_train)
    elapsed = time.perf_counter() - start

    logger.info("'%s' trained in %.2f s.", model_name, elapsed)
    return model, elapsed


# ──────────────────────────────────────────────────────────────────────
# 3. Train all models
# ──────────────────────────────────────────────────────────────────────


def train_all_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    feature_columns: list[str],
) -> dict[str, dict[str, Any]]:
    """Train every model in the configuration registry.

    For models that require feature scaling (``use_pipeline=True``), a
    ``sklearn.pipeline.Pipeline`` with a :class:`StandardScaler` is
    built automatically.

    Args:
        X_train: Training features (all columns available).
        y_train: Training target.
        feature_columns: List of feature column names to select from
            *X_train*.  The persistence baseline receives the full
            DataFrame so that lag columns are visible.

    Returns:
        A dict keyed by model name, each value being a dict with:
            * ``"model"`` — the fitted model/pipeline.
            * ``"training_time"`` — wall-clock seconds.
            * ``"feature_columns"`` — columns used.
    """
    configs = get_model_configs()
    results: dict[str, dict[str, Any]] = {}

    for name, cfg in configs.items():
        estimator = cfg["model"]

        # The persistence baseline needs access to lag columns, so give
        # it the full DataFrame rather than the reduced feature set.
        if isinstance(estimator, PersistenceBaseline):
            X_subset = X_train
        else:
            X_subset = X_train[feature_columns]

        # Wrap in a scaling pipeline when requested.
        if cfg["use_pipeline"]:
            pipeline = Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("model", estimator),
                ]
            )
            fitted, elapsed = train_model(pipeline, X_subset, y_train, name)
        else:
            fitted, elapsed = train_model(estimator, X_subset, y_train, name)

        results[name] = {
            "model": fitted,
            "training_time": elapsed,
            "feature_columns": (
                list(X_subset.columns) if isinstance(X_subset, pd.DataFrame) else feature_columns
            ),
        }

    logger.info(
        "All %d models trained. Total time: %.2f s.",
        len(results),
        sum(r["training_time"] for r in results.values()),
    )
    return results


# ──────────────────────────────────────────────────────────────────────
# 4. Persistence helpers
# ──────────────────────────────────────────────────────────────────────


def save_model(
    model: Any,
    model_name: str,
    metadata: dict[str, Any],
    artifacts_dir: Path,
) -> Path:
    """Serialize a trained model and its metadata to disk.

    Two files are created inside *artifacts_dir*:

    * ``<model_name>.joblib`` — the model object.
    * ``<model_name>_metadata.json`` — accompanying metadata.

    Args:
        model: Fitted model / pipeline.
        model_name: Identifier used as the file stem.
        metadata: Arbitrary metadata dict (metrics, dates, etc.).
        artifacts_dir: Target directory (created if needed).

    Returns:
        Path to the saved ``.joblib`` file.
    """
    artifacts_dir = Path(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    model_path = artifacts_dir / f"{model_name}.joblib"
    meta_path = artifacts_dir / f"{model_name}_metadata.json"

    joblib.dump(model, model_path)
    logger.info("Model '%s' saved → %s", model_name, model_path)

    # Ensure metadata is JSON-serializable (convert numpy types).
    clean_meta = _sanitize_for_json(metadata)
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(clean_meta, fh, indent=2, default=str)
    logger.info("Metadata saved → %s", meta_path)

    return model_path


def load_model(model_path: Path) -> Any:
    """Load a model previously saved with :func:`save_model`.

    Args:
        model_path: Path to the ``.joblib`` file.

    Returns:
        The deserialized model object.

    Raises:
        FileNotFoundError: If *model_path* does not exist.
    """
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    model = joblib.load(model_path)
    logger.info("Model loaded from %s", model_path)
    return model


# ──────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────


def _sanitize_for_json(obj: Any) -> Any:
    """Recursively convert numpy / pandas types to JSON-safe Python types."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    return obj
