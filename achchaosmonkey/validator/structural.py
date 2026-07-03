"""NACHA structural / business-rule validation, operating on persisted ORM rows."""

from dataclasses import dataclass

from ..db.models import AchBatch, AchEntry
from ..nacha.checksum import is_valid_routing_number
from ..nacha.fields import CREDIT_TRANSACTION_CODES, DEBIT_TRANSACTION_CODES, VALID_SEC_CODES, VALID_TRANSACTION_CODES


@dataclass
class RuleViolation:
    rule_id: str
    message: str
    severity: str  # "error" | "warning"


def check_routing_checksum(entry: AchEntry) -> RuleViolation | None:
    if not is_valid_routing_number(entry.receiving_dfi_routing):
        return RuleViolation(
            "routing_checksum", f"Invalid ABA check digit for routing {entry.receiving_dfi_routing}", "error"
        )
    return None


def check_valid_transaction_code(entry: AchEntry) -> RuleViolation | None:
    if entry.transaction_code not in VALID_TRANSACTION_CODES:
        return RuleViolation("valid_transaction_code", f"Unknown transaction code {entry.transaction_code}", "error")
    return None


def check_ascii_name(entry: AchEntry) -> RuleViolation | None:
    if not entry.individual_name.isascii():
        return RuleViolation("ascii_name_field", "Individual name contains non-ASCII characters", "error")
    return None


def check_field_lengths(entry: AchEntry) -> RuleViolation | None:
    if len(entry.individual_name) > 22 or len(entry.dfi_account_number) > 17 or len(entry.receiving_dfi_routing) != 9:
        return RuleViolation("field_length", "One or more fields exceed their fixed-width NACHA slot", "error")
    return None


ENTRY_RULES = [check_routing_checksum, check_valid_transaction_code, check_ascii_name, check_field_lengths]


def validate_entry(entry: AchEntry) -> list[RuleViolation]:
    return [violation for rule in ENTRY_RULES if (violation := rule(entry)) is not None]


def check_valid_sec_code(batch: AchBatch) -> RuleViolation | None:
    if batch.sec_code not in VALID_SEC_CODES:
        return RuleViolation("valid_sec_code", f"Unrecognized SEC code {batch.sec_code}", "error")
    return None


def check_batch_entry_hash(batch: AchBatch) -> RuleViolation | None:
    expected = sum(int(e.receiving_dfi_routing[:8]) for e in batch.entries) % (10**10)
    if expected != batch.entry_hash:
        return RuleViolation(
            "batch_entry_hash", f"Batch control entry hash {batch.entry_hash} != recomputed {expected}", "error"
        )
    return None


def check_batch_totals(batch: AchBatch) -> RuleViolation | None:
    expected_debit = sum(e.amount_cents for e in batch.entries if e.transaction_code in DEBIT_TRANSACTION_CODES)
    expected_credit = sum(e.amount_cents for e in batch.entries if e.transaction_code in CREDIT_TRANSACTION_CODES)
    if expected_debit != batch.total_debit_amount or expected_credit != batch.total_credit_amount:
        return RuleViolation(
            "batch_control_totals", "Batch control debit/credit totals do not match recomputed totals", "error"
        )
    return None


def check_batch_entry_count(batch: AchBatch) -> RuleViolation | None:
    expected = sum(1 + len(e.addenda) for e in batch.entries)
    if expected != batch.entry_addenda_count:
        return RuleViolation(
            "batch_entry_count", f"Batch entry/addenda count {batch.entry_addenda_count} != recomputed {expected}", "error"
        )
    return None


BATCH_RULES = [check_valid_sec_code, check_batch_entry_hash, check_batch_totals, check_batch_entry_count]


def check_duplicate_trace_numbers(batch: AchBatch) -> dict[int, list[RuleViolation]]:
    by_trace: dict[str, list[AchEntry]] = {}
    for entry in batch.entries:
        by_trace.setdefault(entry.trace_number, []).append(entry)

    result: dict[int, list[RuleViolation]] = {}
    for trace, entries in by_trace.items():
        if len(entries) > 1:
            for entry in entries:
                result.setdefault(entry.id, []).append(
                    RuleViolation("duplicate_trace_number", f"Trace number {trace} duplicated within batch", "error")
                )
    return result


def validate_batch(batch: AchBatch) -> dict[int, list[RuleViolation]]:
    """Returns entry_id -> violations, combining whole-batch rules (applied to
    every entry in the batch) with per-entry and per-entry-pair rules."""
    whole_batch_violations = [violation for rule in BATCH_RULES if (violation := rule(batch)) is not None]
    duplicate_violations = check_duplicate_trace_numbers(batch)

    result: dict[int, list[RuleViolation]] = {}
    for entry in batch.entries:
        result[entry.id] = validate_entry(entry) + whole_batch_violations + duplicate_violations.get(entry.id, [])
    return result
