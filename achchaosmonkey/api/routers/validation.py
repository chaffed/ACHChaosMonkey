from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ...db import models
from ...validator import structural
from ...validator.anomaly import DEFAULT_MODEL_PATH, AnomalyModel
from ...validator.evaluation import evaluate
from ...validator.features import extract_batch_features
from ...validator.risk import score_entry
from ..deps import get_db
from ..schemas import EvaluationSummaryResponse, ValidateRequest, ValidateResponse

router = APIRouter(prefix="/api/validate", tags=["validation"])


def _load_anomaly_model() -> AnomalyModel:
    if DEFAULT_MODEL_PATH.exists():
        return AnomalyModel.load()
    return AnomalyModel()  # unfitted: score() returns 0.0 for every entry until ml.train is run


@router.post("", response_model=ValidateResponse)
def validate(request: ValidateRequest, db: Session = Depends(get_db)) -> ValidateResponse:
    query = db.query(models.AchBatch).options(
        joinedload(models.AchBatch.entries).joinedload(models.AchEntry.addenda)
    )
    if request.file_id is not None:
        query = query.filter(models.AchBatch.file_id == request.file_id)
    if request.batch_id is not None:
        query = query.filter(models.AchBatch.id == request.batch_id)
    batches = query.all()
    if not batches:
        raise HTTPException(status_code=404, detail="No batches found for the given scope")

    anomaly_model = _load_anomaly_model()

    scope = f"file_id={request.file_id} batch_id={request.batch_id}" if (request.file_id or request.batch_id) else "all"
    run = models.ValidationRun(
        scope_description=scope,
        model_version=str(DEFAULT_MODEL_PATH) if DEFAULT_MODEL_PATH.exists() else None,
    )
    db.add(run)
    db.flush()

    all_entries = []
    all_results: dict[int, models.ValidationResult] = {}

    for batch in batches:
        violations_by_entry = structural.validate_batch(batch)
        features_by_entry = extract_batch_features(batch)
        entries_by_id = {e.id: e for e in batch.entries}

        entry_ids = list(features_by_entry.keys())
        feature_matrix = [features_by_entry[eid] for eid in entry_ids]
        anomaly_scores = anomaly_model.score(feature_matrix)

        for entry_id, anomaly_score in zip(entry_ids, anomaly_scores):
            risk = score_entry(entry_id, violations_by_entry.get(entry_id, []), anomaly_score)
            db_result = models.ValidationResult(
                entry_id=entry_id,
                run_id=run.id,
                structural_valid=risk.structural_valid,
                structural_errors=risk.structural_errors,
                matched_rule_ids=risk.matched_rule_ids,
                rule_risk_score=risk.rule_risk_score,
                anomaly_score=risk.anomaly_score,
                combined_risk_score=risk.combined_risk_score,
                verdict=risk.verdict,
            )
            db.add(db_result)
            all_entries.append(entries_by_id[entry_id])
            all_results[entry_id] = db_result

    db.commit()

    summary = evaluate(all_entries, all_results)

    return ValidateResponse(
        run_id=run.id,
        num_entries=len(all_entries),
        num_flagged=sum(1 for r in all_results.values() if r.verdict != models.VERDICT_CLEAN),
        evaluation=EvaluationSummaryResponse(
            precision=summary.precision,
            recall=summary.recall,
            f1=summary.f1,
            accuracy=summary.accuracy,
            true_positives=summary.true_positives,
            false_positives=summary.false_positives,
            false_negatives=summary.false_negatives,
            true_negatives=summary.true_negatives,
        ),
    )
