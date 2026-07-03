from achchaosmonkey.db.models import VERDICT_CLEAN, VERDICT_HIGH_RISK, AchEntry
from achchaosmonkey.validator.evaluation import evaluate


class FakeResult:
    def __init__(self, verdict):
        self.verdict = verdict


def make_entry(entry_id, is_fraud=False, is_miscoded=False):
    return AchEntry(
        id=entry_id,
        sequence_in_batch=1,
        transaction_code="22",
        receiving_dfi_routing="021000021",
        dfi_account_number="000123456789",
        amount_cents=1000,
        individual_name="X",
        is_fraud=is_fraud,
        is_miscoded=is_miscoded,
    )


def test_perfect_classifier_scores_1_0():
    entries = [make_entry(1, is_fraud=True), make_entry(2, is_fraud=False)]
    results = {1: FakeResult(VERDICT_HIGH_RISK), 2: FakeResult(VERDICT_CLEAN)}
    summary = evaluate(entries, results)
    assert summary.precision == 1.0
    assert summary.recall == 1.0
    assert summary.f1 == 1.0
    assert summary.accuracy == 1.0


def test_known_confusion_matrix():
    # 2 true fraud entries: one caught (TP), one missed (FN).
    # 2 clean entries: one wrongly flagged (FP), one correctly clean (TN).
    entries = [
        make_entry(1, is_fraud=True),  # TP
        make_entry(2, is_fraud=True),  # FN
        make_entry(3),  # FP
        make_entry(4),  # TN
    ]
    results = {
        1: FakeResult(VERDICT_HIGH_RISK),
        2: FakeResult(VERDICT_CLEAN),
        3: FakeResult(VERDICT_HIGH_RISK),
        4: FakeResult(VERDICT_CLEAN),
    }
    summary = evaluate(entries, results)
    assert (summary.true_positives, summary.false_negatives, summary.false_positives, summary.true_negatives) == (
        1,
        1,
        1,
        1,
    )
    assert summary.precision == 0.5
    assert summary.recall == 0.5
    assert round(summary.f1, 4) == 0.5
    assert summary.accuracy == 0.5


def test_missing_result_treated_as_not_flagged():
    entries = [make_entry(1, is_fraud=True)]
    summary = evaluate(entries, {})
    assert summary.false_negatives == 1
    assert summary.recall == 0.0


def test_empty_input_returns_zeroed_summary():
    summary = evaluate([], {})
    assert summary.total == 0
    assert summary.precision == 0.0
    assert summary.recall == 0.0
    assert summary.accuracy == 0.0
