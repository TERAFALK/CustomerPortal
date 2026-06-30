"""Kontrollerar SLA-brott och auto-stänger lösta ärenden — körs av schemaläggaren."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Ticket, TicketHistory

logger = logging.getLogger(__name__)

OPEN_STATUSES = {"new", "open", "in_progress", "pending_customer"}

# Lösta ärenden stängs automatiskt efter så här många dagar utan ny aktivitet.
AUTO_CLOSE_DAYS = 7


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


async def auto_close_resolved_tickets() -> None:
    """Stänger lösta ärenden som legat orörda längre än AUTO_CLOSE_DAYS."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=AUTO_CLOSE_DAYS)
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        tickets = (await db.scalars(
            select(Ticket).where(
                Ticket.status == "resolved",
                Ticket.resolved_at.isnot(None),
                Ticket.resolved_at <= cutoff,
            )
        )).all()
        for ticket in tickets:
            ticket.status = "closed"
            ticket.closed_at = now
            db.add(TicketHistory(
                id=str(uuid.uuid4()),
                ticket_id=ticket.id,
                user_id=None,
                field_changed="status",
                old_value="resolved",
                new_value="closed",
            ))
        if tickets:
            await db.commit()
            logger.info("Auto-stängde %d lösta ärenden", len(tickets))
