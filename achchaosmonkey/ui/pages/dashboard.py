from nicegui import ui

from ...db import models
from ...db.base import SessionLocal
from ..app import add_nav


@ui.page("/")
def dashboard_page() -> None:
    add_nav("/")

    session = SessionLocal()
    try:
        num_files = session.query(models.AchFile).count()
        num_entries = session.query(models.AchEntry).count()
        num_fraud = session.query(models.AchEntry).filter(models.AchEntry.is_fraud.is_(True)).count()
        num_miscoded = session.query(models.AchEntry).filter(models.AchEntry.is_miscoded.is_(True)).count()
        num_runs = session.query(models.ValidationRun).count()
    finally:
        session.close()

    with ui.row().classes("gap-4 p-4"):
        for label, value in [
            ("Files", num_files),
            ("Entries", num_entries),
            ("Fraud entries", num_fraud),
            ("Miscoded entries", num_miscoded),
            ("Validation runs", num_runs),
        ]:
            with ui.card():
                ui.label(label).classes("text-sm text-gray-500")
                ui.label(str(value)).classes("text-2xl font-bold")

    with ui.card().classes("m-4"):
        ui.label("Getting started").classes("text-lg font-bold")
        ui.markdown(
            "1. **Generate** a chaos-injected ACH file with configurable fraud/miscoding rates.\n"
            "2. **Validate** it to run structural rules and the anomaly-detection model, and see precision/recall "
            "against the generator's ground truth.\n"
            "3. Browse results in **Transactions**, or **Import/Export** as NACHA, CSV, or Excel."
        )
