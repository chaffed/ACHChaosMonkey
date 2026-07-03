from nicegui import ui

from ...db import models
from ...db.base import SessionLocal
from ...db.ingest import ingest_file_record
from ...generator.builder import build_file
from ...generator.chaos import ChaosConfig
from ...nacha.writer import assemble_file
from ..app import add_nav

CHAOS_LEVELS = ["none", "low", "medium", "high"]


@ui.page("/generate")
def generate_page() -> None:
    add_nav("/generate")
    ui.label("Generate ACH File").classes("text-xl font-bold p-4")

    with ui.card().classes("m-4 gap-2"):
        num_batches = ui.number("Batches", value=1, min=1, max=50, precision=0)
        entries_per_batch = ui.number("Entries per batch", value=10, min=1, max=1000, precision=0)
        chaos_level = ui.select(CHAOS_LEVELS, value="none", label="Chaos level")
        seed = ui.number("Seed (optional, for reproducible output)", value=None)
        result_label = ui.label().classes("mt-2")

        def on_generate() -> None:
            session = SessionLocal()
            try:
                chaos = ChaosConfig.preset(chaos_level.value)
                seed_value = int(seed.value) if seed.value not in (None, "") else None
                generated = build_file(
                    num_batches=int(num_batches.value or 1),
                    entries_per_batch=int(entries_per_batch.value or 1),
                    chaos=chaos,
                    seed=seed_value,
                )
                assemble_file(generated.record, overrides=generated.overrides)
                db_file = ingest_file_record(
                    session, generated.record, source=models.SOURCE_GENERATED, labels=generated.labels
                )
                session.commit()

                num_entries = sum(len(b.entries) for b in generated.record.batches)
                num_fraud = sum(1 for label in generated.labels.values() if label.is_fraud)
                num_miscoded = sum(1 for label in generated.labels.values() if label.is_miscoded)
                result_label.set_text(
                    f"Generated file #{db_file.id}: {num_entries} entries, {num_fraud} fraud, {num_miscoded} miscoded."
                )
                ui.notify(f"Generated file #{db_file.id}", type="positive")
            except Exception as exc:  # noqa: BLE001  surface any generation failure to the user
                ui.notify(f"Generation failed: {exc}", type="negative")
            finally:
                session.close()

        ui.button("Generate", on_click=on_generate).classes("mt-2")
