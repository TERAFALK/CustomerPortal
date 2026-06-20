"""
Integrations-registry.

Designprincip: UniFi är INTE speciellt — det är en integration bland andra,
precis som Microsoft 365, Acronis och Cloudfactory. En kund kan ha noll,
en eller flera integrationer konfigurerade. Rapport-generatorn bygger
rapporten dynamiskt utifrån vilka integrationer som faktiskt är
konfigurerade OCH verifierade för kunden — aldrig platshållardata för
integrationer som saknas.

Varje integration implementerar:
  - verify(credential) -> bool          : testar att credentials funkar
  - fetch_report_data(credential) -> dict : hämtar data för rapporten

Att lägga till en ny integration (t.ex. Acronis på riktigt) innebär:
  1. Implementera verify() och fetch_report_data() i modulen
  2. Registrera den i INTEGRATIONS nedan
  3. Lägga till en sektion i PDF-mallen (reports/pdf_generator.py)
Inget annat i kodbasen behöver ändras.
"""

from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol

from app.db.models import IntegrationCredential


@dataclass
class IntegrationMeta:
    key: str            # "unifi" | "microsoft" | "acronis" | "cloudfactory"
    display_name: str
    icon: str            # tabler-icons class, för frontend-konsistens
    description: str


class IntegrationClient(Protocol):
    async def verify(self, credential: IntegrationCredential) -> tuple[bool, str]:
        """Returnerar (lyckades, meddelande)."""
        ...

    async def fetch_report_data(self, credential: IntegrationCredential) -> dict:
        """Returnerar data redo att läggas in i rapport-kontexten."""
        ...


INTEGRATIONS: dict[str, IntegrationMeta] = {
    "unifi": IntegrationMeta(
        key="unifi",
        display_name="UniFi",
        icon="ti-router",
        description="Nätverksenheter, WAN-status och ISP-mått via UniFi Site Manager API",
    ),
    "microsoft": IntegrationMeta(
        key="microsoft",
        display_name="Microsoft 365",
        icon="ti-brand-windows",
        description="Licensöversikt, MFA-status och säkerhetspoäng",
    ),
    "acronis": IntegrationMeta(
        key="acronis",
        display_name="Acronis Backup",
        icon="ti-shield",
        description="Backup-status och skyddade enheter",
    ),
    "cloudfactory": IntegrationMeta(
        key="cloudfactory",
        display_name="Cloudfactory",
        icon="ti-package",
        description="Licens- och tjänstedata",
    ),
}


def get_client(integration_type: str) -> IntegrationClient:
    """Returnerar rätt klient-instans för en integrationstyp."""
    if integration_type == "unifi":
        from app.integrations.unifi.adapter import UnifiIntegration
        return UnifiIntegration()
    if integration_type == "microsoft":
        from app.integrations.microsoft.adapter import MicrosoftIntegration
        return MicrosoftIntegration()
    if integration_type == "acronis":
        from app.integrations.acronis.adapter import AcronisIntegration
        return AcronisIntegration()
    if integration_type == "cloudfactory":
        from app.integrations.cloudfactory.adapter import CloudfactoryIntegration
        return CloudfactoryIntegration()
    raise ValueError(f"Okänd integrationstyp: {integration_type}")
