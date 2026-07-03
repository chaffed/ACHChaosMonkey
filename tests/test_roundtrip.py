from dataclasses import asdict

from achchaosmonkey.nacha.parser import parse_file
from achchaosmonkey.nacha.writer import assemble_file
from tests.conftest import build_sample_file


def test_write_then_parse_preserves_entry_fields():
    original = build_sample_file(num_entries=3)
    text = assemble_file(original)
    parsed = parse_file(text)

    assert len(parsed.batches) == len(original.batches)
    for orig_batch, parsed_batch in zip(original.batches, parsed.batches):
        assert orig_batch.header.company_name == parsed_batch.header.company_name
        assert orig_batch.header.company_identification == parsed_batch.header.company_identification
        assert orig_batch.header.sec_code == parsed_batch.header.sec_code
        assert orig_batch.header.effective_entry_date == parsed_batch.header.effective_entry_date
        assert len(orig_batch.entries) == len(parsed_batch.entries)
        for orig_entry, parsed_entry in zip(orig_batch.entries, parsed_batch.entries):
            assert orig_entry.transaction_code == parsed_entry.transaction_code
            assert orig_entry.receiving_dfi_routing == parsed_entry.receiving_dfi_routing
            assert orig_entry.dfi_account_number == parsed_entry.dfi_account_number.strip()
            assert orig_entry.amount_cents == parsed_entry.amount_cents
            assert orig_entry.individual_name.strip() == parsed_entry.individual_name.strip()
            assert orig_entry.trace_number == parsed_entry.trace_number


def test_write_then_parse_preserves_control_totals():
    original = build_sample_file(num_entries=5)
    text = assemble_file(original)
    parsed = parse_file(text)

    assert parsed.control.batch_count == original.control.batch_count
    assert parsed.control.entry_addenda_count == original.control.entry_addenda_count
    assert parsed.control.entry_hash == original.control.entry_hash
    assert parsed.control.total_debit_amount == original.control.total_debit_amount
    assert parsed.control.total_credit_amount == original.control.total_credit_amount
    assert parsed.control.block_count == original.control.block_count


def test_double_round_trip_is_stable():
    original = build_sample_file(num_entries=2)
    text1 = assemble_file(original)
    parsed1 = parse_file(text1)
    text2 = assemble_file(parsed1)
    assert text1 == text2
