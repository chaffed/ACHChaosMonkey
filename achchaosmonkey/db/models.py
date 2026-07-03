from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

# Plain string constants rather than SQLAlchemy Enum columns, so values stay
# simple to filter/export as CSV/Excel without enum-name/value translation.
SOURCE_GENERATED = "generated"
SOURCE_IMPORTED = "imported"

VERDICT_CLEAN = "clean"
VERDICT_SUSPICIOUS = "suspicious"
VERDICT_HIGH_RISK = "high_risk"
VERDICT_STRUCTURAL_FAIL = "structural_fail"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AchFile(Base):
    __tablename__ = "ach_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id_modifier: Mapped[str] = mapped_column(String(1), default="A")
    immediate_origin: Mapped[str] = mapped_column(String(10))
    immediate_destination: Mapped[str] = mapped_column(String(10))
    immediate_origin_name: Mapped[str] = mapped_column(String(23), default="")
    immediate_destination_name: Mapped[str] = mapped_column(String(23), default="")
    creation_date: Mapped[str] = mapped_column(String(6), default="")
    creation_time: Mapped[str] = mapped_column(String(4), default="")
    source: Mapped[str] = mapped_column(String(16), default=SOURCE_GENERATED)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    batches: Mapped[list["AchBatch"]] = relationship(back_populates="file", cascade="all, delete-orphan")


class AchBatch(Base):
    __tablename__ = "ach_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("ach_files.id"))
    batch_number: Mapped[int] = mapped_column(Integer)
    service_class_code: Mapped[str] = mapped_column(String(3), default="200")
    company_name: Mapped[str] = mapped_column(String(16), default="")
    company_identification: Mapped[str] = mapped_column(String(10), default="")
    sec_code: Mapped[str] = mapped_column(String(3), default="PPD")
    company_entry_description: Mapped[str] = mapped_column(String(10), default="")
    effective_entry_date: Mapped[str] = mapped_column(String(6), default="")
    originating_dfi: Mapped[str] = mapped_column(String(8), default="")
    entry_addenda_count: Mapped[int] = mapped_column(Integer, default=0)
    entry_hash: Mapped[int] = mapped_column(Integer, default=0)
    total_debit_amount: Mapped[int] = mapped_column(Integer, default=0)
    total_credit_amount: Mapped[int] = mapped_column(Integer, default=0)

    file: Mapped["AchFile"] = relationship(back_populates="batches")
    entries: Mapped[list["AchEntry"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class AchEntry(Base):
    __tablename__ = "ach_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("ach_batches.id"))
    sequence_in_batch: Mapped[int] = mapped_column(Integer, default=1)
    transaction_code: Mapped[str] = mapped_column(String(2))
    receiving_dfi_routing: Mapped[str] = mapped_column(String(9))
    dfi_account_number: Mapped[str] = mapped_column(String(17))
    amount_cents: Mapped[int] = mapped_column(Integer)
    individual_id: Mapped[str] = mapped_column(String(15), default="")
    individual_name: Mapped[str] = mapped_column(String(22))
    discretionary_data: Mapped[str] = mapped_column(String(2), default="")
    addenda_indicator: Mapped[str] = mapped_column(String(1), default="0")
    trace_number: Mapped[str] = mapped_column(String(15), default="")

    is_fraud: Mapped[bool] = mapped_column(Boolean, default=False)
    fraud_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_miscoded: Mapped[bool] = mapped_column(Boolean, default=False)
    miscode_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    chaos_injected: Mapped[bool] = mapped_column(Boolean, default=False)

    batch: Mapped["AchBatch"] = relationship(back_populates="entries")
    addenda: Mapped[list["AchAddenda"]] = relationship(back_populates="entry", cascade="all, delete-orphan")
    validation_results: Mapped[list["ValidationResult"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )


class AchAddenda(Base):
    __tablename__ = "ach_addenda"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("ach_entries.id"))
    addenda_type_code: Mapped[str] = mapped_column(String(2), default="05")
    payment_related_info: Mapped[str] = mapped_column(String(80), default="")
    addenda_sequence_number: Mapped[int] = mapped_column(Integer, default=1)

    entry: Mapped["AchEntry"] = relationship(back_populates="addenda")


class ValidationRun(Base):
    __tablename__ = "validation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    scope_description: Mapped[str] = mapped_column(String(255), default="")
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")

    results: Mapped[list["ValidationResult"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("ach_entries.id"))
    run_id: Mapped[int] = mapped_column(ForeignKey("validation_runs.id"))
    structural_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    structural_errors: Mapped[list] = mapped_column(JSON, default=list)
    matched_rule_ids: Mapped[list] = mapped_column(JSON, default=list)
    rule_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    anomaly_score: Mapped[float] = mapped_column(Float, default=0.0)
    combined_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    verdict: Mapped[str] = mapped_column(String(24), default=VERDICT_CLEAN)

    entry: Mapped["AchEntry"] = relationship(back_populates="validation_results")
    run: Mapped["ValidationRun"] = relationship(back_populates="results")
