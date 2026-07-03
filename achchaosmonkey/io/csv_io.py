import io as stdlib_io

import pandas as pd
from sqlalchemy.orm import Session

from ..db import models
from ..db.ingest import ingest_file_record
from ..generator.strategies import EntryLabel
from ..nacha.records import AchFileRecord, Batch, BatchHeader, EntryDetail, FileHeader
from ..nacha.writer import assemble_file

# One row per entry; batch/file fields repeat across the rows that belong to
# them. This is an entry-centric convenience format (see io/nacha_io.py for
# the only fully lossless round trip of file/batch/control-record fidelity).
FLAT_COLUMNS = [
    "immediate_origin",
    "immediate_destination",
    "immediate_origin_name",
    "immediate_destination_name",
    "file_creation_date",
    "file_creation_time",
    "file_id_modifier",
    "batch_number",
    "company_name",
    "company_identification",
    "sec_code",
    "company_entry_description",
    "effective_entry_date",
    "originating_dfi",
    "transaction_code",
    "receiving_dfi_routing",
    "dfi_account_number",
    "amount_cents",
    "individual_id",
    "individual_name",
    "discretionary_data",
    "trace_number",
    "is_fraud",
    "fraud_type",
    "is_miscoded",
    "miscode_type",
]


def build_dataframe(db_file: models.AchFile) -> pd.DataFrame:
    rows = []
    for batch in db_file.batches:
        for entry in batch.entries:
            rows.append(
                {
                    "immediate_origin": db_file.immediate_origin,
                    "immediate_destination": db_file.immediate_destination,
                    "immediate_origin_name": db_file.immediate_origin_name,
                    "immediate_destination_name": db_file.immediate_destination_name,
                    "file_creation_date": db_file.creation_date,
                    "file_creation_time": db_file.creation_time,
                    "file_id_modifier": db_file.file_id_modifier,
                    "batch_number": batch.batch_number,
                    "company_name": batch.company_name,
                    "company_identification": batch.company_identification,
                    "sec_code": batch.sec_code,
                    "company_entry_description": batch.company_entry_description,
                    "effective_entry_date": batch.effective_entry_date,
                    "originating_dfi": batch.originating_dfi,
                    "transaction_code": entry.transaction_code,
                    "receiving_dfi_routing": entry.receiving_dfi_routing,
                    "dfi_account_number": entry.dfi_account_number,
                    "amount_cents": entry.amount_cents,
                    "individual_id": entry.individual_id,
                    "individual_name": entry.individual_name,
                    "discretionary_data": entry.discretionary_data,
                    "trace_number": entry.trace_number,
                    "is_fraud": entry.is_fraud,
                    "fraud_type": entry.fraud_type,
                    "is_miscoded": entry.is_miscoded,
                    "miscode_type": entry.miscode_type,
                }
            )
    return pd.DataFrame(rows, columns=FLAT_COLUMNS)


def dataframe_to_file_record(df: pd.DataFrame) -> tuple[AchFileRecord, dict[tuple[int, int], EntryLabel]]:
    if df.empty:
        raise ValueError("no rows to import")

    first = df.iloc[0]
    file_header = FileHeader(
        immediate_destination=_str(first, "immediate_destination", "000000000"),
        immediate_origin=_str(first, "immediate_origin", "000000000"),
        immediate_destination_name=_str(first, "immediate_destination_name", ""),
        immediate_origin_name=_str(first, "immediate_origin_name", ""),
        file_creation_date=_str(first, "file_creation_date", ""),
        file_creation_time=_str(first, "file_creation_time", ""),
        file_id_modifier=_str(first, "file_id_modifier", "A"),
    )

    batches: dict[int, Batch] = {}
    batch_idx_by_number: dict[int, int] = {}
    labels: dict[tuple[int, int], EntryLabel] = {}

    for _, row in df.iterrows():
        batch_number = int(row.get("batch_number") or 1)
        if batch_number not in batches:
            batch_idx_by_number[batch_number] = len(batches)
            batches[batch_number] = Batch(
                header=BatchHeader(
                    company_name=_str(row, "company_name", ""),
                    company_identification=_str(row, "company_identification", ""),
                    sec_code=_str(row, "sec_code", "PPD"),
                    company_entry_description=_str(row, "company_entry_description", ""),
                    effective_entry_date=_str(row, "effective_entry_date", ""),
                    originating_dfi=_str(row, "originating_dfi", ""),
                    batch_number=batch_number,
                )
            )
        batch = batches[batch_number]
        entry = EntryDetail(
            transaction_code=_str(row, "transaction_code", "22"),
            receiving_dfi_routing=_str(row, "receiving_dfi_routing", ""),
            dfi_account_number=_str(row, "dfi_account_number", ""),
            amount_cents=int(row.get("amount_cents") or 0),
            individual_name=_str(row, "individual_name", ""),
            individual_id=_str(row, "individual_id", ""),
            discretionary_data=_str(row, "discretionary_data", ""),
            trace_number=_str(row, "trace_number", ""),
        )
        batch.entries.append(entry)
        entry_idx = len(batch.entries) - 1

        is_fraud = bool(row.get("is_fraud", False))
        is_miscoded = bool(row.get("is_miscoded", False))
        if is_fraud or is_miscoded:
            labels[(batch_idx_by_number[batch_number], entry_idx)] = EntryLabel(
                is_fraud=is_fraud,
                fraud_type=_str_or_none(row, "fraud_type"),
                is_miscoded=is_miscoded,
                miscode_type=_str_or_none(row, "miscode_type"),
            )

    file_record = AchFileRecord(header=file_header, batches=list(batches.values()))
    return file_record, labels


def _str(row, key: str, default: str) -> str:
    value = row.get(key, default)
    return default if pd.isna(value) else str(value)


def _str_or_none(row, key: str) -> str | None:
    value = row.get(key)
    return None if value is None or pd.isna(value) else str(value)


def export_csv(db_file: models.AchFile) -> str:
    return build_dataframe(db_file).to_csv(index=False)


def import_csv(session: Session, csv_text: str, original_filename: str | None = None) -> models.AchFile:
    df = pd.read_csv(stdlib_io.StringIO(csv_text))
    file_record, labels = dataframe_to_file_record(df)
    assemble_file(file_record)  # computes control totals from the imported entries
    return ingest_file_record(
        session, file_record, source=models.SOURCE_IMPORTED, original_filename=original_filename, labels=labels
    )
