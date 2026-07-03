import random

import pytest

from achchaosmonkey.generator.profiles import generate_profiles, random_routing
from achchaosmonkey.generator.strategies import BatchContext, EntryContext
from achchaosmonkey.generator.strategies.fraud import (
    amount_structuring,
    duplicate_trace_number,
    name_account_mismatch,
    new_receiver_high_value,
    round_trip_entries,
    shell_company_batch,
    velocity_burst,
)
from achchaosmonkey.generator.strategies.miscode import (
    bad_control_totals,
    bad_routing_checksum,
    corrupted_name_field,
    invalid_sec_code,
    transaction_code_account_type_mismatch,
)
from achchaosmonkey.nacha.checksum import is_valid_routing_number
from achchaosmonkey.nacha.fields import CHECKING_TRANSACTION_CODES, SAVINGS_TRANSACTION_CODES, VALID_SEC_CODES
from achchaosmonkey.nacha.records import BatchHeader, EntryDetail
from tests.conftest import ROUTING, build_sample_file


def make_entry(**overrides) -> EntryDetail:
    defaults = dict(
        transaction_code="22",
        receiving_dfi_routing=ROUTING,
        dfi_account_number="000123456789",
        amount_cents=100_000,
        individual_name="JOHN DOE",
        individual_id="EMP001",
        trace_number=f"{ROUTING[:8]}0000001",
    )
    defaults.update(overrides)
    return EntryDetail(**defaults)


def make_ctx(entries=None, rng=None):
    rng = rng or random.Random(1)
    entries = entries if entries is not None else []
    profiles = generate_profiles(5, rng)
    return EntryContext(rng=rng, batch_entries=entries, profiles=profiles, hot_account="999999999999")


def test_amount_structuring_targets_ctr_threshold():
    entry = make_entry()
    label = amount_structuring(entry, make_ctx())
    assert label.is_fraud and label.fraud_type == "amount_structuring"
    assert 900_000 <= entry.amount_cents <= 999_999


def test_velocity_burst_reuses_hot_account():
    entry = make_entry()
    ctx = make_ctx()
    label = velocity_burst(entry, ctx)
    assert label.fraud_type == "velocity_burst"
    assert entry.dfi_account_number == ctx.hot_account


def test_name_account_mismatch_changes_name():
    entry = make_entry(individual_name="ORIGINAL NAME")
    ctx = make_ctx()
    label = name_account_mismatch(entry, ctx)
    assert label.fraud_type == "name_account_mismatch"
    assert entry.individual_name != "ORIGINAL NAME"


def test_new_receiver_high_value_raises_amount():
    entry = make_entry(amount_cents=50_000)
    label = new_receiver_high_value(entry, make_ctx())
    assert label.fraud_type == "new_receiver_high_value"
    assert entry.amount_cents > 1_000_000


def test_round_trip_entries_requires_prior_entry():
    entry = make_entry()
    assert round_trip_entries(entry, make_ctx(entries=[entry])) is None


def test_round_trip_entries_mirrors_counterpart():
    counterpart = make_entry(dfi_account_number="000999999999", amount_cents=200_000, transaction_code="22")
    entry = make_entry()
    ctx = make_ctx(entries=[counterpart, entry])
    label = round_trip_entries(entry, ctx)
    assert label.fraud_type == "round_trip_entries"
    assert entry.dfi_account_number == counterpart.dfi_account_number
    assert entry.transaction_code == "27"  # offsetting debit against counterpart's credit
    assert abs(entry.amount_cents - counterpart.amount_cents) <= counterpart.amount_cents * 0.05


def test_duplicate_trace_number_requires_prior_entry():
    entry = make_entry()
    assert duplicate_trace_number(entry, make_ctx(entries=[entry])) is None


def test_duplicate_trace_number_copies_prior_trace():
    counterpart = make_entry(trace_number="021000020000099")
    entry = make_entry()
    ctx = make_ctx(entries=[counterpart, entry])
    label = duplicate_trace_number(entry, ctx)
    assert label.fraud_type == "duplicate_trace_number"
    assert entry.trace_number == counterpart.trace_number


def test_shell_company_batch_mutates_header():
    file_record = build_sample_file(num_entries=2)
    batch = file_record.batches[0]
    original_name = batch.header.company_name
    label, control_override = shell_company_batch(batch, BatchContext(rng=random.Random(3)))
    assert label.fraud_type == "shell_company_batch"
    assert batch.header.company_name != original_name
    assert control_override is None


def test_bad_routing_checksum_breaks_validity():
    entry = make_entry()
    assert is_valid_routing_number(entry.receiving_dfi_routing)
    label = bad_routing_checksum(entry, make_ctx())
    assert label.miscode_type == "bad_routing_checksum"
    assert not is_valid_routing_number(entry.receiving_dfi_routing)
    assert entry.receiving_dfi_routing[:8] == ROUTING[:8]  # only the check digit changed


def test_transaction_code_account_type_mismatch_flips_category():
    checking_entry = make_entry(transaction_code="22")
    label = transaction_code_account_type_mismatch(checking_entry, make_ctx())
    assert label.miscode_type == "transaction_code_account_type_mismatch"
    assert checking_entry.transaction_code in SAVINGS_TRANSACTION_CODES

    savings_entry = make_entry(transaction_code="32")
    transaction_code_account_type_mismatch(savings_entry, make_ctx())
    assert savings_entry.transaction_code in CHECKING_TRANSACTION_CODES


def test_corrupted_name_field_injects_non_ascii():
    entry = make_entry(individual_name="JOHN DOE")
    label = corrupted_name_field(entry, make_ctx())
    assert label.miscode_type == "corrupted_name_field"
    assert not entry.individual_name.isascii()
    assert len(entry.individual_name) <= 22


def test_invalid_sec_code_sets_unrecognized_code():
    file_record = build_sample_file(num_entries=1)
    batch = file_record.batches[0]
    label, control_override = invalid_sec_code(batch, BatchContext(rng=random.Random(2)))
    assert label.miscode_type == "invalid_sec_code"
    assert batch.header.sec_code not in VALID_SEC_CODES
    assert control_override is None


def test_bad_control_totals_returns_entry_hash_override():
    file_record = build_sample_file(num_entries=1)
    batch = file_record.batches[0]
    label, control_override = bad_control_totals(batch, BatchContext(rng=random.Random(4)))
    assert label.miscode_type == "bad_control_totals"
    assert "entry_hash" in control_override
