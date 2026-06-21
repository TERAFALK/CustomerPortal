import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import current_user, require_admin
from app.core.config import settings
from app.db.database import get_db
from app.db.models import Customer, Report, User

router = APIRouter()


@router.get("")
async def list_reports(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    q = select(Report).order_by(Report.created_at.desc()).offset(skip).limit(limit)
    if user.role == "customer":
        q = q.where(Report.customer_id == user.customer_id)
    rows = await db.scalars(q)
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
    _: User = Depends(require_admin),
):
    """Triggar rapport-generering för en specifik kund direkt (asynkront)."""
    from app.reports.runner import run_report_for_customer
    import asyncio
    asyncio.create_task(run_report_for_customer(customer_id))
    return {"status": "accepted", "customer_id": customer_id}


@router.post("/run-all", status_code=202)
async def trigger_all_reports(_: User = Depends(require_admin)):
    """Triggar rapport-generering för alla aktiva kunder."""
    from app.reports.runner import run_all_reports
    import asyncio
    asyncio.create_task(run_all_reports())
    return {"status": "accepted"}


@router.delete("/history", status_code=200)
async def clear_report_history(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Raderar all rapporthistorik (DB-poster och PDF-filer på disk)."""
    rows = await db.scalars(select(Report))
    reports = rows.all()
    deleted_files = 0
    for r in reports:
        if r.pdf_path:
            try:
                safe_root = os.path.realpath(settings.REPORTS_OUTPUT_DIR)
                pdf_abs = os.path.realpath(r.pdf_path)
                if pdf_abs.startswith(safe_root + os.sep) and os.path.isfile(pdf_abs):
                    os.remove(pdf_abs)
                    deleted_files += 1
            except Exception:
                pass
    result = await db.execute(delete(Report))
    await db.commit()
    return {"deleted_reports": result.rowcount, "deleted_files": deleted_files}


@router.get("/preview/{customer_id}", response_class=HTMLResponse)
async def preview_report(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    """Genererar och returnerar rapport-HTML för förhandsgranskning (ingen PDF, ingen DB-post)."""
    from app.core.time_utils import now_stockholm
    from app.integrations.registry import get_client
    from app.reports.pdf_generator import generate_preview_html

    customer = await db.scalar(
        select(Customer)
        .where(Customer.id == customer_id)
        .options(selectinload(Customer.credentials))
    )
    if not customer:
        raise HTTPException(404, "Kund hittades inte")

    period = now_stockholm().strftime("%Y-%m")
    sections: dict = {}
    for cred in customer.credentials:
        if not cred.is_verified:
            continue
        try:
            client = get_client(cred.integration_type)
            data = await client.fetch_report_data(cred)
            sections[cred.integration_type] = data
        except NotImplementedError:
            pass
        except Exception:
            pass

    if not sections:
        raise HTTPException(422, "Ingen verifierad integration med data — kan inte förhandsvisa rapport")

    html = await generate_preview_html(
        customer_name=customer.name,
        period=period,
        sections=sections,
    )
    return HTMLResponse(content=html)


@router.get("/{report_id}/pdf")
async def download_pdf(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    report = await db.get(Report, report_id)
    if not report or not report.pdf_path:
        raise HTTPException(404, "Rapport-PDF hittades inte")
    safe_root = os.path.realpath(settings.REPORTS_OUTPUT_DIR)
    pdf_abs = os.path.realpath(report.pdf_path)
    if not pdf_abs.startswith(safe_root + os.sep) and pdf_abs != safe_root:
        raise HTTPException(403, "Åtkomst nekad")
    return FileResponse(pdf_abs, media_type="application/pdf")
