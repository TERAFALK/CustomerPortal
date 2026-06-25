"""E-postnotifieringar för ordrar och projekt via Microsoft Graph."""

import logging
from app.core import app_settings

logger = logging.getLogger(__name__)


async def _get_setting(event_type: str):
    from app.db.database import AsyncSessionLocal
    from app.db.models import NotificationSetting
    async with AsyncSessionLocal() as db:
        return await db.get(NotificationSetting, event_type)


async def _send(to_email: str, to_name: str, subject: str, body_html: str) -> None:
    from app.graph.sender import _get_token
    import httpx

    if not app_settings.get("graph_tenant_id"):
        return

    sender = app_settings.get("support_inbox") or "support@terafalk.com"
    token = await _get_token()
    url = f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_html},
            "toRecipients": [{"emailAddress": {"address": to_email, "name": to_name}}],
        },
        "saveToSentItems": False,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
    logger.info("Ordermejl skickat till %s: %s", to_email, subject)


def _base_html(content: str) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#1a1a1a">
      <div style="background:#0047a3;padding:20px 24px;border-radius:8px 8px 0 0">
        <span style="color:#fff;font-size:18px;font-weight:700">TERAFALK</span>
      </div>
      <div style="background:#f8f9fa;padding:24px;border-radius:0 0 8px 8px;border:1px solid #e0e0e0;border-top:none">
        {content}
      </div>
      <p style="font-size:11px;color:#888;text-align:center;margin-top:12px">
        TERAFALK AB · support@terafalk.com
      </p>
    </div>
    """


async def _notify(event_type: str, order, subject: str, content: str) -> None:
    """Skicka notis baserat på konfiguration för händelsetypen."""
    cfg = await _get_setting(event_type)
    if not cfg or not cfg.enabled:
        return

    recipients: list[tuple[str, str]] = []

    if cfg.notify_customer and order.customer and order.customer.contact_email:
        recipients.append((order.customer.contact_email, order.customer.name))

    # Orderspecifika kontakter
    if cfg.notify_customer:
        for oc in (order.contacts or []):
            c = oc.contact
            if c and c.email and c.is_active:
                if c.email not in {r[0] for r in recipients}:
                    recipients.append((c.email, c.name))

    if cfg.notify_assigned and order.assigned_to and order.assigned_to.email:
        if order.assigned_to.email not in {r[0] for r in recipients}:
            recipients.append((order.assigned_to.email, order.assigned_to.full_name or order.assigned_to.email))

    if cfg.notify_internal:
        internal = cfg.internal_email or app_settings.get("support_inbox") or "support@terafalk.com"
        if internal not in {r[0] for r in recipients}:
            recipients.append((internal, "TERAFALK Support"))

    html = _base_html(content)
    for email, name in recipients:
        try:
            await _send(email, name, subject, html)
        except Exception as e:
            logger.warning("Kunde inte skicka ordermejl till %s: %s", email, e)


async def send_order_created(order) -> None:
    type_label = "Projekt" if order.type == "project" else "Order"
    content = f"""
    <h2 style="margin:0 0 16px;font-size:16px">Ny {type_label.lower()} skapad</h2>
    <div style="background:#fff;border:1px solid #e0e0e0;border-radius:6px;padding:16px;margin-bottom:16px">
      <div style="font-size:13px;color:#555">Kund</div>
      <div style="font-weight:700">{order.customer.name if order.customer else '—'}</div>
      <div style="font-size:13px;color:#555;margin-top:10px">{type_label}</div>
      <div style="font-weight:600">{order.title}</div>
    </div>
    """
    await _notify("order_created", order, f"{type_label}: {order.title}", content)


async def send_order_status_changed(order, old_status: str, new_status: str) -> None:
    type_label = "Projekt" if order.type == "project" else "Order"
    status_map = {"active": "Aktiv", "completed": "Avslutad", "cancelled": "Makulerad"}
    content = f"""
    <h2 style="margin:0 0 16px;font-size:16px">{type_label}status ändrad</h2>
    <div style="background:#fff;border:1px solid #e0e0e0;border-radius:6px;padding:16px">
      <div style="font-weight:700;color:#0047a3">{order.title}</div>
      <div style="font-size:13px;color:#555;margin-top:8px">
        Status: <em>{status_map.get(old_status, old_status)}</em> → <strong>{status_map.get(new_status, new_status)}</strong>
      </div>
    </div>
    """
    await _notify("order_status_changed", order, f"{type_label} uppdaterad: {order.title}", content)


async def send_order_phase_changed(order, old_phase: str, new_phase: str) -> None:
    type_label = "Projekt" if order.type == "project" else "Order"
    content = f"""
    <h2 style="margin:0 0 16px;font-size:16px">{type_label}fas uppdaterad</h2>
    <div style="background:#fff;border:1px solid #e0e0e0;border-radius:6px;padding:16px">
      <div style="font-weight:700;color:#0047a3">{order.title}</div>
      <div style="font-size:13px;color:#555;margin-top:8px">
        Fas: <em>{old_phase or '—'}</em> → <strong>{new_phase or '—'}</strong>
      </div>
    </div>
    """
    await _notify("order_phase_changed", order, f"{type_label} fas ändrad: {order.title}", content)
