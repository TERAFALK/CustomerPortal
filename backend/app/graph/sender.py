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

import base64
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GRAPH_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
GRAPH_SEND_URL = "https://graph.microsoft.com/v1.0/users/{sender}/sendMail"


async def _get_token() -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            GRAPH_TOKEN_URL.format(tenant=settings.GRAPH_TENANT_ID),
            data={
                "grant_type": "client_credentials",
                "client_id": settings.GRAPH_CLIENT_ID,
                "client_secret": settings.GRAPH_CLIENT_SECRET,
                "scope": "https://graph.microsoft.com/.default",
            },
        )
        r.raise_for_status()
        return r.json()["access_token"]


async def send_report_email(
    to_email: str,
    to_name: str,
    subject: str,
    body_html: str,
    pdf_path: str,
    pdf_filename: str,
) -> None:
    """
    Skickar ett e-postmeddelande med bifogad PDF-rapport via Microsoft Graph.

    Raises httpx.HTTPStatusError vid fel från Graph API.
    """
    if not settings.GRAPH_TENANT_ID:
        logger.warning("Graph inte konfigurerat — hoppar över e-postutskick till %s", to_email)
        return

    token = await _get_token()

    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_html},
            "toRecipients": [{"emailAddress": {"address": to_email, "name": to_name}}],
            "attachments": [
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": pdf_filename,
                    "contentType": "application/pdf",
                    "contentBytes": pdf_b64,
                }
            ],
        },
        "saveToSentItems": False,
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(
            GRAPH_SEND_URL.format(sender=settings.GRAPH_SENDER),
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        r.raise_for_status()

    logger.info("Rapport skickad till %s via Graph", to_email)
