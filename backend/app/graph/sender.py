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

import asyncio
import logging
import time

import httpx

from app.core import app_settings

logger = logging.getLogger(__name__)

GRAPH_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"

# Enkel token-cache i minnet. Nyckel = (tenant, client) så att ändrade Graph-
# inställningar automatiskt ger en ny token. Förnyas 60 s innan utgång.
_token_cache: dict[tuple[str, str], tuple[str, float]] = {}
_token_lock = asyncio.Lock()


def invalidate_token() -> None:
    """Töm token-cachen — anropas t.ex. vid 401 från Graph."""
    _token_cache.clear()


async def _get_token() -> str:
    tenant = app_settings.get("graph_tenant_id")
    client_id = app_settings.get("graph_client_id")
    key = (tenant, client_id)

    cached = _token_cache.get(key)
    if cached and time.time() < cached[1] - 60:
        return cached[0]

    async with _token_lock:
        # Kontrollera igen — någon annan kan ha förnyat medan vi väntade på låset
        cached = _token_cache.get(key)
        if cached and time.time() < cached[1] - 60:
            return cached[0]

        async with httpx.AsyncClient() as client:
            r = await client.post(
                GRAPH_TOKEN_URL.format(tenant=tenant),
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": app_settings.get("graph_client_secret"),
                    "scope": "https://graph.microsoft.com/.default",
                },
            )
            r.raise_for_status()
            data = r.json()

        token = data["access_token"]
        expires_at = time.time() + float(data.get("expires_in", 3600))
        _token_cache[key] = (token, expires_at)
        return token
