from . import EntryLabel, batch_miscode, entry_miscode
from ...nacha.fields import CHECKING_TRANSACTION_CODES, SAVINGS_TRANSACTION_CODES


@entry_miscode("bad_routing_checksum")
def bad_routing_checksum(entry, ctx):
    prefix = entry.receiving_dfi_routing[:8]
    correct_digit = entry.receiving_dfi_routing[8]
    wrong_digit = ctx.rng.choice([d for d in "0123456789" if d != correct_digit])
    entry.receiving_dfi_routing = prefix + wrong_digit
    return EntryLabel(is_miscoded=True, miscode_type="bad_routing_checksum")


@entry_miscode("transaction_code_account_type_mismatch")
def transaction_code_account_type_mismatch(entry, ctx):
    if entry.transaction_code in CHECKING_TRANSACTION_CODES:
        entry.transaction_code = ctx.rng.choice(sorted(SAVINGS_TRANSACTION_CODES))
    else:
        entry.transaction_code = ctx.rng.choice(sorted(CHECKING_TRANSACTION_CODES))
    return EntryLabel(is_miscoded=True, miscode_type="transaction_code_account_type_mismatch")


@entry_miscode("corrupted_name_field")
def corrupted_name_field(entry, ctx):
    garbage = "".join(chr(ctx.rng.randint(0x80, 0xFF)) for _ in range(6))
    entry.individual_name = (entry.individual_name[:10] + garbage)[:22]
    return EntryLabel(is_miscoded=True, miscode_type="corrupted_name_field")


@batch_miscode("invalid_sec_code")
def invalid_sec_code(batch, ctx):
    batch.header.sec_code = ctx.rng.choice(["XXX", "ZZZ", "999"])
    return EntryLabel(is_miscoded=True, miscode_type="invalid_sec_code"), None


@batch_miscode("bad_control_totals")
def bad_control_totals(batch, ctx):
    # Corrupt the batch's entry hash so it no longer matches the sum of RDFI routing prefixes.
    return (
        EntryLabel(is_miscoded=True, miscode_type="bad_control_totals"),
        {"entry_hash": ctx.rng.randint(1, 10**10 - 1)},
    )
