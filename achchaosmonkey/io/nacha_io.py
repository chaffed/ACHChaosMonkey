from sqlalchemy.orm import Session

from ..db import models
from ..db.ingest import ingest_file_record
from ..nacha.parser import parse_file
from ..nacha.records import AchFileRecord, Batch, BatchHeader, EntryDetail, FileHeader
from ..nacha.writer import assemble_file


def export_nacha(db_file: models.AchFile) -> str:
    """Rebuilds an AchFileRecord from the DB and re-serializes it to NACHA text.

    Batch control totals are forced back to exactly what's stored on each
    AchBatch (rather than recomputed from the current entries), so a file
    that was ingested with deliberately corrupted control totals (the
    bad_control_totals chaos strategy) round-trips losslessly instead of
    being silently "healed" by fresh recomputation.
    """
    file_header = FileHeader(
        immediate_destination=db_file.immediate_destination,
        immediate_origin=db_file.immediate_origin,
        immediate_destination_name=db_file.immediate_destination_name,
        immediate_origin_name=db_file.immediate_origin_name,
        file_creation_date=db_file.creation_date,
        file_creation_time=db_file.creation_time,
        file_id_modifier=db_file.file_id_modifier,
    )

    batches = []
    batch_control_overrides = {}
    for batch in db_file.batches:
        bh = BatchHeader(
            company_name=batch.company_name,
            company_identification=batch.company_identification,
            sec_code=batch.sec_code,
            company_entry_description=batch.company_entry_description,
            effective_entry_date=batch.effective_entry_date,
            originating_dfi=batch.originating_dfi,
            batch_number=batch.batch_number,
        )
        entries = [
            EntryDetail(
                transaction_code=entry.transaction_code,
                receiving_dfi_routing=entry.receiving_dfi_routing,
                dfi_account_number=entry.dfi_account_number,
                amount_cents=entry.amount_cents,
                individual_name=entry.individual_name,
                individual_id=entry.individual_id,
                discretionary_data=entry.discretionary_data,
                addenda_indicator=entry.addenda_indicator,
                trace_number=entry.trace_number,
            )
            for entry in batch.entries
        ]
        batches.append(Batch(header=bh, entries=entries))
        batch_control_overrides[batch.batch_number] = {
            "entry_addenda_count": batch.entry_addenda_count,
            "entry_hash": batch.entry_hash,
            "total_debit_amount": batch.total_debit_amount,
            "total_credit_amount": batch.total_credit_amount,
        }

    file_record = AchFileRecord(header=file_header, batches=batches)
    return assemble_file(file_record, overrides={"batch_control": batch_control_overrides})


def import_nacha(session: Session, text: str, original_filename: str | None = None) -> models.AchFile:
    file_record = parse_file(text)
    return ingest_file_record(session, file_record, source=models.SOURCE_IMPORTED, original_filename=original_filename)
