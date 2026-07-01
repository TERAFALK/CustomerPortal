"""baseline — nuvarande schema

Idempotent baslinje. På en färsk databas skapas alla tabeller från
ORM-modellerna. På en befintlig databas (som redan har schemat) ska denna
revision markeras som körd utan att köras:  alembic stamp 0001_baseline

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-01
"""
from typing import Sequence, Union

from alembic import op

from app.db.database import Base
import app.db.models  # noqa: F401 — registrerar modeller på Base.metadata

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Idempotenta drift-fixar (speglar app/db/database.py) så baslinjen kan lyfta
# även äldre databaser till nuvarande schema.
_DRIFT = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR NOT NULL DEFAULT 'admin'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS customer_id VARCHAR REFERENCES customers(id)",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS assigned_to_user_id VARCHAR REFERENCES users(id)",
    "ALTER TABLE customer_contacts ADD COLUMN IF NOT EXISTS receives_reports BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE customer_contacts ADD COLUMN IF NOT EXISTS has_portal_access BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE customer_contacts ADD COLUMN IF NOT EXISTS user_id VARCHAR REFERENCES users(id)",
    "ALTER TABLE customers DROP COLUMN IF EXISTS contact_email",
    "UPDATE users SET role = 'admin' WHERE role = 'technician'",
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS parent_ticket_id VARCHAR REFERENCES tickets(id)",
    "DO $$ DECLARE col text; BEGIN "
    "FOR col IN SELECT column_name FROM information_schema.columns "
    "WHERE table_name='audit_logs' AND column_name NOT IN "
    "('id','actor_user_id','actor_email','action','entity_type','entity_id','summary','created_at') "
    "LOOP EXECUTE 'ALTER TABLE audit_logs DROP COLUMN ' || quote_ident(col); END LOOP; END $$;",
]


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind)  # checkfirst=True → skapar bara det som saknas
    for stmt in _DRIFT:
        op.execute(stmt)


def downgrade() -> None:
    # Baslinje — ingen nedgradering.
    pass
