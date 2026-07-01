"""CRUD för standardsvar (canned responses). Endast personal."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin
from app.db.database import get_db
from app.db.models import CannedResponse, User

router = APIRouter()


class CannedBody(BaseModel):
    title: str
    body: str


def _dict(c: CannedResponse) -> dict:
    return {"id": c.id, "title": c.title, "body": c.body}


@router.get("")
async def list_canned(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.scalars(select(CannedResponse).order_by(CannedResponse.title))
    return [_dict(c) for c in rows.all()]


@router.post("", status_code=201)
async def create_canned(
    body: CannedBody,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if not body.title.strip() or not body.body.strip():
        raise HTTPException(400, "Titel och text krävs")
    c = CannedResponse(title=body.title.strip(), body=body.body, created_by=admin.id)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _dict(c)


@router.put("/{canned_id}")
async def update_canned(
    canned_id: str,
    body: CannedBody,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    c = await db.get(CannedResponse, canned_id)
    if not c:
        raise HTTPException(404, "Standardsvar hittades inte")
    c.title = body.title.strip()
    c.body = body.body
    await db.commit()
    return _dict(c)


@router.delete("/{canned_id}", status_code=204)
async def delete_canned(
    canned_id: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    c = await db.get(CannedResponse, canned_id)
    if c:
        await db.delete(c)
        await db.commit()
