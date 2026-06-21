"""
Microsoft 365-adapter.

Autentisering: TERAFALK:s multi-tenant app (client credentials) + kundens tenant_id.
Inga per-kund secrets — kunden ger admin consent en gång via consent-URL.
"""

from app.core.config import settings
from app.core.security import decrypt
from app.db.models import IntegrationCredential
from app.integrations.microsoft.client import GraphClient


def _graph_client(credential: IntegrationCredential) -> GraphClient:
    if not credential.tenant_id:
        raise ValueError("Kundens tenant ID saknas — koppla Microsoft 365 via consent-flödet")
    tenant_id = decrypt(credential.tenant_id)
    return GraphClient(
        tenant_id=tenant_id,
        client_id=settings.MS_APP_CLIENT_ID,
        client_secret=settings.MS_APP_CLIENT_SECRET,
    )


class MicrosoftIntegration:
    async def verify(self, credential: IntegrationCredential) -> tuple[bool, str]:
        if not settings.MS_APP_CLIENT_ID or not settings.MS_APP_CLIENT_SECRET:
            return False, "MS_APP_CLIENT_ID/MS_APP_CLIENT_SECRET ej konfigurerade i .env"
        if not credential.tenant_id:
            return False, "Inte kopplad — kund måste godkänna via consent-länken"
        try:
            import httpx
            tenant_id = decrypt(credential.tenant_id)
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": settings.MS_APP_CLIENT_ID,
                        "client_secret": settings.MS_APP_CLIENT_SECRET,
                        "scope": "https://graph.microsoft.com/.default",
                    },
                )
            if r.status_code == 200:
                return True, "OK"
            body = r.json()
            return False, body.get("error_description") or f"HTTP {r.status_code}"
        except Exception as e:
            return False, str(e)

    async def fetch_report_data(self, credential: IntegrationCredential) -> dict:
        gc = _graph_client(credential)
        return await gc.fetch_all()
