from dataclasses import dataclass, field

from .strategies import BATCH_FRAUD_STRATEGIES, BATCH_MISCODE_STRATEGIES, ENTRY_FRAUD_STRATEGIES, ENTRY_MISCODE_STRATEGIES

LEVEL_RATES = {"none": 0.0, "low": 0.03, "medium": 0.08, "high": 0.2}


@dataclass
class ChaosConfig:
    fraud_rates: dict[str, float] = field(default_factory=dict)
    miscode_rates: dict[str, float] = field(default_factory=dict)
    max_mutations_per_entry: int = 2

    @classmethod
    def preset(cls, level: str = "none") -> "ChaosConfig":
        rate = LEVEL_RATES.get(level, 0.0)
        fraud_ids = {**ENTRY_FRAUD_STRATEGIES, **BATCH_FRAUD_STRATEGIES}
        miscode_ids = {**ENTRY_MISCODE_STRATEGIES, **BATCH_MISCODE_STRATEGIES}
        return cls(
            fraud_rates=dict.fromkeys(fraud_ids, rate),
            miscode_rates=dict.fromkeys(miscode_ids, rate),
        )

    @classmethod
    def none(cls) -> "ChaosConfig":
        return cls.preset("none")

    @classmethod
    def all_strategy_ids(cls) -> dict[str, list[str]]:
        return {
            "fraud": sorted({**ENTRY_FRAUD_STRATEGIES, **BATCH_FRAUD_STRATEGIES}),
            "miscode": sorted({**ENTRY_MISCODE_STRATEGIES, **BATCH_MISCODE_STRATEGIES}),
        }
