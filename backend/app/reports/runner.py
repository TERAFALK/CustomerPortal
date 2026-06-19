"""
Rapport-runner: hämtar data från UniFi, genererar PDF och skickar via Graph.
"""

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import decrypt
from app.db.database import AsyncSessionLocal
from app.db.models import Customer, IntegrationCredential, Report
from app.graph.sender import send_report_email
from app.reports.pdf_generator import generate_pdf

logger = logging.getLogger(__name__)


async def run_all_reports() -> None:
    async with AsyncSessionLocal() as db:
        customers = (
            await db.scalars(
                select(Customer)
                .where(Customer.is_active == True)
                .options(selectinload(Customer.credentials))
            )
        ).all()

    for customer in customers:
        try:
            await run_report_for_customer(customer.id)
        except Exception as e:
            logger.error("Rapport misslyckades för %s: %s", customer.name, e)


async def run_report_for_customer(customer_id: str) -> None:
    async with AsyncSessionLocal() as db:
        customer = await db.scalar(
            select(Customer)
            .where(Customer.id == customer_id)
            .options(selectinload(Customer.credentials))
        )
        if not customer:
            logger.error("Kund %s hittades inte", customer_id)
            return

        period = datetime.now(timezone.utc).strftime("%Y-%m")

        # Hämta UniFi-data
        unifi_cred = next(
            (c for c in customer.credentials if c.integration_type == "unifi"), None
        )
        if not unifi_cred or not unifi_cred.api_key:
            logger.warning("Ingen UniFi-nyckel för %s — hoppar över", customer.name)
            return

        from app.unifi.client import UnifiClient
        api_key = decrypt(unifi_cred.api_key)
        with UnifiClient(api_key) as client:
            sites = client.list_sites()
            devices = client.list_devices()
            isp_metrics = None
            if sites:
                try:
                    isp_metrics = client.query_isp_metrics(
                        site_id=sites[0].site_id,
                        host_id=sites[0].host_id,
                    )
                except Exception as e:
                    logger.warning("ISP-metrics misslyckades för %s: %s", customer.name, e)

        data = {
            "customer_name": customer.name,
            "contact_name": customer.contact_name,
            "period": period,
            "sites": [s.raw for s in sites],
            "devices": [d.raw for d in devices],
            "isp_metrics": isp_metrics,
            "device_summaries": [
                {
                    "name": d.name,
                    "model": d.model,
                    "product_line": d.product_line,
                    "is_online": d.is_online,
                    "firmware_version": d.firmware_version,
                    "firmware_status": d.firmware_status,
                    "needs_update": d.needs_update,
                    "adoption_time": d.adoption_time,
                }
                for d in devices
            ],
            "site_summaries": [
                {
                    "name": s.name,
                    "total_devices": s.total_devices,
                    "offline_devices": s.offline_devices,
                    "pending_updates": s.pending_updates,
                    "wifi_clients": s.wifi_clients,
                    "wired_clients": s.wired_clients,
                    "gateway_model": s.gateway_model,
                    "ips_rules_count": s.ips_rules_count,
                    "wans": [
                        {
                            "name": w.name,
                            "uptime_percentage": w.uptime_percentage,
                            "isp_name": w.isp_name,
                            "isp_organization": w.isp_organization,
                            "external_ip": w.external_ip,
                            "has_issues": w.has_issues,
                            "issue_count": w.issue_count,
                        }
                        for w in s.wans
                    ],
                }
                for s in sites
            ],
        }

        # Generera PDF
        pdf_path = await generate_pdf(data, customer_id, period)

        # Skapa rapport-post i databasen
        report = Report(
            customer_id=customer_id,
            period=period,
            pdf_path=pdf_path,
            data_snapshot=json.dumps(data, ensure_ascii=False, default=str),
        )
        db.add(report)
        await db.flush()

        # Skicka via Graph
        month_names = {
            "01": "januari", "02": "februari", "03": "mars", "04": "april",
            "05": "maj", "06": "juni", "07": "juli", "08": "augusti",
            "09": "september", "10": "oktober", "11": "november", "12": "december",
        }
        year, month_num = period.split("-")
        month_sv = month_names.get(month_num, month_num)

        try:
            await send_report_email(
                to_email=customer.contact_email,
                to_name=customer.contact_name or customer.name,
                subject=f"Nätverksrapport {month_sv} {year} — {customer.name}",
                body_html=_email_body(customer.name, month_sv, year),
                pdf_path=pdf_path,
                pdf_filename=f"terafalk-rapport-{period}-{customer.name.lower().replace(' ', '-')}.pdf",
            )
            report.send_status = "sent"
            report.sent_at = datetime.now(timezone.utc)
        except Exception as e:
            logger.error("Graph-utskick misslyckades för %s: %s", customer.name, e)
            report.send_status = "error"
            report.error_message = str(e)

        await db.commit()
        logger.info("Rapport klar för %s (%s)", customer.name, period)


def _email_body(customer_name: str, month: str, year: str) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#141414">
      <div style="background:#0047A3;padding:24px 28px;border-radius:8px 8px 0 0">
        <svg xmlns="http://www.w3.org/2000/svg" width="80" height="38" viewBox="0 0 91 43" fill="none">
          <path d="M0.0117188 0.308043H41.9517V7.80805H24.7317V42.308H17.2317V7.80805H0.0117188V0.308043ZM59.34 0.248044H90.06V7.74804H59.4C57.3 7.74804 55.56 9.48805 55.56 11.588V15.488H82.56V22.988H55.5V42.248H48.06V11.588C48.06 5.34805 53.1 0.248044 59.34 0.248044Z" fill="white"/>
        </svg>
      </div>
      <div style="background:#fff;padding:28px;border:1px solid #e0e9f5;border-top:none;border-radius:0 0 8px 8px">
        <p style="margin:0 0 16px">Hej {customer_name},</p>
        <p style="margin:0 0 16px">Bifogat finns er månadsrapport för <strong>{month} {year}</strong> från TERAFALK:s Managed Network-tjänst.</p>
        <p style="margin:0 0 16px">Rapporten innehåller:</p>
        <ul style="margin:0 0 16px;padding-left:20px">
          <li>Status för alla era nätverksenheter</li>
          <li>WAN-uptime och ISP-mått</li>
          <li>Firmware-status och genomförda uppdateringar</li>
          <li>IPS-skyddsstatus</li>
        </ul>
        <p style="margin:0 0 24px">Har ni frågor är ni välkomna att kontakta oss.</p>
        <p style="margin:0;font-size:12px;color:#666">TERAFALK AB · admin@terafalk.com<br>Detta är ett automatiskt utskick — svara inte på detta e-postmeddelande.</p>
      </div>
    </div>
    """
