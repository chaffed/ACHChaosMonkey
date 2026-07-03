from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ...db import models
from ...io import csv_io, excel_io, nacha_io
from ...nacha.exceptions import NachaFormatError
from ..deps import get_db

router = APIRouter(prefix="/api", tags=["io"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("/import")
async def import_file(file: UploadFile, db: Session = Depends(get_db)) -> dict:
    filename = file.filename or "upload"
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    content = await file.read()

    try:
        if extension in ("ach", "txt"):
            db_file = nacha_io.import_nacha(db, content.decode("utf-8"), original_filename=filename)
        elif extension == "csv":
            db_file = csv_io.import_csv(db, content.decode("utf-8"), original_filename=filename)
        elif extension in ("xlsx", "xls"):
            db_file = excel_io.import_excel(db, content, original_filename=filename)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file extension: .{extension}")
    except (NachaFormatError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    num_entries = sum(len(batch.entries) for batch in db_file.batches)
    return {"file_id": db_file.id, "num_batches": len(db_file.batches), "num_entries": num_entries}


@router.get("/export/{file_id}")
def export_file(file_id: int, format: str = "nacha", db: Session = Depends(get_db)) -> Response:
    db_file = db.get(models.AchFile, file_id)
    if db_file is None:
        raise HTTPException(status_code=404, detail="file not found")

    if format == "nacha":
        return Response(
            content=nacha_io.export_nacha(db_file),
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="ach_file_{file_id}.ach"'},
        )
    if format == "csv":
        return Response(
            content=csv_io.export_csv(db_file),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="ach_file_{file_id}.csv"'},
        )
    if format == "xlsx":
        return Response(
            content=excel_io.export_excel(db_file),
            media_type=XLSX_MEDIA_TYPE,
            headers={"Content-Disposition": f'attachment; filename="ach_file_{file_id}.xlsx"'},
        )
    raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
