from .exceptions import RecordParseError
from .fields import (
    ADDENDA_FIELDS,
    BATCH_CONTROL_FIELDS,
    BATCH_HEADER_FIELDS,
    ENTRY_DETAIL_FIELDS,
    FILE_CONTROL_FIELDS,
    FILE_HEADER_FIELDS,
    RECORD_LENGTH,
    FieldKind,
    FieldSpec,
)
from .records import AchFileRecord, Addenda, Batch, BatchControl, BatchHeader, EntryDetail, FileControl, FileHeader
from .writer import FILLER_LINE


def parse_field(line: str, spec: FieldSpec) -> str:
    raw = line[spec.start - 1 : spec.end]
    return raw.rstrip() if spec.kind == FieldKind.ALPHA else raw


def parse_fields(line: str, specs: list[FieldSpec]) -> dict:
    return {spec.name: parse_field(line, spec) for spec in specs}


def parse_file_header(line: str) -> FileHeader:
    v = parse_fields(line, FILE_HEADER_FIELDS)
    return FileHeader(
        immediate_destination=v["immediate_destination"].strip(),
        immediate_origin=v["immediate_origin"].strip(),
        immediate_destination_name=v["immediate_destination_name"],
        immediate_origin_name=v["immediate_origin_name"],
        file_creation_date=v["file_creation_date"],
        file_creation_time=v["file_creation_time"],
        file_id_modifier=v["file_id_modifier"],
        reference_code=v["reference_code"],
        priority_code=v["priority_code"],
        record_size=v["record_size"],
        blocking_factor=v["blocking_factor"],
        format_code=v["format_code"],
    )


def parse_batch_header(line: str) -> BatchHeader:
    v = parse_fields(line, BATCH_HEADER_FIELDS)
    return BatchHeader(
        company_name=v["company_name"],
        company_identification=v["company_identification"],
        sec_code=v["sec_code"],
        company_entry_description=v["company_entry_description"],
        effective_entry_date=v["effective_entry_date"],
        originating_dfi=v["originating_dfi"],
        batch_number=int(v["batch_number"]),
        service_class_code=v["service_class_code"],
        company_discretionary_data=v["company_discretionary_data"],
        company_descriptive_date=v["company_descriptive_date"],
        settlement_date=v["settlement_date"],
        originator_status_code=v["originator_status_code"],
    )


def parse_entry_detail(line: str) -> EntryDetail:
    v = parse_fields(line, ENTRY_DETAIL_FIELDS)
    return EntryDetail(
        transaction_code=v["transaction_code"],
        receiving_dfi_routing=v["rdfi_routing"] + v["check_digit"],
        dfi_account_number=v["dfi_account_number"],
        amount_cents=int(v["amount"]),
        individual_name=v["individual_name"],
        individual_id=v["individual_id"],
        discretionary_data=v["discretionary_data"],
        addenda_indicator=v["addenda_indicator"],
        trace_number=v["trace_number"],
    )


def parse_addenda(line: str) -> Addenda:
    v = parse_fields(line, ADDENDA_FIELDS)
    return Addenda(
        payment_related_info=v["payment_related_info"],
        addenda_sequence_number=int(v["addenda_sequence_number"]),
        entry_detail_sequence_number=int(v["entry_detail_sequence_number"]),
        addenda_type_code=v["addenda_type_code"],
    )


def parse_batch_control(line: str) -> BatchControl:
    v = parse_fields(line, BATCH_CONTROL_FIELDS)
    return BatchControl(
        service_class_code=v["service_class_code"],
        entry_addenda_count=int(v["entry_addenda_count"]),
        entry_hash=int(v["entry_hash"]),
        total_debit_amount=int(v["total_debit_amount"]),
        total_credit_amount=int(v["total_credit_amount"]),
        company_identification=v["company_identification"],
        originating_dfi=v["originating_dfi"],
        batch_number=int(v["batch_number"]),
        message_authentication_code=v["message_authentication_code"],
        reserved=v["reserved"],
    )


def parse_file_control(line: str) -> FileControl:
    v = parse_fields(line, FILE_CONTROL_FIELDS)
    return FileControl(
        batch_count=int(v["batch_count"]),
        block_count=int(v["block_count"]),
        entry_addenda_count=int(v["entry_addenda_count"]),
        entry_hash=int(v["entry_hash"]),
        total_debit_amount=int(v["total_debit_amount"]),
        total_credit_amount=int(v["total_credit_amount"]),
        reserved=v["reserved"],
    )


def parse_file(text: str) -> AchFileRecord:
    raw_lines = [line for line in text.replace("\r\n", "\n").split("\n") if line != ""]

    file_header = None
    file_control = None
    batches: list[Batch] = []
    current_batch: Batch | None = None
    current_entry: EntryDetail | None = None

    for lineno, line in enumerate(raw_lines, start=1):
        if len(line) != RECORD_LENGTH:
            raise RecordParseError(f"line {lineno}: expected {RECORD_LENGTH} chars, got {len(line)}")

        record_type = line[0]
        if record_type == "1":
            file_header = parse_file_header(line)
        elif record_type == "5":
            current_batch = Batch(header=parse_batch_header(line))
            batches.append(current_batch)
            current_entry = None
        elif record_type == "6":
            if current_batch is None:
                raise RecordParseError(f"line {lineno}: entry detail record before any batch header")
            current_entry = parse_entry_detail(line)
            current_batch.entries.append(current_entry)
        elif record_type == "7":
            if current_entry is None:
                raise RecordParseError(f"line {lineno}: addenda record before any entry detail")
            current_entry.addenda.append(parse_addenda(line))
        elif record_type == "8":
            if current_batch is None:
                raise RecordParseError(f"line {lineno}: batch control record before any batch header")
            current_batch.control = parse_batch_control(line)
        elif record_type == "9":
            if line == FILLER_LINE:
                continue
            file_control = parse_file_control(line)
        else:
            raise RecordParseError(f"line {lineno}: unknown record type code '{record_type}'")

    if file_header is None:
        raise RecordParseError("file is missing a file header record")

    return AchFileRecord(header=file_header, batches=batches, control=file_control)
