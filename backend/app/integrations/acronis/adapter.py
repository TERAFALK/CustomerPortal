"""
Acronis-adapter.

Inte implementerat än — kräver Acronis API-credentials. Se
app/integrations/acronis/client.py för planerad funktionalitet.
"""

from app.db.models import IntegrationCredential


class AcronisIntegration:
    async def verify(self, credential: IntegrationCredential) -> tuple[bool, str]:
        return False, "Acronis-integration är inte implementerad än"

    async def fetch_report_data(self, credential: IntegrationCredential) -> dict:
        raise NotImplementedError("Acronis-integration kommer i nästa version")
