"""Kontrollerar SLA-brott var 15:e minut och skickar varningar."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Ticket

logger = logging.getLogger(__name__)

OPEN_STATUSES = {"new", "open", "in_progress", "pending_customer"}


async def check_sla_breaches() -> None:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        from sqlalchemy.orm import selectinload
        tickets = await db.scalars(
            select(Ticket)
            .options(selectinload(Ticket.customer), selectinload(Ticket.assigned_to))
            .where(
                Ticket.status.in_(OPEN_STATUSES),
                Ticket.sla_due_at.isnot(None),
                Ticket.sla_due_at <= now,
                Ticket.sla_breached == False,  # noqa: E712
            )
        )
        breached = tickets.all()
        for ticket in breached:
            ticket.sla_breached = True
            try:
                from app.graph.ticket_mailer import send_sla_breach_warning
                await send_sla_breach_warning(ticket)
            except Exception as e:
                logger.warning("Kunde inte skicka SLA-varning för %s: %s", ticket.ticket_number, e)
        if breached:
            await db.commit()
            logger.info("SLA-brott markerade: %d ärenden", len(breached))
