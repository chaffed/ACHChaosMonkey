import io as stdlib_io

import pandas as pd
from sqlalchemy.orm import Session

from ..db import models
from ..db.ingest import ingest_file_record
from ..nacha.writer import assemble_file
from .csv_io import build_dataframe, dataframe_to_file_record


def export_excel(db_file: models.AchFile) -> bytes:
    buffer = stdlib_io.BytesIO()
    build_dataframe(db_file).to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()


def import_excel(session: Session, file_bytes: bytes, original_filename: str | None = None) -> models.AchFile:
    df = pd.read_excel(stdlib_io.BytesIO(file_bytes), engine="openpyxl")
    file_record, labels = dataframe_to_file_record(df)
    assemble_file(file_record)
    return ingest_file_record(
        session, file_record, source=models.SOURCE_IMPORTED, original_filename=original_filename, labels=labels
    )
