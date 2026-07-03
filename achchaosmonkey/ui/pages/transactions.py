from nicegui import ui
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from ...db import models
from ...db.base import SessionLocal
from ..app import add_nav
from ..components.tables import entry_columns, format_amount, ground_truth_label


@ui.page("/transactions")
def transactions_page() -> None:
    add_nav("/transactions")
    ui.label("Files").classes("text-xl font-bold p-4")

    session = SessionLocal()
    try:
        files = session.query(models.AchFile).order_by(desc(models.AchFile.id)).all()
        rows = []
        for f in files:
            entries = [e for b in f.batches for e in b.entries]
            rows.append(
                {
                    "id": f.id,
                    "source": f.source,
                    "created_at": f.created_at.strftime("%Y-%m-%d %H:%M") if f.created_at else "",
                    "batches": len(f.batches),
                    "entries": len(entries),
                    "fraud": sum(1 for e in entries if e.is_fraud),
                    "miscoded": sum(1 for e in entries if e.is_miscoded),
                }
            )
    finally:
        session.close()

    columns = [
        {"name": "id", "label": "File ID", "field": "id", "sortable": True},
        {"name": "source", "label": "Source", "field": "source"},
        {"name": "created_at", "label": "Created", "field": "created_at", "sortable": True},
        {"name": "batches", "label": "Batches", "field": "batches"},
        {"name": "entries", "label": "Entries", "field": "entries"},
        {"name": "fraud", "label": "Fraud", "field": "fraud"},
        {"name": "miscoded", "label": "Miscoded", "field": "miscoded"},
    ]
    table = ui.table(rows=rows, columns=columns, row_key="id", pagination=20).classes("m-4")
    table.on("rowClick", lambda e: ui.navigate.to(f"/transactions/{e.args[1]['id']}"))
    ui.label("Click a row to view its entries.").classes("px-4 text-gray-500")


@ui.page("/transactions/{file_id}")
def transaction_detail_page(file_id: int) -> None:
    add_nav("/transactions")

    session = SessionLocal()
    try:
        db_file = (
            session.query(models.AchFile)
            .options(joinedload(models.AchFile.batches).joinedload(models.AchBatch.entries))
            .filter(models.AchFile.id == file_id)
            .first()
        )
        if db_file is None:
            ui.label(f"File #{file_id} not found").classes("p-4 text-red-600")
            return

        latest_results: dict[int, models.ValidationResult] = {}
        entry_ids = [e.id for b in db_file.batches for e in b.entries]
        if entry_ids:
            results = (
                session.query(models.ValidationResult)
                .filter(models.ValidationResult.entry_id.in_(entry_ids))
                .order_by(models.ValidationResult.id.desc())
                .all()
            )
            for result in results:
                latest_results.setdefault(result.entry_id, result)

        rows = []
        for batch in db_file.batches:
            for entry in batch.entries:
                result = latest_results.get(entry.id)
                rows.append(
                    {
                        "id": entry.id,
                        "batch": batch.batch_number,
                        "transaction_code": entry.transaction_code,
                        "routing": entry.receiving_dfi_routing,
                        "account": entry.dfi_account_number,
                        "amount": format_amount(entry.amount_cents),
                        "name": entry.individual_name,
                        "ground_truth": ground_truth_label(entry),
                        "verdict": result.verdict if result else "not validated",
                        "risk_score": f"{result.combined_risk_score:.2f}" if result else "-",
                    }
                )
    finally:
        session.close()

    ui.link("< Back to files", "/transactions").classes("p-4")
    ui.label(f"File #{file_id} entries").classes("text-xl font-bold px-4")
    ui.table(rows=rows, columns=entry_columns(), row_key="id", pagination=25).classes("m-4")
