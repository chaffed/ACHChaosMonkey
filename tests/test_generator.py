from achchaosmonkey.generator.builder import build_file
from achchaosmonkey.generator.chaos import ChaosConfig
from achchaosmonkey.nacha.checksum import is_valid_routing_number
from achchaosmonkey.nacha.parser import parse_file
from achchaosmonkey.nacha.writer import assemble_file


def test_chaos_none_produces_no_labels():
    generated = build_file(num_batches=2, entries_per_batch=8, chaos=ChaosConfig.none(), seed=1)
    assert generated.labels == {}
    assert generated.overrides == {}


def test_chaos_none_produces_fully_parseable_valid_file():
    generated = build_file(num_batches=2, entries_per_batch=8, chaos=ChaosConfig.none(), seed=1)
    text = assemble_file(generated.record, overrides=generated.overrides)
    parsed = parse_file(text)

    assert len(parsed.batches) == 2
    for batch in parsed.batches:
        assert len(batch.entries) == 8
        for entry in batch.entries:
            assert is_valid_routing_number(entry.receiving_dfi_routing)
        assert batch.control.entry_hash == parsed_batch_entry_hash(batch)


def parsed_batch_entry_hash(batch) -> int:
    return sum(int(e.receiving_dfi_routing[:8]) for e in batch.entries) % (10**10)


def test_chaos_high_produces_labeled_entries():
    generated = build_file(num_batches=3, entries_per_batch=15, chaos=ChaosConfig.preset("high"), seed=123)
    assert len(generated.labels) > 0
    assert all(label.is_fraud or label.is_miscoded for label in generated.labels.values())


def test_seeded_generation_is_deterministic():
    a = build_file(num_batches=2, entries_per_batch=5, chaos=ChaosConfig.preset("medium"), seed=555)
    b = build_file(num_batches=2, entries_per_batch=5, chaos=ChaosConfig.preset("medium"), seed=555)
    text_a = assemble_file(a.record, overrides=a.overrides)
    text_b = assemble_file(b.record, overrides=b.overrides)
    assert text_a == text_b
    assert len(a.labels) == len(b.labels)


def test_max_mutations_per_entry_is_respected():
    from achchaosmonkey.generator.strategies import ENTRY_FRAUD_STRATEGIES, ENTRY_MISCODE_STRATEGIES

    chaos = ChaosConfig(
        fraud_rates=dict.fromkeys(ENTRY_FRAUD_STRATEGIES, 1.0),
        miscode_rates=dict.fromkeys(ENTRY_MISCODE_STRATEGIES, 1.0),
        max_mutations_per_entry=1,
    )
    generated = build_file(num_batches=1, entries_per_batch=30, chaos=chaos, seed=42)
    assert len(generated.labels) == 30
    for label in generated.labels.values():
        # with only entry-level strategies enabled and a cap of 1, exactly one type fires
        assert (label.fraud_type is not None) != (label.miscode_type is not None)
