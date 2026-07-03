from sqlalchemy.orm import Session

from ..nacha.records import AchFileRecord
from . import models


def ingest_file_record(
    session: Session,
    file_record: AchFileRecord,
    source: str,
    original_filename: str | None = None,
    labels: dict[tuple[int, int], object] | None = None,
) -> models.AchFile:
    """Shared ingestion path used by both the generator and NACHA/CSV/XLSX
    importers, so all three input sources land in the same schema.

    `labels` maps (batch_index, entry_index) -> EntryLabel and is only
    populated by the generator, which has ground truth; importers leave it
    None so imported entries carry unknown (False/None) ground truth.
    """
    labels = labels or {}
    fh = file_record.header
    db_file = models.AchFile(
        file_id_modifier=fh.file_id_modifier,
        immediate_origin=fh.immediate_origin,
        immediate_destination=fh.immediate_destination,
        immediate_origin_name=fh.immediate_origin_name,
        immediate_destination_name=fh.immediate_destination_name,
        creation_date=fh.file_creation_date,
        creation_time=fh.file_creation_time,
        source=source,
        original_filename=original_filename,
    )

    for batch_idx, batch in enumerate(file_record.batches):
        bh = batch.header
        control = batch.control
        db_batch = models.AchBatch(
            batch_number=bh.batch_number,
            service_class_code=bh.service_class_code,
            company_name=bh.company_name,
            company_identification=bh.company_identification,
            sec_code=bh.sec_code,
            company_entry_description=bh.company_entry_description,
            effective_entry_date=bh.effective_entry_date,
            originating_dfi=bh.originating_dfi,
            entry_addenda_count=control.entry_addenda_count if control else len(batch.entries),
            entry_hash=control.entry_hash if control else 0,
            total_debit_amount=control.total_debit_amount if control else 0,
            total_credit_amount=control.total_credit_amount if control else 0,
        )

        for entry_idx, entry in enumerate(batch.entries):
            label = labels.get((batch_idx, entry_idx))
            db_entry = models.AchEntry(
                sequence_in_batch=entry_idx + 1,
                transaction_code=entry.transaction_code,
                receiving_dfi_routing=entry.receiving_dfi_routing,
                dfi_account_number=entry.dfi_account_number,
                amount_cents=entry.amount_cents,
                individual_id=entry.individual_id,
                individual_name=entry.individual_name,
                discretionary_data=entry.discretionary_data,
                addenda_indicator=entry.addenda_indicator,
                trace_number=entry.trace_number,
                is_fraud=bool(label and label.is_fraud),
                fraud_type=label.fraud_type if label else None,
                is_miscoded=bool(label and label.is_miscoded),
                miscode_type=label.miscode_type if label else None,
                chaos_injected=label is not None,
            )
            for addenda in entry.addenda:
                db_entry.addenda.append(
                    models.AchAddenda(
                        addenda_type_code=addenda.addenda_type_code,
                        payment_related_info=addenda.payment_related_info,
                        addenda_sequence_number=addenda.addenda_sequence_number,
                    )
                )
            db_batch.entries.append(db_entry)

        db_file.batches.append(db_batch)

    session.add(db_file)
    session.flush()
    return db_file
