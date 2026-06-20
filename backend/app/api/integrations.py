"""
Integrations-router — global status, inte kund-specifik (se customers.py
för kund-specifika endpoints som upsert/verify/live-data per integration).
"""

from fastapi import APIRouter, Depends

from app.api.auth import current_user
from app.core.config import settings
from app.db.models import User
from app.integrations.registry import INTEGRATIONS

router = APIRouter()


@router.get("/status")
async def integration_status(_: User = Depends(current_user)):
    """
    Returnerar alla integrationstyper i systemet, jämbördigt — UniFi har
    ingen särställning. Microsoft Graph (för utskick) listas separat
    eftersom det är TERAFALK:s egen avsändarkonfiguration, inte en
    per-kund-integration.
    """
    return {
        "sender": {
            "configured": bool(settings.GRAPH_TENANT_ID and settings.GRAPH_CLIENT_ID),
            "address": settings.GRAPH_SENDER,
            "note": "Används för att SKICKA rapporter — separat från kunders Microsoft 365-integration",
        },
        "integrations": [
            {
                "key": key,
                "display_name": meta.display_name,
                "icon": meta.icon,
                "description": meta.description,
            }
            for key, meta in INTEGRATIONS.items()
        ],
    }
