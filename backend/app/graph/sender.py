"""
Microsoft Graph e-postutskick via noreply@terafalk.com.

Kräver en Azure Entra ID App Registration med:
  - API permission: Mail.Send (Application, inte Delegated)
  - En client secret

Setup-guide:
  1. portal.azure.com → Entra ID → App registrations → New registration
  2. Namn: "TERAFALK Portal", Supported account types: Single tenant
  3. API permissions → Add → Microsoft Graph → Application → Mail.Send → Grant admin consent
  4. Certificates & secrets → New client secret → kopiera värdet till .env
  5. Overview → kopiera Application (client) ID och Directory (tenant) ID till .env
"""

import logging

import httpx

from app.core import app_settings

logger = logging.getLogger(__name__)

GRAPH_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"


async def _get_token() -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            GRAPH_TOKEN_URL.format(tenant=app_settings.get("graph_tenant_id")),
            data={
                "grant_type": "client_credentials",
                "client_id": app_settings.get("graph_client_id"),
                "client_secret": app_settings.get("graph_client_secret"),
                "scope": "https://graph.microsoft.com/.default",
            },
        )
        r.raise_for_status()
        return r.json()["access_token"]
