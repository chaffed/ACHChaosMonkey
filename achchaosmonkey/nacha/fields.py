"""Single source of truth for NACHA fixed-width (94-char) record layouts.

Field positions are 1-indexed and match the standard NACHA Operating Rules
layout used across File Header (1), Batch Header (5), Entry Detail (6),
Addenda (7), Batch Control (8), and File Control (9) records.
"""

from dataclasses import dataclass
from enum import Enum

RECORD_LENGTH = 94


class FieldKind(str, Enum):
    ALPHA = "alpha"  # alphanumeric, left-justified, space-padded
    NUMERIC = "numeric"  # numeric, right-justified, zero-padded


@dataclass(frozen=True)
class FieldSpec:
    name: str
    start: int
    length: int
    kind: FieldKind
    justify: str = ""
    pad_char: str = ""

    def __post_init__(self):
        if not self.justify:
            object.__setattr__(self, "justify", "left" if self.kind == FieldKind.ALPHA else "right")
        if not self.pad_char:
            object.__setattr__(self, "pad_char", " " if self.kind == FieldKind.ALPHA else "0")

    @property
    def end(self) -> int:
        return self.start + self.length - 1


def _check_specs(specs: list[FieldSpec]) -> list[FieldSpec]:
    pos = 1
    for spec in specs:
        if spec.start != pos:
            raise ValueError(f"{spec.name} expected to start at {pos}, got {spec.start}")
        pos = spec.end + 1
    if pos - 1 != RECORD_LENGTH:
        raise ValueError(f"record layout totals {pos - 1} chars, expected {RECORD_LENGTH}")
    return specs


A = FieldKind.ALPHA
N = FieldKind.NUMERIC

FILE_HEADER_FIELDS = _check_specs([
    FieldSpec("record_type_code", 1, 1, A),
    FieldSpec("priority_code", 2, 2, N),
    FieldSpec("immediate_destination", 4, 10, A, justify="right", pad_char=" "),
    FieldSpec("immediate_origin", 14, 10, A, justify="right", pad_char=" "),
    FieldSpec("file_creation_date", 24, 6, N),
    FieldSpec("file_creation_time", 30, 4, N),
    FieldSpec("file_id_modifier", 34, 1, A),
    FieldSpec("record_size", 35, 3, N),
    FieldSpec("blocking_factor", 38, 2, N),
    FieldSpec("format_code", 40, 1, N),
    FieldSpec("immediate_destination_name", 41, 23, A),
    FieldSpec("immediate_origin_name", 64, 23, A),
    FieldSpec("reference_code", 87, 8, A),
])

BATCH_HEADER_FIELDS = _check_specs([
    FieldSpec("record_type_code", 1, 1, A),
    FieldSpec("service_class_code", 2, 3, N),
    FieldSpec("company_name", 5, 16, A),
    FieldSpec("company_discretionary_data", 21, 20, A),
    FieldSpec("company_identification", 41, 10, A),
    FieldSpec("sec_code", 51, 3, A),
    FieldSpec("company_entry_description", 54, 10, A),
    FieldSpec("company_descriptive_date", 64, 6, A),
    FieldSpec("effective_entry_date", 70, 6, N),
    FieldSpec("settlement_date", 76, 3, A),
    FieldSpec("originator_status_code", 79, 1, A),
    FieldSpec("originating_dfi", 80, 8, N),
    FieldSpec("batch_number", 88, 7, N),
])

ENTRY_DETAIL_FIELDS = _check_specs([
    FieldSpec("record_type_code", 1, 1, A),
    FieldSpec("transaction_code", 2, 2, N),
    FieldSpec("rdfi_routing", 4, 8, N),
    FieldSpec("check_digit", 12, 1, N),
    FieldSpec("dfi_account_number", 13, 17, A),
    FieldSpec("amount", 30, 10, N),
    FieldSpec("individual_id", 40, 15, A),
    FieldSpec("individual_name", 55, 22, A),
    FieldSpec("discretionary_data", 77, 2, A),
    FieldSpec("addenda_indicator", 79, 1, N),
    FieldSpec("trace_number", 80, 15, N),
])

ADDENDA_FIELDS = _check_specs([
    FieldSpec("record_type_code", 1, 1, A),
    FieldSpec("addenda_type_code", 2, 2, A),
    FieldSpec("payment_related_info", 4, 80, A),
    FieldSpec("addenda_sequence_number", 84, 4, N),
    FieldSpec("entry_detail_sequence_number", 88, 7, N),
])

BATCH_CONTROL_FIELDS = _check_specs([
    FieldSpec("record_type_code", 1, 1, A),
    FieldSpec("service_class_code", 2, 3, N),
    FieldSpec("entry_addenda_count", 5, 6, N),
    FieldSpec("entry_hash", 11, 10, N),
    FieldSpec("total_debit_amount", 21, 12, N),
    FieldSpec("total_credit_amount", 33, 12, N),
    FieldSpec("company_identification", 45, 10, A),
    FieldSpec("message_authentication_code", 55, 19, A),
    FieldSpec("reserved", 74, 6, A),
    FieldSpec("originating_dfi", 80, 8, N),
    FieldSpec("batch_number", 88, 7, N),
])

FILE_CONTROL_FIELDS = _check_specs([
    FieldSpec("record_type_code", 1, 1, A),
    FieldSpec("batch_count", 2, 6, N),
    FieldSpec("block_count", 8, 6, N),
    FieldSpec("entry_addenda_count", 14, 8, N),
    FieldSpec("entry_hash", 22, 10, N),
    FieldSpec("total_debit_amount", 32, 12, N),
    FieldSpec("total_credit_amount", 44, 12, N),
    FieldSpec("reserved", 56, 39, A),
])


class TransactionCode(str, Enum):
    CHECKING_CREDIT = "22"
    CHECKING_PRENOTE_CREDIT = "23"
    CHECKING_DEBIT = "27"
    CHECKING_PRENOTE_DEBIT = "28"
    SAVINGS_CREDIT = "32"
    SAVINGS_PRENOTE_CREDIT = "33"
    SAVINGS_DEBIT = "37"
    SAVINGS_PRENOTE_DEBIT = "38"


CREDIT_TRANSACTION_CODES = {"22", "23", "32", "33"}
DEBIT_TRANSACTION_CODES = {"27", "28", "37", "38"}
VALID_TRANSACTION_CODES = CREDIT_TRANSACTION_CODES | DEBIT_TRANSACTION_CODES
CHECKING_TRANSACTION_CODES = {"22", "23", "27", "28"}
SAVINGS_TRANSACTION_CODES = {"32", "33", "37", "38"}


class SECCode(str, Enum):
    PPD = "PPD"
    CCD = "CCD"
    WEB = "WEB"
    TEL = "TEL"
    CTX = "CTX"


VALID_SEC_CODES = {code.value for code in SECCode}
