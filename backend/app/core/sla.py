"""Beräkning av SLA-tidsgränser (first response + resolution) per prioritet.

Tidsberäkningen är centraliserad här. Om arbetstidskalendern är aktiverad
(business_hours_enabled) tickar SLA-klockan bara under konfigurerad arbetstid
mån–fre; annars används väggklocka (24/7).
"""

import logging
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import app_settings
from app.db.models import TicketSlaPolicy

logger = logging.getLogger(__name__)


def _parse_hm(value: str, default: time) -> time:
    try:
        h, m = value.split(":")
        return time(int(h), int(m))
    except Exception:
        return default


def _business_config():
    """Returnerar (enabled, tz, start_time, end_time, days:set[int]) — days i ISO (mån=1)."""
    enabled = (app_settings.get("business_hours_enabled") or "").lower() in ("1", "true", "yes", "on")
    start = _parse_hm(app_settings.get("business_hours_start") or "08:00", time(8, 0))
    end = _parse_hm(app_settings.get("business_hours_end") or "17:00", time(17, 0))
    try:
        days = {int(d) for d in (app_settings.get("business_days") or "1,2,3,4,5").split(",") if d.strip()}
    except Exception:
        days = {1, 2, 3, 4, 5}
    tzname = app_settings.get("business_timezone") or "Europe/Stockholm"
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tzname)
    except Exception:
        tz = timezone.utc
    # Skydd mot ogiltig konfig → fall tillbaka på väggklocka
    if not days or start >= end:
        enabled = False
    return enabled, tz, start, end, days


def _add_business_hours(start_utc: datetime, hours: int, tz, start_t: time, end_t: time, days: set[int]) -> datetime:
    local = start_utc.astimezone(tz)
    remaining = timedelta(hours=hours)
    guard = 0
    while remaining > timedelta(0) and guard < 4000:
        guard += 1
        if local.isoweekday() not in days:
            nxt = (local + timedelta(days=1)).date()
            local = datetime.combine(nxt, start_t, tzinfo=tz)
            continue
        day_start = local.replace(hour=start_t.hour, minute=start_t.minute, second=0, microsecond=0)
        day_end = local.replace(hour=end_t.hour, minute=end_t.minute, second=0, microsecond=0)
        if local < day_start:
            local = day_start
        if local >= day_end:
            nxt = (local + timedelta(days=1)).date()
            local = datetime.combine(nxt, start_t, tzinfo=tz)
            continue
        avail = day_end - local
        if remaining <= avail:
            local = local + remaining
            remaining = timedelta(0)
        else:
            remaining -= avail
            nxt = (local + timedelta(days=1)).date()
            local = datetime.combine(nxt, start_t, tzinfo=tz)
    return local.astimezone(timezone.utc)


def _add_sla_hours(start: datetime, hours: int) -> datetime:
    enabled, tz, start_t, end_t, days = _business_config()
    if not enabled:
        return start + timedelta(hours=hours)
    return _add_business_hours(start, hours, tz, start_t, end_t, days)


async def sla_due_dates(db: AsyncSession, priority: str) -> tuple[datetime | None, datetime | None]:
    """Returnerar (first_response_due, resolution_due) för prioriteten, eller (None, None)."""
    policy = await db.scalar(select(TicketSlaPolicy).where(TicketSlaPolicy.priority == priority))
    if not policy:
        return None, None
    now = datetime.now(timezone.utc)
    return _add_sla_hours(now, policy.response_hours), _add_sla_hours(now, policy.resolution_hours)
