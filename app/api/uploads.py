import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from app.core.config import get_settings
from app.core.security import get_current_user
from app.models.user import User
from app.services.audit import log_audit
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/uploads", tags=["File Uploads"])
settings = get_settings()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".dcm", ".dicom", ".mp4", ".webm", ".mov", ".pdf"}
MAX_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not allowed")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = upload_dir / filename

    with open(filepath, "wb") as f:
        f.write(content)

    file_type = "image"
    if ext in (".mp4", ".webm", ".mov"):
        file_type = "video"
    elif ext in (".dcm", ".dicom"):
        file_type = "dicom"
    elif ext == ".pdf":
        file_type = "document"

    await log_audit(db, action="upload_file", resource_type="file", resource_id=filename,
                    detail=f"Uploaded {file.filename} ({len(content)} bytes)",
                    user_id=current_user.id, user_email=current_user.email, request=request)
    await db.commit()

    return {
        "filename": filename,
        "original_name": file.filename,
        "url": f"/static/uploads/{filename}",
        "size": len(content),
        "type": file_type,
    }


@router.post("/multiple")
async def upload_multiple_files(
    request: Request,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files per upload")

    results = []
    for file in files:
        if not file.filename:
            continue

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            results.append({"original_name": file.filename, "error": f"Type '{ext}' not allowed"})
            continue

        content = await file.read()
        if len(content) > MAX_SIZE:
            results.append({"original_name": file.filename, "error": "File too large"})
            continue

        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = upload_dir / filename

        with open(filepath, "wb") as f:
            f.write(content)

        file_type = "image"
        if ext in (".mp4", ".webm", ".mov"):
            file_type = "video"
        elif ext in (".dcm", ".dicom"):
            file_type = "dicom"
        elif ext == ".pdf":
            file_type = "document"

        results.append({
            "filename": filename,
            "original_name": file.filename,
            "url": f"/static/uploads/{filename}",
            "size": len(content),
            "type": file_type,
        })

    await log_audit(db, action="upload_multiple", resource_type="file",
                    detail=f"Uploaded {len(results)} files",
                    user_id=current_user.id, user_email=current_user.email, request=request)
    await db.commit()

    return {"files": results, "count": len(results)}
