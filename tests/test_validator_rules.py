from achchaosmonkey.db.models import AchBatch, AchEntry
from achchaosmonkey.validator import structural

ROUTING_PREFIX = "02100002"
ROUTING = "021000021"  # valid check digit for prefix 02100002


def make_entry(entry_id: int, **overrides) -> AchEntry:
    defaults = dict(
        id=entry_id,
        sequence_in_batch=entry_id,
        transaction_code="22",
        receiving_dfi_routing=ROUTING,
        dfi_account_number="000123456789",
        amount_cents=100_000,
        individual_id="EMP001",
        individual_name="JOHN DOE",
        trace_number=f"{ROUTING_PREFIX}000000{entry_id}",
        addenda=[],
    )
    defaults.update(overrides)
    return AchEntry(**defaults)


def make_batch(entries: list[AchEntry], **overrides) -> AchBatch:
    entry_count = sum(1 + len(e.addenda) for e in entries)
    entry_hash = sum(int(e.receiving_dfi_routing[:8]) for e in entries) % (10**10)
    total_debit = sum(e.amount_cents for e in entries if e.transaction_code in {"27", "28", "37", "38"})
    total_credit = sum(e.amount_cents for e in entries if e.transaction_code in {"22", "23", "32", "33"})
    defaults = dict(
        id=1,
        sec_code="PPD",
        entry_addenda_count=entry_count,
        entry_hash=entry_hash,
        total_debit_amount=total_debit,
        total_credit_amount=total_credit,
        entries=entries,
    )
    defaults.update(overrides)
    return AchBatch(**defaults)


def test_valid_batch_has_no_violations():
    batch = make_batch([make_entry(1), make_entry(2)])
    results = structural.validate_batch(batch)
    assert all(v == [] for v in results.values())


def test_bad_routing_checksum_detected():
    batch = make_batch([make_entry(1, receiving_dfi_routing="021000029")])
    results = structural.validate_batch(batch)
    assert any(v.rule_id == "routing_checksum" for v in results[1])


def test_unknown_transaction_code_detected():
    batch = make_batch([make_entry(1, transaction_code="99")])
    results = structural.validate_batch(batch)
    assert any(v.rule_id == "valid_transaction_code" for v in results[1])


def test_non_ascii_name_detected():
    batch = make_batch([make_entry(1, individual_name="JOHN\x80\x81")])
    results = structural.validate_batch(batch)
    assert any(v.rule_id == "ascii_name_field" for v in results[1])


def test_invalid_sec_code_flags_whole_batch():
    entries = [make_entry(1), make_entry(2)]
    batch = make_batch(entries, sec_code="XXX")
    results = structural.validate_batch(batch)
    assert any(v.rule_id == "valid_sec_code" for v in results[1])
    assert any(v.rule_id == "valid_sec_code" for v in results[2])


def test_corrupted_entry_hash_detected():
    batch = make_batch([make_entry(1)], entry_hash=999999)
    results = structural.validate_batch(batch)
    assert any(v.rule_id == "batch_entry_hash" for v in results[1])


def test_corrupted_totals_detected():
    batch = make_batch([make_entry(1, amount_cents=100_000)], total_credit_amount=1)
    results = structural.validate_batch(batch)
    assert any(v.rule_id == "batch_control_totals" for v in results[1])


def test_wrong_entry_count_detected():
    batch = make_batch([make_entry(1), make_entry(2)], entry_addenda_count=1)
    results = structural.validate_batch(batch)
    assert any(v.rule_id == "batch_entry_count" for v in results[1])


def test_duplicate_trace_number_flags_both_entries():
    e1 = make_entry(1, trace_number="021000020000099")
    e2 = make_entry(2, trace_number="021000020000099")
    batch = make_batch([e1, e2])
    results = structural.validate_batch(batch)
    assert any(v.rule_id == "duplicate_trace_number" for v in results[1])
    assert any(v.rule_id == "duplicate_trace_number" for v in results[2])


def test_duplicate_trace_number_does_not_flag_unique_entries():
    batch = make_batch([make_entry(1), make_entry(2)])
    results = structural.validate_batch(batch)
    assert not any(v.rule_id == "duplicate_trace_number" for v in results[1])
    assert not any(v.rule_id == "duplicate_trace_number" for v in results[2])
