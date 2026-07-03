"""Unsupervised anomaly detection over the feature vectors from features.py."""

from pathlib import Path

import joblib
from sklearn.ensemble import IsolationForest

from ..settings import settings
from .features import FEATURE_NAMES

DEFAULT_MODEL_PATH = settings.ml_artifact_dir / "isolation_forest.joblib"


class AnomalyModel:
    def __init__(self, contamination: float = 0.1, random_state: int = 42):
        self.model = IsolationForest(contamination=contamination, random_state=random_state, n_estimators=200)
        self.fitted = False

    def fit(self, feature_matrix: list[list[float]]) -> None:
        self.model.fit(feature_matrix)
        self.fitted = True

    def score(self, feature_matrix: list[list[float]]) -> list[float]:
        """Returns a risk score in [0, 1] per row, higher = more anomalous."""
        if not self.fitted or not feature_matrix:
            return [0.0] * len(feature_matrix)
        raw = self.model.decision_function(feature_matrix)  # positive = inlier, negative = outlier
        return [max(0.0, min(1.0, 0.5 - value)) for value in raw]

    def save(self, path: Path | None = None) -> Path:
        path = path or DEFAULT_MODEL_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "fitted": self.fitted, "feature_names": FEATURE_NAMES}, path)
        return path

    @classmethod
    def load(cls, path: Path | None = None) -> "AnomalyModel":
        path = path or DEFAULT_MODEL_PATH
        data = joblib.load(path)
        instance = cls()
        instance.model = data["model"]
        instance.fitted = data["fitted"]
        return instance
