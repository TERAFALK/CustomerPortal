"""Race-säker generering av ärendenummer (TFyyyymmdd-NNNN).

Ersätter den tidigare "SELECT max + 1"-logiken som kunde ge dubbletter vid
samtidiga skapanden. En atomär INSERT ... ON CONFLICT DO UPDATE serialiserar
räknaren per dag och garanterar unika, löpande nummer.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Ticket


async def generate_ticket_number(db: AsyncSession) -> str:
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"TF{day}-"

    # Första gången en räknare skapas för dagen: starta från högsta befintliga
    # löpnummer (så vi inte krockar med ärenden som skapats innan räknaren fanns).
    current_max = await db.scalar(
        select(func.max(Ticket.ticket_number)).where(Ticket.ticket_number.like(prefix + "%"))
    )
    start = (int(current_max.split("-")[-1]) if current_max else 0) + 1

    seq = await db.scalar(
        text(
            "INSERT INTO ticket_counters (day, last_seq) VALUES (:day, :start) "
            "ON CONFLICT (day) DO UPDATE SET last_seq = ticket_counters.last_seq + 1 "
            "RETURNING last_seq"
        ),
        {"day": day, "start": start},
    )
    return f"{prefix}{seq:04d}"
