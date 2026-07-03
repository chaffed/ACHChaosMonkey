import pytest

from achchaosmonkey.db import models
from achchaosmonkey.db.ingest import ingest_file_record
from achchaosmonkey.generator.builder import build_file
from achchaosmonkey.generator.chaos import ChaosConfig
from achchaosmonkey.io import csv_io, excel_io, nacha_io
from achchaosmonkey.nacha.writer import assemble_file


@pytest.fixture
def seeded_db_file(db_session):
    generated = build_file(num_batches=2, entries_per_batch=6, chaos=ChaosConfig.preset("high"), seed=55)
    assemble_file(generated.record, overrides=generated.overrides)
    db_file = ingest_file_record(db_session, generated.record, source=models.SOURCE_GENERATED, labels=generated.labels)
    db_session.commit()
    return db_file


def entry_count(db_file) -> int:
    return sum(len(b.entries) for b in db_file.batches)


def fraud_or_miscoded_count(db_file) -> int:
    return sum(1 for b in db_file.batches for e in b.entries if e.is_fraud or e.is_miscoded)


def test_nacha_export_import_preserves_entry_count(db_session, seeded_db_file):
    text = nacha_io.export_nacha(seeded_db_file)
    reimported = nacha_io.import_nacha(db_session, text, original_filename="roundtrip.ach")
    db_session.commit()
    assert entry_count(reimported) == entry_count(seeded_db_file)


def test_nacha_export_import_preserves_batch_control_totals(db_session, seeded_db_file):
    text = nacha_io.export_nacha(seeded_db_file)
    reimported = nacha_io.import_nacha(db_session, text, original_filename="roundtrip.ach")
    db_session.commit()

    original_hashes = [b.entry_hash for b in seeded_db_file.batches]
    reimported_hashes = [b.entry_hash for b in reimported.batches]
    assert original_hashes == reimported_hashes


def test_nacha_export_preserves_corrupted_control_totals(db_session):
    from achchaosmonkey.generator.strategies import BATCH_MISCODE_STRATEGIES, BatchContext
    import random

    generated = build_file(num_batches=1, entries_per_batch=3, chaos=ChaosConfig.none(), seed=1)
    batch = generated.record.batches[0]
    label, control_override = BATCH_MISCODE_STRATEGIES["bad_control_totals"](batch, BatchContext(rng=random.Random(9)))
    generated.overrides = {"batch_control": {batch.header.batch_number: control_override}}
    generated.labels[(0, 0)] = label
    assemble_file(generated.record, overrides=generated.overrides)

    db_file = ingest_file_record(db_session, generated.record, source=models.SOURCE_GENERATED, labels=generated.labels)
    db_session.commit()
    corrupted_hash = db_file.batches[0].entry_hash

    text = nacha_io.export_nacha(db_file)
    reimported = nacha_io.import_nacha(db_session, text, original_filename="roundtrip.ach")
    db_session.commit()

    assert reimported.batches[0].entry_hash == corrupted_hash


def test_csv_export_import_preserves_entries_and_labels(db_session, seeded_db_file):
    text = csv_io.export_csv(seeded_db_file)
    reimported = csv_io.import_csv(db_session, text, original_filename="roundtrip.csv")
    db_session.commit()

    assert entry_count(reimported) == entry_count(seeded_db_file)
    assert fraud_or_miscoded_count(reimported) == fraud_or_miscoded_count(seeded_db_file)
    assert reimported.source == models.SOURCE_IMPORTED


def test_csv_export_import_preserves_amounts_and_names(db_session, seeded_db_file):
    text = csv_io.export_csv(seeded_db_file)
    reimported = csv_io.import_csv(db_session, text, original_filename="roundtrip.csv")
    db_session.commit()

    original_amounts = sorted(e.amount_cents for b in seeded_db_file.batches for e in b.entries)
    reimported_amounts = sorted(e.amount_cents for b in reimported.batches for e in b.entries)
    assert original_amounts == reimported_amounts


def test_excel_export_import_preserves_entries_and_labels(db_session, seeded_db_file):
    content = excel_io.export_excel(seeded_db_file)
    reimported = excel_io.import_excel(db_session, content, original_filename="roundtrip.xlsx")
    db_session.commit()

    assert entry_count(reimported) == entry_count(seeded_db_file)
    assert fraud_or_miscoded_count(reimported) == fraud_or_miscoded_count(seeded_db_file)


def test_csv_import_rejects_empty_file(db_session):
    with pytest.raises(ValueError):
        csv_io.import_csv(db_session, "col_a,col_b\n", original_filename="empty.csv")


def test_nacha_import_rejects_malformed_text(db_session):
    from achchaosmonkey.nacha.exceptions import RecordParseError

    with pytest.raises(RecordParseError):
        nacha_io.import_nacha(db_session, "not a valid nacha file\n", original_filename="bad.ach")
