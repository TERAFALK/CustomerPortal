"""Läs-endpoint för audit-loggen (endast admin)."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin
from app.db.database import get_db
from app.db.models import AuditLog, User

router = APIRouter()


@router.get("")
async def list_audit_log(
    skip: int = 0,
    limit: int = 100,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    limit = min(limit, 200)
    rows = await db.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    )
    return [
        {
            "id": r.id,
            "actor_email": r.actor_email,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "summary": r.summary,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows.all()
    ]
