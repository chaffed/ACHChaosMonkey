"""Compare validator verdicts against generator ground truth (precision/recall/F1)."""

from dataclasses import dataclass

from ..db.models import AchEntry, ValidationResult


@dataclass
class EvaluationSummary:
    total: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float
    recall: float
    f1: float
    accuracy: float


def evaluate(
    entries: list[AchEntry],
    results_by_entry: dict[int, ValidationResult],
    positive_verdicts: tuple[str, ...] = ("suspicious", "high_risk", "structural_fail"),
) -> EvaluationSummary:
    tp = fp = fn = tn = 0
    for entry in entries:
        actual_positive = entry.is_fraud or entry.is_miscoded
        result = results_by_entry.get(entry.id)
        predicted_positive = result is not None and result.verdict in positive_verdicts

        if actual_positive and predicted_positive:
            tp += 1
        elif actual_positive and not predicted_positive:
            fn += 1
        elif not actual_positive and predicted_positive:
            fp += 1
        else:
            tn += 1

    total = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / total if total else 0.0

    return EvaluationSummary(
        total=total,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_negatives=tn,
        precision=precision,
        recall=recall,
        f1=f1,
        accuracy=accuracy,
    )
