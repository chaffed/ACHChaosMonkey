# ACH Chaos Monkey

A three-part system for testing and hardening an ACH fraud-detection pipeline:

1. **Generator** — produces synthetic ACH batches/files in NACHA format, with controllable, labeled injection
   of fraud patterns (amount structuring, velocity bursts, account-holder mismatch, round-trip/kiting entries,
   duplicate trace numbers, shell-company batches, new-receiver high-value transfers) and miscoded/malformed
   records (bad routing checksums, transaction-code/account-type mismatches, corrupted name fields, invalid
   SEC codes, bad control totals). Every injected entry carries ground truth in the database.
2. **Validator** — checks NACHA structural/encoding correctness (fixed-width fields, routing check digits,
   batch/file control hash and totals, valid transaction/SEC codes) via a rule engine, and scores fraud risk
   with an unsupervised anomaly model (`scikit-learn` `IsolationForest`). Validation runs can be compared
   against the generator's ground truth (precision/recall/F1).
3. **Frontend** — a NiceGUI console (mounted directly on the FastAPI app) to generate chaos files, run
   validation, browse transactions, and import/export as NACHA, CSV, or Excel.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Alternatively, install pinned versions from a requirements file (no editable install):

```bash
pip install -r requirements.txt        # runtime only
pip install -r requirements-dev.txt    # runtime + test/lint tooling
```

## Run

```bash
source .venv/bin/activate
uvicorn achchaosmonkey.main:app --reload
```

Then open http://127.0.0.1:8000/ for the UI. The API lives under `/api/*` (see `/docs` for the OpenAPI schema).

## Seed some demo data

```bash
python scripts/seed_demo_data.py
```

Generates a handful of files across chaos levels (none/low/medium/high) and trains the anomaly model on the
resulting corpus.

## Train the anomaly model

The anomaly model is a separate artifact from the DB — retrain it any time after generating more data:

```bash
python -m achchaosmonkey.ml.train
```

Until a model is trained, `/api/validate` still runs (rule-engine checks apply normally), but every entry's
`anomaly_score` defaults to `0.0`.

## Tests

```bash
python -m pytest
```

## Project layout

- `achchaosmonkey/nacha/` — pure NACHA fixed-width format logic (field layouts, checksum, writer, parser).
  No DB or ML dependencies; everything else builds on this.
- `achchaosmonkey/generator/` — chaos-monkey file builder and the fraud/miscode strategy registry.
- `achchaosmonkey/validator/` — structural rule engine, feature extraction, anomaly model, risk scoring,
  evaluation against ground truth.
- `achchaosmonkey/io/` — NACHA/CSV/Excel import and export, all funneling into one shared DB ingestion path.
- `achchaosmonkey/db/` — SQLAlchemy models and the file/batch/entry ingestion function.
- `achchaosmonkey/api/` — FastAPI routers (`/api/generate`, `/api/validate`, `/api/import`, `/api/export`).
- `achchaosmonkey/ui/` — NiceGUI pages (dashboard, generate, transactions, validate, import/export).

## Notes on fidelity

NACHA export/import is the only fully lossless round trip for file/batch/control-record fidelity — a file
ingested with deliberately corrupted control totals (the `bad_control_totals` chaos strategy) re-exports with
those same corrupted totals rather than being silently "healed." CSV/Excel are entry-centric conveniences and
don't carry file/batch control-record fidelity, though ground-truth `is_fraud`/`fraud_type` columns do survive
their round trip.
