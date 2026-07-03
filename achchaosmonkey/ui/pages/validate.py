from nicegui import ui
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from ...db import models
from ...db.base import SessionLocal
from ...validator import structural
from ...validator.anomaly import DEFAULT_MODEL_PATH, AnomalyModel
from ...validator.evaluation import evaluate
from ...validator.features import extract_batch_features
from ...validator.risk import score_entry
from ..app import add_nav
from ..components.tables import entry_columns, format_amount, ground_truth_label


def _load_anomaly_model() -> AnomalyModel:
    if DEFAULT_MODEL_PATH.exists():
        return AnomalyModel.load()
    return AnomalyModel()


@ui.page("/validate")
def validate_page() -> None:
    add_nav("/validate")
    ui.label("Run Validation").classes("text-xl font-bold p-4")

    session = SessionLocal()
    try:
        files = session.query(models.AchFile).order_by(desc(models.AchFile.id)).all()
        file_options = {f.id: f"#{f.id} ({f.source}, {sum(len(b.entries) for b in f.batches)} entries)" for f in files}
    finally:
        session.close()

    with ui.card().classes("m-4 gap-2"):
        file_select = ui.select(file_options, label="File to validate")
        summary_label = ui.label().classes("mt-2")
        metrics_row = ui.row().classes("gap-4")
        results_table_container = ui.column().classes("w-full")

        def on_validate() -> None:
            if file_select.value is None:
                ui.notify("Select a file first", type="warning")
                return

            session = SessionLocal()
            try:
                batches = (
                    session.query(models.AchBatch)
                    .options(joinedload(models.AchBatch.entries).joinedload(models.AchEntry.addenda))
                    .filter(models.AchBatch.file_id == file_select.value)
                    .all()
                )
                if not batches:
                    ui.notify("No batches found for this file", type="warning")
                    return

                anomaly_model = _load_anomaly_model()
                run = models.ValidationRun(
                    scope_description=f"file_id={file_select.value}",
                    model_version=str(DEFAULT_MODEL_PATH) if DEFAULT_MODEL_PATH.exists() else None,
                )
                session.add(run)
                session.flush()

                all_entries = []
                all_results = {}
                for batch in batches:
                    violations_by_entry = structural.validate_batch(batch)
                    features_by_entry = extract_batch_features(batch)
                    entries_by_id = {e.id: e for e in batch.entries}
                    entry_ids = list(features_by_entry.keys())
                    scores = anomaly_model.score([features_by_entry[eid] for eid in entry_ids])

                    for entry_id, anomaly_score in zip(entry_ids, scores):
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
                        session.add(db_result)
                        all_entries.append(entries_by_id[entry_id])
                        all_results[entry_id] = db_result

                session.commit()
                summary = evaluate(all_entries, all_results)

                summary_label.set_text(
                    f"Run #{run.id}: {len(all_entries)} entries, "
                    f"{sum(1 for r in all_results.values() if r.verdict != models.VERDICT_CLEAN)} flagged."
                )
                metrics_row.clear()
                with metrics_row:
                    for label, value in [
                        ("Precision", summary.precision),
                        ("Recall", summary.recall),
                        ("F1", summary.f1),
                        ("Accuracy", summary.accuracy),
                    ]:
                        with ui.card():
                            ui.label(label).classes("text-sm text-gray-500")
                            ui.label(f"{value:.2f}").classes("text-xl font-bold")

                rows = []
                for entry in all_entries:
                    result = all_results[entry.id]
                    rows.append(
                        {
                            "id": entry.id,
                            "batch": entry.batch.batch_number,
                            "transaction_code": entry.transaction_code,
                            "routing": entry.receiving_dfi_routing,
                            "account": entry.dfi_account_number,
                            "amount": format_amount(entry.amount_cents),
                            "name": entry.individual_name,
                            "ground_truth": ground_truth_label(entry),
                            "verdict": result.verdict,
                            "risk_score": f"{result.combined_risk_score:.2f}",
                        }
                    )
                results_table_container.clear()
                with results_table_container:
                    ui.table(rows=rows, columns=entry_columns(), row_key="id", pagination=25)

                ui.notify(f"Validation run #{run.id} complete", type="positive")
            except Exception as exc:  # noqa: BLE001  surface any validation failure to the user
                ui.notify(f"Validation failed: {exc}", type="negative")
            finally:
                session.close()

        ui.button("Run Validation", on_click=on_validate).classes("mt-2")

    ui.label(
        "Tip: run `python -m achchaosmonkey.ml.train` after generating some chaos data "
        "to fit the anomaly model; until then, anomaly scores default to 0."
    ).classes("px-4 text-gray-500")
