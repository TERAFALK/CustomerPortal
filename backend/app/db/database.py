from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR NOT NULL DEFAULT ''",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR NOT NULL DEFAULT 'admin'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS customer_id VARCHAR REFERENCES customers(id)",
        ]:
            await conn.execute(text(stmt))
    await _seed_phase_templates()
    await _seed_ticket_defaults()


async def _seed_phase_templates() -> None:
    """Skapa standardfaser om tabellen är tom."""
    from app.db.models import OrderPhaseTemplate

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func as sqlfunc

        count = await session.scalar(
            select(sqlfunc.count()).select_from(OrderPhaseTemplate)
        )
        if count and count > 0:
            return

        defaults = {
            "order": ["Bekräftad", "Beställd hos leverantör", "Skickad", "Levererad", "Klar"],
            "project": ["Planering", "Pågår", "Delleverans", "Avslutat"],
        }
        import uuid as _uuid_mod
        for order_type, names in defaults.items():
            for pos, name in enumerate(names):
                session.add(
                    OrderPhaseTemplate(
                        id=str(_uuid_mod.uuid4()),
                        order_type=order_type,
                        name=name,
                        position=pos,
                        is_default=(pos == 0),
                    )
                )
        await session.commit()



async def _seed_ticket_defaults() -> None:
    """Skapa standard SLA-policyer och ärendekategorier om de saknas."""
    from app.db.models import TicketSlaPolicy, TicketCategory
    from sqlalchemy import select, func as sqlfunc
    import uuid as _uuid_mod

    async with AsyncSessionLocal() as session:
        sla_count = await session.scalar(
            select(sqlfunc.count()).select_from(TicketSlaPolicy)
        )
        if not sla_count:
            defaults = [
                ("Critical", "critical", 1, 4),
                ("High",     "high",     4, 8),
                ("Medium",   "medium",   8, 24),
                ("Low",      "low",      24, 72),
            ]
            for name, prio, resp, resol in defaults:
                session.add(TicketSlaPolicy(
                    id=str(_uuid_mod.uuid4()),
                    name=name, priority=prio,
                    response_hours=resp, resolution_hours=resol,
                    is_default=True,
                ))

        cat_count = await session.scalar(
            select(sqlfunc.count()).select_from(TicketCategory)
        )
        if not cat_count:
            categories = [
                ("Nätverk",      "#3b82f6", "ti-network"),
                ("Server",       "#8b5cf6", "ti-server"),
                ("Säkerhet",     "#ef4444", "ti-shield"),
                ("E-post",       "#f59e0b", "ti-mail"),
                ("Övrigt",       "#6b7280", "ti-dots"),
            ]
            for name, color, icon in categories:
                session.add(TicketCategory(
                    id=str(_uuid_mod.uuid4()),
                    name=name, color=color, icon=icon,
                ))
        await session.commit()


async def get_db():
    session: AsyncSession = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
