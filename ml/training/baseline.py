"""
Persistence baseline model for solar power forecasting.

Uses a lagged value of the target as its prediction, providing a
simple, hard-to-beat reference for more complex models.  The default
strategy is "same time yesterday" (lag_96 for 15-minute intervals).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin

logger = logging.getLogger(__name__)


class PersistenceBaseline(BaseEstimator, RegressorMixin):
    """Persistence (lag) baseline regressor.

    Predicts the target value as the lagged observation stored in a
    pre-computed column of the input DataFrame/array.

    Parameters:
        lag_column: Name of the lag column to use as the prediction
            (default ``"energy_delta_wh_lag_96"``).  Falls back to
            ``"energy_delta_wh_lag_1"`` if the specified column is
            absent in the input data.

    Notes:
        * ``fit()`` is a no-op — included for scikit-learn pipeline
          compatibility.
        * NaN lag values are filled with 0.0 so that the output
          array never contains NaNs.

    Examples:
        >>> model = PersistenceBaseline(lag_column="energy_delta_wh_lag_96")
        >>> model.fit(X_train, y_train)
        PersistenceBaseline(lag_column='energy_delta_wh_lag_96')
        >>> preds = model.predict(X_test)
    """

    # Explicit list for sklearn clone / get_params
    _FALLBACK_COLUMN = "energy_delta_wh_lag_1"

    def __init__(self, lag_column: str = "energy_delta_wh_lag_96") -> None:
        self.lag_column = lag_column

    # ------------------------------------------------------------------ fit
    def fit(
        self,
        X: pd.DataFrame | np.ndarray,
        y: pd.Series | np.ndarray | None = None,
    ) -> "PersistenceBaseline":
        """No-op fit for scikit-learn compatibility.

        Args:
            X: Feature matrix (ignored).
            y: Target vector (ignored).

        Returns:
            self
        """
        logger.info(
            "PersistenceBaseline.fit() called (no-op). lag_column='%s'",
            self.lag_column,
        )
        return self

    # -------------------------------------------------------------- predict
    def predict(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        """Return lagged values as predictions.

        If *X* is a DataFrame and contains ``self.lag_column``, that
        column is used.  Otherwise, the fallback column
        ``energy_delta_wh_lag_1`` is tried.  If neither column exists
        (or *X* is a plain ndarray), the method raises a ``ValueError``.

        Args:
            X: Feature matrix.  Must be a :class:`pandas.DataFrame`
                containing the lag column.

        Returns:
            1-D numpy array of predictions.

        Raises:
            ValueError: If the lag column cannot be found in *X*.
        """
        col = self._resolve_column(X)
        logger.info("PersistenceBaseline.predict() using column '%s'", col)

        predictions: np.ndarray = X[col].values.astype(float).copy()
        nan_count = int(np.isnan(predictions).sum())
        if nan_count > 0:
            logger.warning(
                "Filling %d NaN lag values with 0.0 in predictions.", nan_count
            )
            predictions = np.nan_to_num(predictions, nan=0.0)

        return predictions

    # --------------------------------------------------- internal helpers
    def _resolve_column(self, X: Any) -> str:
        """Determine which lag column to use, with fallback logic.

        Args:
            X: Feature matrix (expected to be a DataFrame).

        Returns:
            Column name to use for predictions.

        Raises:
            ValueError: If no usable lag column is found.
        """
        if not isinstance(X, pd.DataFrame):
            raise ValueError(
                "PersistenceBaseline requires a pandas DataFrame as input, "
                f"got {type(X).__name__}."
            )

        if self.lag_column in X.columns:
            return self.lag_column

        if self._FALLBACK_COLUMN in X.columns:
            logger.warning(
                "Preferred lag column '%s' not found; falling back to '%s'.",
                self.lag_column,
                self._FALLBACK_COLUMN,
            )
            return self._FALLBACK_COLUMN

        raise ValueError(
            f"Neither '{self.lag_column}' nor '{self._FALLBACK_COLUMN}' "
            f"found in input columns: {list(X.columns)}"
        )

    # --------------------------------------------------- repr
    def __repr__(self) -> str:
        return f"PersistenceBaseline(lag_column='{self.lag_column}')"
