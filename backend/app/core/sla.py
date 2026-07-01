"""Beräkning av SLA-tidsgränser (first response + resolution) per prioritet.

Tidsberäkningen är centraliserad här. Idag används väggklocka (24/7). Fas 3c
byter _add_sla_hours mot en arbetstidskalender utan att röra anroparna.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TicketSlaPolicy


def _add_sla_hours(start: datetime, hours: int) -> datetime:
    return start + timedelta(hours=hours)


async def sla_due_dates(db: AsyncSession, priority: str) -> tuple[datetime | None, datetime | None]:
    """Returnerar (first_response_due, resolution_due) för prioriteten, eller (None, None)."""
    policy = await db.scalar(select(TicketSlaPolicy).where(TicketSlaPolicy.priority == priority))
    if not policy:
        return None, None
    now = datetime.now(timezone.utc)
    return _add_sla_hours(now, policy.response_hours), _add_sla_hours(now, policy.resolution_hours)
