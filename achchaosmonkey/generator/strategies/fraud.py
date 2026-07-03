from . import EntryLabel, batch_fraud, entry_fraud
from ...nacha.fields import CREDIT_TRANSACTION_CODES


@entry_fraud("amount_structuring")
def amount_structuring(entry, ctx):
    # $9,000.00-$9,999.99: just under the $10k CTR-style reporting threshold.
    entry.amount_cents = ctx.rng.randint(900_000, 999_999)
    return EntryLabel(is_fraud=True, fraud_type="amount_structuring")


@entry_fraud("velocity_burst")
def velocity_burst(entry, ctx):
    # Many entries in the same batch rapidly hitting one receiver account.
    entry.dfi_account_number = ctx.hot_account
    return EntryLabel(is_fraud=True, fraud_type="velocity_burst")


@entry_fraud("name_account_mismatch")
def name_account_mismatch(entry, ctx):
    other_names = [p.name for p in ctx.profiles if p.name != entry.individual_name]
    if not other_names:
        return None
    entry.individual_name = ctx.rng.choice(other_names)
    return EntryLabel(is_fraud=True, fraud_type="name_account_mismatch")


@entry_fraud("new_receiver_high_value")
def new_receiver_high_value(entry, ctx):
    entry.dfi_account_number = str(ctx.rng.randint(10**9, 10**12 - 1))  # never seen in this batch's profile pool
    entry.amount_cents = ctx.rng.randint(1_500_000, 5_000_000)  # $15k-$50k, well above typical payroll amounts
    return EntryLabel(is_fraud=True, fraud_type="new_receiver_high_value")


@entry_fraud("round_trip_entries")
def round_trip_entries(entry, ctx):
    prior = [e for e in ctx.batch_entries if e is not entry]
    if not prior:
        return None
    counterpart = ctx.rng.choice(prior)
    entry.dfi_account_number = counterpart.dfi_account_number
    entry.receiving_dfi_routing = counterpart.receiving_dfi_routing
    entry.amount_cents = int(counterpart.amount_cents * ctx.rng.uniform(0.97, 1.0))
    entry.transaction_code = "27" if counterpart.transaction_code in CREDIT_TRANSACTION_CODES else "22"
    return EntryLabel(is_fraud=True, fraud_type="round_trip_entries")


@entry_fraud("duplicate_trace_number")
def duplicate_trace_number(entry, ctx):
    prior = [e for e in ctx.batch_entries if e is not entry]
    if not prior:
        return None
    entry.trace_number = ctx.rng.choice(prior).trace_number
    return EntryLabel(is_fraud=True, fraud_type="duplicate_trace_number")


@batch_fraud("shell_company_batch")
def shell_company_batch(batch, ctx):
    suffix = "".join(ctx.rng.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))
    batch.header.company_name = f"QUICKCO {suffix}"[:16]
    batch.header.company_identification = "9" + "".join(ctx.rng.choices("0123456789", k=9))
    batch.header.company_entry_description = "MISC PMT"
    return EntryLabel(is_fraud=True, fraud_type="shell_company_batch"), None
