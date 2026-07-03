import math

from .exceptions import FieldLengthError
from .fields import (
    ADDENDA_FIELDS,
    BATCH_CONTROL_FIELDS,
    BATCH_HEADER_FIELDS,
    CREDIT_TRANSACTION_CODES,
    DEBIT_TRANSACTION_CODES,
    ENTRY_DETAIL_FIELDS,
    FILE_CONTROL_FIELDS,
    FILE_HEADER_FIELDS,
    RECORD_LENGTH,
    FieldKind,
    FieldSpec,
)
from .records import AchFileRecord, Addenda, Batch, BatchControl, BatchHeader, EntryDetail, FileControl, FileHeader

FILLER_LINE = "9" * RECORD_LENGTH


def format_field(spec: FieldSpec, value) -> str:
    text = "" if value is None else str(value)
    if len(text) > spec.length:
        raise FieldLengthError(f"{spec.name}: value '{text}' exceeds length {spec.length}")
    return text.ljust(spec.length, spec.pad_char) if spec.justify == "left" else text.rjust(spec.length, spec.pad_char)


def format_line(specs: list[FieldSpec], values: dict) -> str:
    line = "".join(format_field(spec, values.get(spec.name)) for spec in specs)
    assert len(line) == RECORD_LENGTH
    return line


def write_file_header(fh: FileHeader) -> str:
    values = {
        "record_type_code": "1",
        "priority_code": fh.priority_code,
        "immediate_destination": fh.immediate_destination,
        "immediate_origin": fh.immediate_origin,
        "file_creation_date": fh.file_creation_date,
        "file_creation_time": fh.file_creation_time,
        "file_id_modifier": fh.file_id_modifier,
        "record_size": fh.record_size,
        "blocking_factor": fh.blocking_factor,
        "format_code": fh.format_code,
        "immediate_destination_name": fh.immediate_destination_name,
        "immediate_origin_name": fh.immediate_origin_name,
        "reference_code": fh.reference_code,
    }
    return format_line(FILE_HEADER_FIELDS, values)


def write_batch_header(bh: BatchHeader) -> str:
    values = {
        "record_type_code": "5",
        "service_class_code": bh.service_class_code,
        "company_name": bh.company_name,
        "company_discretionary_data": bh.company_discretionary_data,
        "company_identification": bh.company_identification,
        "sec_code": bh.sec_code,
        "company_entry_description": bh.company_entry_description,
        "company_descriptive_date": bh.company_descriptive_date,
        "effective_entry_date": bh.effective_entry_date,
        "settlement_date": bh.settlement_date,
        "originator_status_code": bh.originator_status_code,
        "originating_dfi": bh.originating_dfi,
        "batch_number": bh.batch_number,
    }
    return format_line(BATCH_HEADER_FIELDS, values)


def write_entry_detail(entry: EntryDetail) -> str:
    routing = entry.receiving_dfi_routing
    prefix, check_digit = routing[:8], routing[8:9]
    values = {
        "record_type_code": "6",
        "transaction_code": entry.transaction_code,
        "rdfi_routing": prefix,
        "check_digit": check_digit,
        "dfi_account_number": entry.dfi_account_number,
        "amount": entry.amount_cents,
        "individual_id": entry.individual_id,
        "individual_name": entry.individual_name,
        "discretionary_data": entry.discretionary_data,
        "addenda_indicator": entry.addenda_indicator,
        "trace_number": entry.trace_number,
    }
    return format_line(ENTRY_DETAIL_FIELDS, values)


def write_addenda(addenda: Addenda) -> str:
    values = {
        "record_type_code": "7",
        "addenda_type_code": addenda.addenda_type_code,
        "payment_related_info": addenda.payment_related_info,
        "addenda_sequence_number": addenda.addenda_sequence_number,
        "entry_detail_sequence_number": addenda.entry_detail_sequence_number,
    }
    return format_line(ADDENDA_FIELDS, values)


def write_batch_control(bc: BatchControl) -> str:
    values = {
        "record_type_code": "8",
        "service_class_code": bc.service_class_code,
        "entry_addenda_count": bc.entry_addenda_count,
        "entry_hash": bc.entry_hash,
        "total_debit_amount": bc.total_debit_amount,
        "total_credit_amount": bc.total_credit_amount,
        "company_identification": bc.company_identification,
        "message_authentication_code": bc.message_authentication_code,
        "reserved": bc.reserved,
        "originating_dfi": bc.originating_dfi,
        "batch_number": bc.batch_number,
    }
    return format_line(BATCH_CONTROL_FIELDS, values)


def write_file_control(fc: FileControl) -> str:
    values = {
        "record_type_code": "9",
        "batch_count": fc.batch_count,
        "block_count": fc.block_count,
        "entry_addenda_count": fc.entry_addenda_count,
        "entry_hash": fc.entry_hash,
        "total_debit_amount": fc.total_debit_amount,
        "total_credit_amount": fc.total_credit_amount,
        "reserved": fc.reserved,
    }
    return format_line(FILE_CONTROL_FIELDS, values)


def compute_entry_hash(routing_prefixes: list[str]) -> int:
    return sum(int(prefix) for prefix in routing_prefixes) % (10**10)


def compute_batch_control(batch: Batch, overrides: dict | None = None) -> BatchControl:
    entries = batch.entries
    entry_addenda_count = sum(1 + len(e.addenda) for e in entries)
    entry_hash = compute_entry_hash([e.receiving_dfi_routing[:8] for e in entries])
    total_debit = sum(e.amount_cents for e in entries if e.transaction_code in DEBIT_TRANSACTION_CODES)
    total_credit = sum(e.amount_cents for e in entries if e.transaction_code in CREDIT_TRANSACTION_CODES)
    bc = BatchControl(
        service_class_code=batch.header.service_class_code,
        entry_addenda_count=entry_addenda_count,
        entry_hash=entry_hash,
        total_debit_amount=total_debit,
        total_credit_amount=total_credit,
        company_identification=batch.header.company_identification,
        originating_dfi=batch.header.originating_dfi,
        batch_number=batch.header.batch_number,
    )
    for key, value in (overrides or {}).items():
        setattr(bc, key, value)
    return bc


def compute_file_control(file_record: AchFileRecord, batch_controls: list[BatchControl], overrides: dict | None = None) -> FileControl:
    fc = FileControl(
        batch_count=len(file_record.batches),
        block_count=0,
        entry_addenda_count=sum(bc.entry_addenda_count for bc in batch_controls),
        entry_hash=sum(bc.entry_hash for bc in batch_controls) % (10**10),
        total_debit_amount=sum(bc.total_debit_amount for bc in batch_controls),
        total_credit_amount=sum(bc.total_credit_amount for bc in batch_controls),
    )
    for key, value in (overrides or {}).items():
        setattr(fc, key, value)
    return fc


def assemble_file(file_record: AchFileRecord, overrides: dict | None = None) -> str:
    """Serialize a full AchFileRecord to NACHA text, computing batch/file
    control totals from the actual record set unless overridden (the seam
    chaos strategies use to deliberately corrupt control totals)."""
    overrides = overrides or {}
    batch_control_overrides = overrides.get("batch_control", {})
    file_control_overrides = overrides.get("file_control", {})

    lines = [write_file_header(file_record.header)]
    batch_controls = []
    for batch in file_record.batches:
        lines.append(write_batch_header(batch.header))
        for entry in batch.entries:
            lines.append(write_entry_detail(entry))
            for addenda in entry.addenda:
                lines.append(write_addenda(addenda))
        bc = compute_batch_control(batch, batch_control_overrides.get(batch.header.batch_number))
        batch.control = bc
        batch_controls.append(bc)
        lines.append(write_batch_control(bc))

    fc = compute_file_control(file_record, batch_controls, file_control_overrides)
    fc.block_count = math.ceil((len(lines) + 1) / 10)
    if "block_count" in file_control_overrides:
        fc.block_count = file_control_overrides["block_count"]
    file_record.control = fc
    lines.append(write_file_control(fc))

    while len(lines) % 10 != 0:
        lines.append(FILLER_LINE)

    return "\n".join(lines) + "\n"
