from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.database import get_db
from app.db.models import Report, User

router = APIRouter()


@router.get("")
async def list_reports(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    rows = await db.scalars(
        select(Report).order_by(Report.created_at.desc()).limit(50)
    )
    return [
        {
            "id": r.id,
            "customer_id": r.customer_id,
            "period": r.period,
            "send_status": r.send_status,
            "sent_at": r.sent_at,
            "error_message": r.error_message,
            "pdf_path": r.pdf_path,
        }
        for r in rows.all()
    ]


@router.post("/run/{customer_id}", status_code=202)
async def trigger_report(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    """Triggar rapport-generering för en specifik kund direkt (asynkront)."""
    from app.reports.runner import run_report_for_customer
    import asyncio
    asyncio.create_task(run_report_for_customer(customer_id))
    return {"status": "accepted", "customer_id": customer_id}


@router.post("/run-all", status_code=202)
async def trigger_all_reports(_: User = Depends(current_user)):
    """Triggar rapport-generering för alla aktiva kunder."""
    from app.reports.runner import run_all_reports
    import asyncio
    asyncio.create_task(run_all_reports())
    return {"status": "accepted"}


@router.get("/{report_id}/pdf")
async def download_pdf(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    report = await db.get(Report, report_id)
    if not report or not report.pdf_path:
        raise HTTPException(404, "Rapport-PDF hittades inte")
    return FileResponse(report.pdf_path, media_type="application/pdf")
