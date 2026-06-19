"""
Integrations-router — stubs för Microsoft 365, Acronis och Cloudfactory.
Varje integration aktiveras när credentials lagts till för en kund.
"""

from fastapi import APIRouter, Depends

from app.api.auth import current_user
from app.db.models import User

router = APIRouter()


@router.get("/status")
async def integration_status(_: User = Depends(current_user)):
    """Returnerar vilka integrationer som är konfigurerade globalt."""
    from app.core.config import settings
    return {
        "graph": {
            "configured": bool(settings.GRAPH_TENANT_ID and settings.GRAPH_CLIENT_ID),
            "sender": settings.GRAPH_SENDER,
        },
        "unifi": {"note": "Konfigureras per kund via /api/customers/{id}/credentials/unifi"},
        "microsoft_365": {"note": "Konfigureras per kund — tenant-koppling kommande"},
        "acronis": {"note": "Konfigureras per kund — backup-status kommande"},
        "cloudfactory": {"note": "Konfigureras per kund — licensdata kommande"},
    }
