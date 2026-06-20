"""
Microsoft 365-adapter.

Inte implementerat än — kräver App Registration med admin consent i
kundens egen tenant (separat från TERAFALK:s egen Graph-app som används
för att SKICKA rapporter). Se app/integrations/microsoft/client.py för
planerad funktionalitet.
"""

from app.db.models import IntegrationCredential


class MicrosoftIntegration:
    async def verify(self, credential: IntegrationCredential) -> tuple[bool, str]:
        return False, "Microsoft 365-integration är inte implementerad än"

    async def fetch_report_data(self, credential: IntegrationCredential) -> dict:
        raise NotImplementedError("Microsoft 365-integration kommer i nästa version")
