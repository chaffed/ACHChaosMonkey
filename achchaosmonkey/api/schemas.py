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
