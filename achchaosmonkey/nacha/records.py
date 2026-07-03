from dataclasses import dataclass, field


@dataclass
class FileHeader:
    immediate_destination: str
    immediate_origin: str
    immediate_destination_name: str = ""
    immediate_origin_name: str = ""
    file_creation_date: str = ""
    file_creation_time: str = ""
    file_id_modifier: str = "A"
    reference_code: str = ""
    priority_code: str = "01"
    record_size: str = "094"
    blocking_factor: str = "10"
    format_code: str = "1"


@dataclass
class BatchHeader:
    company_name: str
    company_identification: str
    sec_code: str
    company_entry_description: str
    effective_entry_date: str
    originating_dfi: str
    batch_number: int = 1
    service_class_code: str = "200"
    company_discretionary_data: str = ""
    company_descriptive_date: str = ""
    settlement_date: str = ""
    originator_status_code: str = "1"


@dataclass
class Addenda:
    payment_related_info: str = ""
    addenda_sequence_number: int = 1
    entry_detail_sequence_number: int = 1
    addenda_type_code: str = "05"


@dataclass
class EntryDetail:
    transaction_code: str
    receiving_dfi_routing: str  # full 9-digit routing number (8-digit prefix + check digit)
    dfi_account_number: str
    amount_cents: int
    individual_name: str
    individual_id: str = ""
    discretionary_data: str = ""
    addenda_indicator: str = "0"
    trace_number: str = ""
    addenda: list[Addenda] = field(default_factory=list)


@dataclass
class BatchControl:
    service_class_code: str
    entry_addenda_count: int
    entry_hash: int
    total_debit_amount: int
    total_credit_amount: int
    company_identification: str
    originating_dfi: str
    batch_number: int = 1
    message_authentication_code: str = ""
    reserved: str = ""


@dataclass
class FileControl:
    batch_count: int
    block_count: int
    entry_addenda_count: int
    entry_hash: int
    total_debit_amount: int
    total_credit_amount: int
    reserved: str = ""


@dataclass
class Batch:
    header: BatchHeader
    entries: list[EntryDetail] = field(default_factory=list)
    control: BatchControl | None = None


@dataclass
class AchFileRecord:
    header: FileHeader
    batches: list[Batch] = field(default_factory=list)
    control: FileControl | None = None
