from nicegui import ui
from sqlalchemy import desc

from ...db import models
from ...db.base import SessionLocal
from ...io import csv_io, excel_io, nacha_io
from ...nacha.exceptions import NachaFormatError
from ..app import add_nav

FORMAT_MEDIA_TYPES = {
    "nacha": "text/plain",
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@ui.page("/io")
def io_page() -> None:
    add_nav("/io")

    ui.label("Import").classes("text-xl font-bold p-4")
    with ui.card().classes("m-4"):
        ui.label("Upload a NACHA (.ach/.txt), CSV, or Excel (.xlsx) file.").classes("text-gray-500")

        async def on_upload(e) -> None:
            filename = e.file.name
            extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            content = await e.file.read()

            session = SessionLocal()
            try:
                if extension in ("ach", "txt"):
                    db_file = nacha_io.import_nacha(session, content.decode("utf-8"), original_filename=filename)
                elif extension == "csv":
                    db_file = csv_io.import_csv(session, content.decode("utf-8"), original_filename=filename)
                elif extension in ("xlsx", "xls"):
                    db_file = excel_io.import_excel(session, content, original_filename=filename)
                else:
                    ui.notify(f"Unsupported file extension: .{extension}", type="negative")
                    return
                session.commit()
                num_entries = sum(len(b.entries) for b in db_file.batches)
                ui.notify(f"Imported file #{db_file.id} with {num_entries} entries", type="positive")
            except (NachaFormatError, ValueError) as exc:
                ui.notify(f"Import failed: {exc}", type="negative")
            finally:
                session.close()

        ui.upload(on_upload=on_upload, auto_upload=True).classes("w-full")

    ui.label("Export").classes("text-xl font-bold p-4")
    with ui.card().classes("m-4 gap-2"):
        session = SessionLocal()
        try:
            files = session.query(models.AchFile).order_by(desc(models.AchFile.id)).all()
            file_options = {f.id: f"#{f.id} ({f.source}, {sum(len(b.entries) for b in f.batches)} entries)" for f in files}
        finally:
            session.close()

        file_select = ui.select(file_options, label="File to export")
        format_select = ui.select(["nacha", "csv", "xlsx"], value="nacha", label="Format")

        def on_export() -> None:
            if file_select.value is None:
                ui.notify("Select a file first", type="warning")
                return

            session = SessionLocal()
            try:
                db_file = session.get(models.AchFile, file_select.value)
                if db_file is None:
                    ui.notify("File not found", type="negative")
                    return

                fmt = format_select.value
                if fmt == "nacha":
                    content = nacha_io.export_nacha(db_file)
                    filename = f"ach_file_{db_file.id}.ach"
                elif fmt == "csv":
                    content = csv_io.export_csv(db_file)
                    filename = f"ach_file_{db_file.id}.csv"
                else:
                    content = excel_io.export_excel(db_file)
                    filename = f"ach_file_{db_file.id}.xlsx"

                ui.download.content(content, filename, FORMAT_MEDIA_TYPES[fmt])
            finally:
                session.close()

        ui.button("Export", on_click=on_export).classes("mt-2")
