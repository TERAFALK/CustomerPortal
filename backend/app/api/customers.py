from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import current_user
from app.core.security import decrypt, encrypt
from app.db.database import get_db
from app.db.models import Customer, IntegrationCredential, User

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: str
    contact_name: str = ""
    contact_email: str
    city: str = ""


class CredentialUpsert(BaseModel):
    integration_type: str  # "unifi" | "microsoft" | "acronis" | "cloudfactory"
    api_key: str | None = None
    tenant_id: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
async def list_customers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    rows = await db.scalars(
        select(Customer)
        .where(Customer.is_active == True)
        .options(selectinload(Customer.credentials))
        .order_by(Customer.name)
    )
    customers = rows.all()
    result = []
    for c in customers:
        cred_types = [cr.integration_type for cr in c.credentials]
        result.append({
            "id": c.id,
            "name": c.name,
            "contact_name": c.contact_name,
            "contact_email": c.contact_email,
            "city": c.city,
            "integrations": cred_types,
            "has_unifi": "unifi" in cred_types,
            "has_microsoft": "microsoft" in cred_types,
            "has_acronis": "acronis" in cred_types,
            "has_cloudfactory": "cloudfactory" in cred_types,
        })
    return result


@router.post("", status_code=201)
async def create_customer(
    body: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    customer = Customer(**body.model_dump())
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return {"id": customer.id, "name": customer.name}


@router.get("/{customer_id}")
async def get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    c = await db.scalar(
        select(Customer)
        .where(Customer.id == customer_id)
        .options(selectinload(Customer.credentials), selectinload(Customer.reports))
    )
    if not c:
        raise HTTPException(404, "Kund hittades inte")
    return {
        "id": c.id,
        "name": c.name,
        "contact_name": c.contact_name,
        "contact_email": c.contact_email,
        "city": c.city,
        "integrations": [cr.integration_type for cr in c.credentials],
        "recent_reports": [
            {"id": r.id, "period": r.period, "status": r.send_status, "sent_at": r.sent_at}
            for r in sorted(c.reports, key=lambda r: r.created_at, reverse=True)[:5]
        ],
    }


@router.delete("/{customer_id}", status_code=204)
async def delete_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    c = await db.get(Customer, customer_id)
    if not c:
        raise HTTPException(404, "Kund hittades inte")
    c.is_active = False
    await db.commit()


@router.put("/{customer_id}/credentials/{integration_type}")
async def upsert_credential(
    customer_id: str,
    integration_type: str,
    body: CredentialUpsert,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    cred = await db.scalar(
        select(IntegrationCredential).where(
            IntegrationCredential.customer_id == customer_id,
            IntegrationCredential.integration_type == integration_type,
        )
    )
    if not cred:
        cred = IntegrationCredential(
            customer_id=customer_id,
            integration_type=integration_type,
        )
        db.add(cred)

    if body.api_key is not None:
        cred.api_key = encrypt(body.api_key)
    if body.tenant_id is not None:
        cred.tenant_id = encrypt(body.tenant_id)
    if body.client_id is not None:
        cred.client_id = encrypt(body.client_id)
    if body.client_secret is not None:
        cred.client_secret = encrypt(body.client_secret)

    await db.commit()
    return {"status": "ok", "integration_type": integration_type}


@router.post("/{customer_id}/credentials/unifi/verify")
async def verify_unifi_key(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    """Testar att den sparade UniFi API-nyckeln faktiskt fungerar."""
    cred = await db.scalar(
        select(IntegrationCredential).where(
            IntegrationCredential.customer_id == customer_id,
            IntegrationCredential.integration_type == "unifi",
        )
    )
    if not cred or not cred.api_key:
        raise HTTPException(400, "Ingen UniFi API-nyckel sparad för denna kund")

    key = decrypt(cred.api_key)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.ui.com/v1/hosts",
                headers={"X-API-Key": key, "Accept": "application/json"},
                params={"pageSize": 1},
            )
        if r.status_code == 200:
            cred.is_verified = True
            cred.last_verified_at = datetime.now(timezone.utc)
            await db.commit()
            return {"status": "ok", "http_status": r.status_code}
        return {"status": "error", "http_status": r.status_code, "detail": r.text[:200]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/{customer_id}/unifi/live")
async def get_customer_unifi_live(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    """Hämtar live-data direkt från UniFi API för en specifik kund."""
    cred = await db.scalar(
        select(IntegrationCredential).where(
            IntegrationCredential.customer_id == customer_id,
            IntegrationCredential.integration_type == "unifi",
        )
    )
    if not cred or not cred.api_key:
        raise HTTPException(400, "Ingen UniFi API-nyckel konfigurerad")

    from app.unifi.client import UnifiClient
    with UnifiClient(decrypt(cred.api_key)) as client:
        sites = client.list_sites()
        hosts = client.list_hosts()
        devices = client.list_devices()

    return {
        "sites": [
            {
                "site_id": s.site_id,
                "name": s.name,
                "total_devices": s.total_devices,
                "offline_devices": s.offline_devices,
                "pending_updates": s.pending_updates,
                "wifi_clients": s.wifi_clients,
                "wired_clients": s.wired_clients,
                "gateway_model": s.gateway_model,
                "ips_rules_count": s.ips_rules_count,
                "wans": [
                    {
                        "name": w.name,
                        "uptime_percentage": w.uptime_percentage,
                        "isp_name": w.isp_name,
                        "isp_organization": w.isp_organization,
                        "external_ip": w.external_ip,
                        "has_issues": w.has_issues,
                        "issue_count": w.issue_count,
                    }
                    for w in s.wans
                ],
            }
            for s in sites
        ],
        "devices": [
            {
                "id": d.id,
                "name": d.name,
                "model": d.model,
                "product_line": d.product_line,
                "is_console": d.is_console,
                "is_online": d.is_online,
                "firmware_version": d.firmware_version,
                "firmware_status": d.firmware_status,
                "needs_update": d.needs_update,
                "update_available_version": d.update_available_version,
                "adoption_time": d.adoption_time,
            }
            for d in devices
        ],
        "host_count": len(hosts),
    }
