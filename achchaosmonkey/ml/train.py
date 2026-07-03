"""CLI: pull entries from the DB, extract features, fit the anomaly model, persist it.

    python -m achchaosmonkey.ml.train [--contamination 0.1]
"""

import argparse
from pathlib import Path

from ..db import models
from ..db.base import SessionLocal, init_db
from ..validator.anomaly import AnomalyModel
from ..validator.features import extract_batch_features


def train_from_db(contamination: float | None = None) -> tuple[AnomalyModel, int, Path]:
    init_db()
    session = SessionLocal()
    try:
        batches = session.query(models.AchBatch).all()
        matrix: list[list[float]] = []
        for batch in batches:
            matrix.extend(extract_batch_features(batch).values())

        if contamination is None:
            entries = session.query(models.AchEntry).all()
            dirty = sum(1 for e in entries if e.is_fraud or e.is_miscoded)
            contamination = min(0.5, max(0.01, dirty / len(entries))) if entries else 0.1

        model = AnomalyModel(contamination=contamination)
        if matrix:
            model.fit(matrix)
        path = model.save()
        return model, len(matrix), path
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the ACH anomaly-detection model from the current DB corpus.")
    parser.add_argument("--contamination", type=float, default=None)
    args = parser.parse_args()

    model, n, path = train_from_db(contamination=args.contamination)
    status = "fitted" if model.fitted else "skipped (no entries in DB)"
    print(f"Trained on {n} entries ({status}). Model saved to {path}")


if __name__ == "__main__":
    main()
