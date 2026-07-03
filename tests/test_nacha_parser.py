import pytest

from achchaosmonkey.nacha.exceptions import RecordParseError
from achchaosmonkey.nacha.parser import parse_file
from achchaosmonkey.nacha.writer import assemble_file
from tests.conftest import ROUTING, build_sample_file


def test_parses_header_and_entries(sample_file_record):
    text = assemble_file(sample_file_record)
    parsed = parse_file(text)
    assert parsed.header.immediate_origin == "123456789"
    assert len(parsed.batches) == 1
    assert len(parsed.batches[0].entries) == 2


def test_skips_filler_lines(sample_file_record):
    text = assemble_file(sample_file_record)
    parsed = parse_file(text)
    assert parsed.control is not None


def test_rejects_wrong_length_line():
    with pytest.raises(RecordParseError):
        parse_file("1" * 50 + "\n")


def test_rejects_unknown_record_type():
    bad_line = "X" + "0" * 93
    with pytest.raises(RecordParseError):
        parse_file(bad_line + "\n")


def test_entry_before_batch_header_rejected():
    file_record = build_sample_file(num_entries=1)
    text = assemble_file(file_record)
    lines = text.strip("\n").split("\n")
    # Drop the batch header line (index 1) so entry detail comes right after file header.
    reordered = "\n".join([lines[0]] + lines[2:]) + "\n"
    with pytest.raises(RecordParseError):
        parse_file(reordered)


def test_missing_file_header_rejected():
    file_record = build_sample_file(num_entries=1)
    text = assemble_file(file_record)
    lines = text.strip("\n").split("\n")
    without_header = "\n".join(lines[1:]) + "\n"
    with pytest.raises(RecordParseError):
        parse_file(without_header)
