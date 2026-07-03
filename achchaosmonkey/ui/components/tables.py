def entry_columns() -> list[dict]:
    return [
        {"name": "id", "label": "ID", "field": "id", "sortable": True},
        {"name": "batch", "label": "Batch", "field": "batch", "sortable": True},
        {"name": "transaction_code", "label": "Txn", "field": "transaction_code"},
        {"name": "routing", "label": "Routing", "field": "routing"},
        {"name": "account", "label": "Account", "field": "account"},
        {"name": "amount", "label": "Amount", "field": "amount", "sortable": True},
        {"name": "name", "label": "Name", "field": "name"},
        {"name": "ground_truth", "label": "Ground Truth", "field": "ground_truth"},
        {"name": "verdict", "label": "Verdict", "field": "verdict", "sortable": True},
        {"name": "risk_score", "label": "Risk", "field": "risk_score", "sortable": True},
    ]


def format_amount(amount_cents: int) -> str:
    return f"${amount_cents / 100:,.2f}"


def ground_truth_label(entry) -> str:
    parts = []
    if entry.is_fraud:
        parts.append(f"fraud:{entry.fraud_type}")
    if entry.is_miscoded:
        parts.append(f"miscode:{entry.miscode_type}")
    return ", ".join(parts) if parts else "-"
