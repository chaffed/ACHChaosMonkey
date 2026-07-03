import random
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..nacha.records import AchFileRecord, Batch, BatchHeader, EntryDetail, FileHeader
from .chaos import ChaosConfig
from .profiles import fake, generate_company_profile, generate_profiles, random_routing
from .strategies import (
    BATCH_FRAUD_STRATEGIES,
    BATCH_MISCODE_STRATEGIES,
    ENTRY_FRAUD_STRATEGIES,
    ENTRY_MISCODE_STRATEGIES,
    BatchContext,
    EntryContext,
    EntryLabel,
)


@dataclass
class GeneratedFile:
    record: AchFileRecord
    # (batch_index, entry_index), both 0-based in file_record.batches[i].entries order
    labels: dict[tuple[int, int], EntryLabel] = field(default_factory=dict)
    overrides: dict = field(default_factory=dict)


def _apply_batch_level_strategies(batch, batch_idx, rates, registry, labels, batch_overrides, ctx):
    for strategy_id, rate in rates.items():
        if strategy_id not in registry or ctx.rng.random() >= rate:
            continue
        label, control_override = registry[strategy_id](batch, ctx)
        for entry_idx in range(len(batch.entries)):
            existing = labels.get((batch_idx, entry_idx), EntryLabel())
            labels[(batch_idx, entry_idx)] = existing.merged_with(label)
        if control_override:
            batch_overrides.setdefault(batch.header.batch_number, {}).update(control_override)


def build_file(
    num_batches: int = 1,
    entries_per_batch: int = 10,
    chaos: ChaosConfig | None = None,
    seed: int | None = None,
) -> GeneratedFile:
    chaos = chaos or ChaosConfig.none()
    rng = random.Random(seed)
    if seed is not None:
        fake.seed_instance(seed)

    origin_routing = random_routing(rng)
    dest_routing = random_routing(rng)
    now = datetime.now(timezone.utc)

    file_header = FileHeader(
        immediate_destination=dest_routing,
        immediate_origin=origin_routing,
        immediate_destination_name="RECEIVING BANK",
        immediate_origin_name="ORIGINATING BANK",
        file_creation_date=now.strftime("%y%m%d"),
        file_creation_time=now.strftime("%H%M"),
        file_id_modifier="A",
    )

    batches: list[Batch] = []
    labels: dict[tuple[int, int], EntryLabel] = {}
    batch_overrides: dict[int, dict] = {}

    for batch_idx in range(num_batches):
        company = generate_company_profile(rng)
        profiles = generate_profiles(max(entries_per_batch, 5), rng)
        batch_header = BatchHeader(
            company_name=company.name,
            company_identification=company.company_id,
            sec_code="PPD",
            company_entry_description="PAYROLL",
            effective_entry_date=now.strftime("%y%m%d"),
            originating_dfi=origin_routing[:8],
            batch_number=batch_idx + 1,
        )
        batch = Batch(header=batch_header)

        entry_ctx = EntryContext(
            rng=rng,
            batch_entries=batch.entries,
            profiles=profiles,
            hot_account=str(rng.randint(10**9, 10**12 - 1)),
        )

        for entry_idx in range(entries_per_batch):
            profile = profiles[entry_idx % len(profiles)]
            transaction_code = "22" if profile.account_type == "checking" else "32"
            trace_seq = len(batch.entries) + 1
            entry = EntryDetail(
                transaction_code=transaction_code,
                receiving_dfi_routing=profile.routing,
                dfi_account_number=profile.account_number,
                amount_cents=rng.randint(5_000, 250_000),
                individual_name=profile.name,
                individual_id=profile.individual_id,
                trace_number=f"{origin_routing[:8]}{trace_seq:07d}",
            )
            batch.entries.append(entry)

            label = EntryLabel()
            mutations = 0
            for strategy_id, rate in chaos.fraud_rates.items():
                if strategy_id not in ENTRY_FRAUD_STRATEGIES:
                    continue
                if mutations >= chaos.max_mutations_per_entry or rng.random() >= rate:
                    continue
                result = ENTRY_FRAUD_STRATEGIES[strategy_id](entry, entry_ctx)
                if result is not None:
                    label = label.merged_with(result)
                    mutations += 1
            for strategy_id, rate in chaos.miscode_rates.items():
                if strategy_id not in ENTRY_MISCODE_STRATEGIES:
                    continue
                if mutations >= chaos.max_mutations_per_entry or rng.random() >= rate:
                    continue
                result = ENTRY_MISCODE_STRATEGIES[strategy_id](entry, entry_ctx)
                if result is not None:
                    label = label.merged_with(result)
                    mutations += 1

            if label.is_fraud or label.is_miscoded:
                labels[(batch_idx, entry_idx)] = label

        batch_ctx = BatchContext(rng=rng)
        _apply_batch_level_strategies(
            batch, batch_idx, chaos.fraud_rates, BATCH_FRAUD_STRATEGIES, labels, batch_overrides, batch_ctx
        )
        _apply_batch_level_strategies(
            batch, batch_idx, chaos.miscode_rates, BATCH_MISCODE_STRATEGIES, labels, batch_overrides, batch_ctx
        )

        batches.append(batch)

    file_record = AchFileRecord(header=file_header, batches=batches)
    overrides = {"batch_control": batch_overrides} if batch_overrides else {}
    return GeneratedFile(record=file_record, labels=labels, overrides=overrides)
