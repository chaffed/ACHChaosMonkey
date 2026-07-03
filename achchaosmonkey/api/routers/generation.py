from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...db import models
from ...db.ingest import ingest_file_record
from ...generator.builder import build_file
from ...generator.chaos import ChaosConfig
from ...nacha.writer import assemble_file
from ..deps import get_db
from ..schemas import GenerateRequest, GenerateResponse

router = APIRouter(prefix="/api/generate", tags=["generation"])


@router.post("", response_model=GenerateResponse)
def generate(request: GenerateRequest, db: Session = Depends(get_db)) -> GenerateResponse:
    chaos = ChaosConfig.preset(request.chaos_level)
    chaos.fraud_rates.update(request.fraud_rate_overrides)
    chaos.miscode_rates.update(request.miscode_rate_overrides)

    generated = build_file(
        num_batches=request.num_batches,
        entries_per_batch=request.entries_per_batch,
        chaos=chaos,
        seed=request.seed,
    )
    # Computes control totals from the actual records (chaos overrides may have corrupted them).
    assemble_file(generated.record, overrides=generated.overrides)

    db_file = ingest_file_record(db, generated.record, source=models.SOURCE_GENERATED, labels=generated.labels)
    db.commit()

    num_entries = sum(len(b.entries) for b in generated.record.batches)
    num_fraud = sum(1 for label in generated.labels.values() if label.is_fraud)
    num_miscoded = sum(1 for label in generated.labels.values() if label.is_miscoded)

    return GenerateResponse(
        file_id=db_file.id,
        num_batches=len(generated.record.batches),
        num_entries=num_entries,
        num_fraud=num_fraud,
        num_miscoded=num_miscoded,
    )
