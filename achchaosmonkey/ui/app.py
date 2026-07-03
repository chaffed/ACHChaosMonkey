from nicegui import ui

NAV_ITEMS = [
    ("/", "Dashboard"),
    ("/generate", "Generate"),
    ("/transactions", "Transactions"),
    ("/validate", "Validate"),
    ("/io", "Import/Export"),
]


def add_nav(active: str) -> None:
    with ui.header().classes("items-center justify-between px-4"):
        ui.label("ACH Chaos Monkey").classes("text-lg font-bold")
        with ui.row().classes("gap-4"):
            for path, label in NAV_ITEMS:
                link = ui.link(label, path).classes("text-white no-underline")
                if path == active:
                    link.classes("font-bold underline")


def register_pages() -> None:
    from .pages import dashboard, generate, io_page, transactions, validate  # noqa: F401  registers @ui.page routes
