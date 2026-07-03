import math

import pytest

from achchaosmonkey.nacha.exceptions import FieldLengthError
from achchaosmonkey.nacha.fields import RECORD_LENGTH
from achchaosmonkey.nacha.writer import assemble_file, format_field, write_entry_detail
from achchaosmonkey.nacha.fields import ENTRY_DETAIL_FIELDS
from tests.conftest import ROUTING, build_sample_file


def test_every_line_is_94_chars(sample_file_record):
    text = assemble_file(sample_file_record)
    lines = text.strip("\n").split("\n")
    assert all(len(line) == RECORD_LENGTH for line in lines)


def test_total_lines_is_multiple_of_ten(sample_file_record):
    text = assemble_file(sample_file_record)
    lines = text.strip("\n").split("\n")
    assert len(lines) % 10 == 0


def test_record_type_codes_in_expected_order(sample_file_record):
    text = assemble_file(sample_file_record)
    lines = text.strip("\n").split("\n")
    codes = [line[0] for line in lines]
    assert codes[0] == "1"
    assert codes[1] == "5"
    assert codes[2] == "6"
    assert codes[3] == "6"
    assert codes[4] == "8"
    assert codes[5] == "9"
    assert all(c == "9" for c in codes[6:])


def test_batch_control_totals_computed_from_entries():
    file_record = build_sample_file(num_entries=3)
    assemble_file(file_record)
    batch = file_record.batches[0]
    expected_credit = sum(e.amount_cents for e in batch.entries)
    assert batch.control.total_credit_amount == expected_credit
    assert batch.control.total_debit_amount == 0
    assert batch.control.entry_addenda_count == 3
    assert batch.control.entry_hash == int(ROUTING[:8]) * 3 % (10**10)


def test_file_control_block_count(sample_file_record):
    text = assemble_file(sample_file_record)
    lines = text.strip("\n").split("\n")
    assert sample_file_record.control.block_count == math.ceil(len(lines) / 10)


def test_overrides_corrupt_batch_control_totals():
    file_record = build_sample_file(num_entries=2)
    assemble_file(file_record, overrides={"batch_control": {1: {"entry_hash": 999999}}})
    assert file_record.batches[0].control.entry_hash == 999999


def test_overrides_corrupt_file_control_totals():
    file_record = build_sample_file(num_entries=2)
    assemble_file(file_record, overrides={"file_control": {"entry_addenda_count": 42}})
    assert file_record.control.entry_addenda_count == 42


def test_format_field_left_justifies_alpha():
    spec = ENTRY_DETAIL_FIELDS[8]  # discretionary_data, ALPHA, length 2
    assert format_field(spec, "X") == "X "


def test_format_field_right_justifies_numeric_zero_padded():
    spec = ENTRY_DETAIL_FIELDS[5]  # amount, NUMERIC, length 10
    assert format_field(spec, 500) == "0000000500"


def test_format_field_raises_when_value_too_long():
    spec = ENTRY_DETAIL_FIELDS[5]  # amount, length 10
    with pytest.raises(FieldLengthError):
        format_field(spec, "12345678901")


def test_write_entry_detail_splits_routing_prefix_and_check_digit():
    file_record = build_sample_file(num_entries=1)
    entry = file_record.batches[0].entries[0]
    line = write_entry_detail(entry)
    assert line[3:11] == ROUTING[:8]
    assert line[11] == ROUTING[8]
