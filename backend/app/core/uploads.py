"""Validering och säker lagring av filuppladdningar (dokument & bilagor)."""

import os

from fastapi import HTTPException, UploadFile

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB

# Tillåtna filändelser för order-dokument och ärendebilagor.
ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg",
    ".txt", ".csv", ".log", ".md",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".7z", ".rar",
    ".eml", ".msg",
}


def validate_extension(filename: str | None) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Filtypen {ext or '(okänd)'} tillåts inte")
    return ext


async def save_upload(file: UploadFile, dest_path: str, *, max_bytes: int = MAX_UPLOAD_BYTES) -> None:
    """Strömmar en uppladdning till disk med storlekstak. Raderar delfil vid överskridande."""
    size = 0
    try:
        with open(dest_path, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Filen är för stor (max {max_bytes // (1024 * 1024)} MB)",
                    )
                out.write(chunk)
    except HTTPException:
        try:
            os.remove(dest_path)
        except OSError:
            pass
        raise
