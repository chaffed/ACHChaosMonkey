from nicegui import ui

VERDICT_COLORS = {
    "clean": "positive",
    "suspicious": "warning",
    "high_risk": "negative",
    "structural_fail": "negative",
}


def risk_badge(verdict: str):
    return ui.badge(verdict.replace("_", " ").title(), color=VERDICT_COLORS.get(verdict, "grey"))
