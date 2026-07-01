"""Hjälpfunktion för att spåra känsliga admin-åtgärder i audit-loggen."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog, User


async def log_action(
    db: AsyncSession,
    actor: User | None,
    action: str,
    entity_type: str = "",
    entity_id: str | None = None,
    summary: str = "",
) -> None:
    """Lägger en audit-post i sessionen. Commit sker av anropande endpoint.

    Loggning får aldrig fälla den egentliga åtgärden — fel sväljs.
    """
    try:
        db.add(AuditLog(
            actor_user_id=actor.id if actor else None,
            actor_email=actor.email if actor else "",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
        ))
    except Exception:
        pass
