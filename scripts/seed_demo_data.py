"""Populate the local dev database with a demo corpus so the UI has something to show.

    python scripts/seed_demo_data.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from achchaosmonkey.db import models  # noqa: E402
from achchaosmonkey.db.base import SessionLocal, init_db  # noqa: E402
from achchaosmonkey.db.ingest import ingest_file_record  # noqa: E402
from achchaosmonkey.generator.builder import build_file  # noqa: E402
from achchaosmonkey.generator.chaos import ChaosConfig  # noqa: E402
from achchaosmonkey.ml.train import train_from_db  # noqa: E402
from achchaosmonkey.nacha.writer import assemble_file  # noqa: E402

SCENARIOS = [
    ("none", 2, 25, 100),
    ("low", 2, 25, 101),
    ("medium", 3, 30, 102),
    ("high", 2, 20, 103),
]


def main() -> None:
    init_db()
    session = SessionLocal()
    try:
        for chaos_level, num_batches, entries_per_batch, seed in SCENARIOS:
            generated = build_file(
                num_batches=num_batches,
                entries_per_batch=entries_per_batch,
                chaos=ChaosConfig.preset(chaos_level),
                seed=seed,
            )
            assemble_file(generated.record, overrides=generated.overrides)
            db_file = ingest_file_record(
                session, generated.record, source=models.SOURCE_GENERATED, labels=generated.labels
            )
            session.commit()
            num_entries = sum(len(b.entries) for b in generated.record.batches)
            num_labeled = len(generated.labels)
            print(f"chaos={chaos_level:>6}: file #{db_file.id}, {num_entries} entries, {num_labeled} labeled")
    finally:
        session.close()

    _, count, path = train_from_db()
    print(f"Trained anomaly model on {count} entries -> {path}")


if __name__ == "__main__":
    main()
