"""Combine rule-engine violations and the anomaly score into one verdict."""

from dataclasses import dataclass

from ..db.models import VERDICT_CLEAN, VERDICT_HIGH_RISK, VERDICT_STRUCTURAL_FAIL, VERDICT_SUSPICIOUS
from .structural import RuleViolation

RULE_SEVERITY_WEIGHT = {"error": 1.0, "warning": 0.3}
HIGH_RISK_THRESHOLD = 0.66
SUSPICIOUS_THRESHOLD = 0.33


@dataclass
class EntryRiskResult:
    entry_id: int
    structural_valid: bool
    structural_errors: list[dict]
    matched_rule_ids: list[str]
    rule_risk_score: float
    anomaly_score: float
    combined_risk_score: float
    verdict: str


def score_entry(entry_id: int, violations: list[RuleViolation], anomaly_score: float) -> EntryRiskResult:
    structural_valid = not any(v.severity == "error" for v in violations)
    rule_risk_score = min(1.0, sum(RULE_SEVERITY_WEIGHT.get(v.severity, 0.5) for v in violations) / 3)
    combined = 1.0 if not structural_valid else max(rule_risk_score, anomaly_score)

    if not structural_valid:
        verdict = VERDICT_STRUCTURAL_FAIL
    elif combined >= HIGH_RISK_THRESHOLD:
        verdict = VERDICT_HIGH_RISK
    elif combined >= SUSPICIOUS_THRESHOLD:
        verdict = VERDICT_SUSPICIOUS
    else:
        verdict = VERDICT_CLEAN

    return EntryRiskResult(
        entry_id=entry_id,
        structural_valid=structural_valid,
        structural_errors=[{"rule_id": v.rule_id, "message": v.message, "severity": v.severity} for v in violations],
        matched_rule_ids=[v.rule_id for v in violations],
        rule_risk_score=rule_risk_score,
        anomaly_score=anomaly_score,
        combined_risk_score=combined,
        verdict=verdict,
    )
