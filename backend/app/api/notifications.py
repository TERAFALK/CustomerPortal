"""API för att läsa och uppdatera notifikationsinställningar."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin
from app.db.database import get_db
from app.db.models import NotificationSetting, User

router = APIRouter()


def _setting_dict(s: NotificationSetting) -> dict:
    return {
        "event_type": s.event_type,
        "label": s.label,
        "enabled": s.enabled,
        "notify_customer": s.notify_customer,
        "notify_assigned": s.notify_assigned,
        "notify_internal": s.notify_internal,
        "internal_email": s.internal_email or "",
    }


@router.get("")
async def list_settings(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(NotificationSetting))).scalars().all()
    return [_setting_dict(r) for r in rows]


class UpdateNotificationBody(BaseModel):
    enabled: bool | None = None
    notify_customer: bool | None = None
    notify_assigned: bool | None = None
    notify_internal: bool | None = None
    internal_email: str | None = None


@router.put("/{event_type}")
async def update_setting(
    event_type: str,
    body: UpdateNotificationBody,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(NotificationSetting, event_type)
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Inställning ej funnen")

    if body.enabled is not None:
        row.enabled = body.enabled
    if body.notify_customer is not None:
        row.notify_customer = body.notify_customer
    if body.notify_assigned is not None:
        row.notify_assigned = body.notify_assigned
    if body.notify_internal is not None:
        row.notify_internal = body.notify_internal
    if body.internal_email is not None:
        row.internal_email = body.internal_email

    await db.commit()
    await db.refresh(row)
    return _setting_dict(row)
