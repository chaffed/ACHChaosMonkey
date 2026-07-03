"""Feature extraction: batch entries -> numeric feature vectors for the anomaly model."""

import math
import statistics

from ..db.models import AchBatch
from ..nacha.fields import DEBIT_TRANSACTION_CODES, SAVINGS_TRANSACTION_CODES

FEATURE_NAMES = [
    "log_amount",
    "is_debit",
    "is_savings",
    "name_length",
    "non_ascii_char_count",
    "account_repeat_count",
    "amount_zscore_in_batch",
    "ctr_threshold_distance",
    "duplicate_trace_flag",
]


def extract_batch_features(batch: AchBatch) -> dict[int, list[float]]:
    """Returns entry_id -> feature vector. Some features (z-score, account
    repetition, duplicate trace) need the whole batch's context, which is why
    extraction is batch-scoped rather than per entry."""
    entries = batch.entries
    amounts = [e.amount_cents for e in entries]
    mean_amount = statistics.fmean(amounts) if amounts else 0.0
    stdev_amount = statistics.pstdev(amounts) if len(amounts) > 1 else 0.0

    account_counts: dict[str, int] = {}
    trace_counts: dict[str, int] = {}
    for entry in entries:
        account_counts[entry.dfi_account_number] = account_counts.get(entry.dfi_account_number, 0) + 1
        trace_counts[entry.trace_number] = trace_counts.get(entry.trace_number, 0) + 1

    features: dict[int, list[float]] = {}
    for entry in entries:
        zscore = (entry.amount_cents - mean_amount) / stdev_amount if stdev_amount > 0 else 0.0
        features[entry.id] = [
            math.log1p(entry.amount_cents),
            1.0 if entry.transaction_code in DEBIT_TRANSACTION_CODES else 0.0,
            1.0 if entry.transaction_code in SAVINGS_TRANSACTION_CODES else 0.0,
            float(len(entry.individual_name)),
            float(sum(1 for c in entry.individual_name if not c.isascii())),
            float(account_counts[entry.dfi_account_number]),
            zscore,
            float(abs(entry.amount_cents - 1_000_000)),  # proximity to the $10k CTR-style threshold
            1.0 if trace_counts[entry.trace_number] > 1 else 0.0,
        ]
    return features
