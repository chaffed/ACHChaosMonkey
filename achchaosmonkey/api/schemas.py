from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    num_batches: int = Field(default=1, ge=1, le=50)
    entries_per_batch: int = Field(default=10, ge=1, le=1000)
    chaos_level: str = Field(default="none")
    fraud_rate_overrides: dict[str, float] = Field(default_factory=dict)
    miscode_rate_overrides: dict[str, float] = Field(default_factory=dict)
    seed: int | None = None


class GenerateResponse(BaseModel):
    file_id: int
    num_batches: int
    num_entries: int
    num_fraud: int
    num_miscoded: int


class ValidateRequest(BaseModel):
    file_id: int | None = None
    batch_id: int | None = None


class EvaluationSummaryResponse(BaseModel):
    precision: float
    recall: float
    f1: float
    accuracy: float
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int


class ValidateResponse(BaseModel):
    run_id: int
    num_entries: int
    num_flagged: int
    evaluation: EvaluationSummaryResponse
