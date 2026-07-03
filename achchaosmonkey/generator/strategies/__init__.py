"""Strategy-pattern contract for fraud/miscode injection.

Entry-level strategies mutate a single EntryDetail and are looked up by id
against a per-entry roll of ChaosConfig rates. Batch-level strategies mutate
a whole Batch (company/SEC-code/control fields that don't live on a single
entry) and label every entry in that batch. Every strategy returns an
EntryLabel (the ground truth persisted to the DB) so it can be evaluated
against the validator's findings later.
"""

import random
from dataclasses import dataclass


@dataclass
class EntryLabel:
    is_fraud: bool = False
    fraud_type: str | None = None
    is_miscoded: bool = False
    miscode_type: str | None = None

    def merged_with(self, other: "EntryLabel") -> "EntryLabel":
        return EntryLabel(
            is_fraud=self.is_fraud or other.is_fraud,
            fraud_type=self.fraud_type or other.fraud_type,
            is_miscoded=self.is_miscoded or other.is_miscoded,
            miscode_type=self.miscode_type or other.miscode_type,
        )


@dataclass
class EntryContext:
    rng: random.Random
    batch_entries: list  # EntryDetail objects already added to the current batch, including this one
    profiles: list  # Profile objects available for this batch
    hot_account: str  # a shared account number used by the velocity_burst strategy


@dataclass
class BatchContext:
    rng: random.Random


ENTRY_FRAUD_STRATEGIES: dict[str, callable] = {}
ENTRY_MISCODE_STRATEGIES: dict[str, callable] = {}
BATCH_FRAUD_STRATEGIES: dict[str, callable] = {}
BATCH_MISCODE_STRATEGIES: dict[str, callable] = {}


def entry_fraud(strategy_id: str):
    def register(fn):
        ENTRY_FRAUD_STRATEGIES[strategy_id] = fn
        return fn

    return register


def entry_miscode(strategy_id: str):
    def register(fn):
        ENTRY_MISCODE_STRATEGIES[strategy_id] = fn
        return fn

    return register


def batch_fraud(strategy_id: str):
    def register(fn):
        BATCH_FRAUD_STRATEGIES[strategy_id] = fn
        return fn

    return register


def batch_miscode(strategy_id: str):
    def register(fn):
        BATCH_MISCODE_STRATEGIES[strategy_id] = fn
        return fn

    return register


from . import fraud, miscode  # noqa: E402,F401  populate the registries above on import
