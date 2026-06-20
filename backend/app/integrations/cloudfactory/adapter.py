"""
Cloudfactory-adapter.

Inte implementerat än — kräver Cloudfactory API-credentials. Se
app/integrations/cloudfactory/client.py för planerad funktionalitet.
"""

from app.db.models import IntegrationCredential


class CloudfactoryIntegration:
    async def verify(self, credential: IntegrationCredential) -> tuple[bool, str]:
        return False, "Cloudfactory-integration är inte implementerad än"

    async def fetch_report_data(self, credential: IntegrationCredential) -> dict:
        raise NotImplementedError("Cloudfactory-integration kommer i nästa version")
