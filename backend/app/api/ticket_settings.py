"""Konfiguration av ärendekategorier och SLA-policyer (admin only)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import current_user, require_admin
from app.db.database import get_db
from app.db.models import TicketCategory, TicketSlaPolicy, User

router = APIRouter()


# ── Kategorier ─────────────────────────────────────────────────────────────────

def _cat_dict(c: TicketCategory, include_children: bool = False) -> dict:
    d = {
        "id": c.id,
        "name": c.name,
        "parent_id": c.parent_id,
        "color": c.color,
        "icon": c.icon,
        "position": c.position,
        "is_active": c.is_active,
    }
    if include_children and c.children:
        d["children"] = [_cat_dict(ch) for ch in sorted(c.children, key=lambda x: x.position)]
    return d


@router.get("/categories")
async def list_categories(
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returnerar alla aktiva kategorier platt (frontend bygger trädet)."""
    result = await db.scalars(
        select(TicketCategory).order_by(TicketCategory.position)
    )
    return [_cat_dict(c) for c in result.all()]


class CategoryBody(BaseModel):
    name: str
    parent_id: str | None = None
    color: str = "#6b7280"
    icon: str = "ti-tag"
    position: int = 0
    is_active: bool = True


@router.post("/categories", status_code=201)
async def create_category(
    body: CategoryBody,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cat = TicketCategory(id=str(uuid.uuid4()), **body.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return _cat_dict(cat)


@router.put("/categories/{cat_id}")
async def update_category(
    cat_id: str,
    body: CategoryBody,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cat = await db.get(TicketCategory, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Kategori hittades inte")
    for k, v in body.model_dump().items():
        setattr(cat, k, v)
    await db.commit()
    return _cat_dict(cat)


@router.delete("/categories/{cat_id}", status_code=204)
async def delete_category(
    cat_id: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cat = await db.get(TicketCategory, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Kategori hittades inte")
    await db.delete(cat)
    await db.commit()


# ── SLA-policyer ───────────────────────────────────────────────────────────────

def _sla_dict(s: TicketSlaPolicy) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "priority": s.priority,
        "response_hours": s.response_hours,
        "resolution_hours": s.resolution_hours,
        "is_default": s.is_default,
    }


@router.get("/sla")
async def list_sla_policies(
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.scalars(select(TicketSlaPolicy))
    return [_sla_dict(s) for s in result.all()]


class SlaBody(BaseModel):
    name: str
    priority: str
    response_hours: int
    resolution_hours: int


@router.post("/sla", status_code=201)
async def create_sla_policy(
    body: SlaBody,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    sla = TicketSlaPolicy(id=str(uuid.uuid4()), **body.model_dump())
    db.add(sla)
    await db.commit()
    await db.refresh(sla)
    return _sla_dict(sla)


@router.put("/sla/{sla_id}")
async def update_sla_policy(
    sla_id: str,
    body: SlaBody,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    sla = await db.get(TicketSlaPolicy, sla_id)
    if not sla:
        raise HTTPException(status_code=404, detail="SLA-policy hittades inte")
    for k, v in body.model_dump().items():
        setattr(sla, k, v)
    await db.commit()
    return _sla_dict(sla)


@router.delete("/sla/{sla_id}", status_code=204)
async def delete_sla_policy(
    sla_id: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    sla = await db.get(TicketSlaPolicy, sla_id)
    if not sla:
        raise HTTPException(status_code=404, detail="SLA-policy hittades inte")
    await db.delete(sla)
    await db.commit()
