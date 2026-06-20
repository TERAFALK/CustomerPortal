"""
PDF-generering med WeasyPrint. Bygger rapporten sektion för sektion utifrån
vilka integrationer som faktiskt finns i `sections` — ingen sektion renderas
om motsvarande integration saknas eller inte är verifierad för kunden.
"""

import os
from datetime import datetime

from jinja2 import Environment, BaseLoader

from app.core.config import settings

TERAFALK_LOGO_SVG = """<svg viewBox="0 0 695.39 84.24" width="170" height="20" xmlns="http://www.w3.org/2000/svg">
<path fill="#141414" d="M236.18,455.57v15H201.74v69h-15v-69H152.3v-15Z" transform="translate(-152.3 -455.45)"/>
<path fill="#141414" d="M263.3,478.13v7.8h54v15h-54v15.84a7.74,7.74,0,0,0,7.68,7.68H332.3v15H271a22.63,22.63,0,0,1-22.56-22.67V478.13A22.64,22.64,0,0,1,271,455.45H332.3v15H271A7.73,7.73,0,0,0,263.3,478.13Z" transform="translate(-152.3 -455.45)"/>
<path fill="#141414" d="M412.1,524.69l7.68,15H403l-7.68-15-8-15.72-.36-.72a14.87,14.87,0,0,0-12.72-7.2h-15v38.63h-15v-84h53a22.53,22.53,0,0,1,22.56,22.56,22.75,22.75,0,0,1-13.2,20.64,20,20,0,0,1-6.48,1.8Zm-14.88-38.64a7,7,0,0,0,3.12-.72,7.62,7.62,0,0,0,4.56-7,7.92,7.92,0,0,0-2.28-5.52,7.56,7.56,0,0,0-5.4-2.16h-38v15.48Z" transform="translate(-152.3 -455.45)"/>
<path fill="#141414" d="M512.78,539.44H496l-7.68-15-18.36-36-18.36,36-7.68,15H427.1l7.68-15,35.16-69,35.16,69Z" transform="translate(-152.3 -455.45)"/>
<path fill="#141414" d="M604.1,455.45v15H542.78a7.73,7.73,0,0,0-7.68,7.68v7.8h54v15H535v38.51H520.1V478.13a22.64,22.64,0,0,1,22.56-22.68Z" transform="translate(-152.3 -455.45)"/>
<path fill="#141414" d="M678.38,539.44h-16.8l-7.68-15-18.36-36-18.36,36-7.68,15H592.7l7.68-15,35.16-69,35.16,69Z" transform="translate(-152.3 -455.45)"/>
<path fill="#141414" d="M751.7,524.57v15H709.1a26.09,26.09,0,0,1-11.76-2.76,26.59,26.59,0,0,1-12.12-12.23,26.12,26.12,0,0,1-2.76-11.76V455.57h15v58.68a12,12,0,0,0,10.2,10.2Z" transform="translate(-152.3 -455.45)"/>
<path fill="#141414" d="M811,489.17l36.35,50.27H828.85l-29-40.07-21.24,19.32v20.75h-15v-84h15v43l12.36-11.28,11.16-10.2,23.39-21.48h22.2Z" transform="translate(-152.3 -455.45)"/>
</svg>"""

BASE_STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@300;400;600;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Exo 2',Arial,sans-serif;color:#141414;font-size:13px;line-height:1.5;background:#fff}
.page{max-width:760px;margin:0 auto}
.header{background:#fff;border-bottom:2px solid #0047A3;padding:24px 36px;display:flex;align-items:center;justify-content:space-between}
.header-right{text-align:right;color:#888;font-size:11px}
.header-right .period{font-size:14px;font-weight:700;color:#0047A3;display:block;margin-bottom:2px}
.hero{background:#F4F8FF;padding:22px 36px;border-bottom:1px solid #dde8f5}
.hero-customer{font-size:21px;font-weight:700;color:#141414;margin-bottom:2px}
.hero-sub{font-size:12px;color:#666;margin-bottom:14px}
.hero-chips{display:flex;gap:6px;flex-wrap:wrap}
.hero-chip{font-size:10px;font-weight:700;background:#fff;border:1px solid #BBF7D0;color:#166534;padding:3px 9px;border-radius:12px}
.content{padding:26px 36px}
.section{margin-bottom:22px}
.section-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#0047A3;border-bottom:1px solid #dde8f5;padding-bottom:6px;margin-bottom:12px;display:flex;align-items:center;gap:6px}
table{width:100%;border-collapse:collapse}
th{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#888;padding:8px 10px;text-align:left;border-bottom:2px solid #dde8f5}
td{padding:9px 10px;font-size:12px;border-bottom:1px solid #f0f4fa}
tr:last-child td{border-bottom:none}
.dev-name{font-weight:700}
.badge-sm{font-size:10px;font-weight:600;padding:2px 7px;border-radius:10px}
.b-ok{background:#ECFDF5;color:#15803D}
.b-warn{background:#FFFBEB;color:#92400E}
.b-net{background:#EEF4FF;color:#0047A3}
.b-prot{background:#F0F9FF;color:#0369a1}
.fw-ok{color:#22C55E;font-weight:700}
.fw-warn{color:#F59E0B;font-weight:700}
.wan-row{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #f0f4fa}
.wan-row:last-child{border-bottom:none}
.wan-name{font-weight:700;width:60px;flex-shrink:0}
.wan-badge{font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px;flex-shrink:0;width:64px;text-align:center}
.wan-ok{background:#ECFDF5;color:#15803D}
.wan-dn{background:#FFF1F2;color:#BE123C}
.upbar-bg{flex:1;height:5px;background:#e8eef7;border-radius:3px;overflow:hidden}
.upbar{height:100%;border-radius:3px}
.upbar-ok{background:#22C55E}
.upbar-dn{background:#EF4444}
.wan-pct{font-size:12px;font-weight:700;width:42px;text-align:right;flex-shrink:0}
.wan-isp{font-size:11px;color:#888;flex-shrink:0}
.wan-alert{background:#FFF1F2;border:1px solid #FECDD3;border-radius:6px;padding:8px 12px;font-size:12px;color:#BE123C;margin-top:8px}
.metrics-row{display:flex;gap:10px;margin-bottom:10px}
.mbox{flex:1;background:#F4F8FF;border-radius:6px;padding:12px 14px;text-align:center}
.mbox-val{font-size:20px;font-weight:700}
.mbox-lbl{font-size:10px;color:#888;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-top:2px}
.ips-box{background:#F4F8FF;border-left:3px solid #0047A3;padding:12px 16px;border-radius:0 6px 6px 0}
.ips-val{font-size:18px;font-weight:700;color:#0047A3}
.ips-lbl{font-size:11px;color:#666;margin-top:2px}
.service-box{background:#F1F9F0;border:1px solid #BBF7D0;border-radius:6px;padding:14px 16px}
.service-title{font-size:12px;font-weight:700;color:#15803D;margin-bottom:6px}
.service-items{display:flex;flex-wrap:wrap;gap:6px}
.service-item{font-size:11px;background:#fff;border:1px solid #BBF7D0;border-radius:12px;padding:3px 10px;color:#166534}
.footer{background:#141414;padding:16px 36px;display:flex;align-items:center;justify-content:space-between}
.footer-left{font-size:11px;color:rgba(255,255,255,0.5)}
.footer-right{font-size:11px;color:rgba(255,255,255,0.35);text-align:right}
.notconf-box{background:#F8FAFC;border:1px dashed #cbd5e1;border-radius:6px;padding:12px 16px;font-size:11px;color:#94a3b8}
@media print{.page{max-width:100%}body{font-size:11px}}
"""

# ── UniFi-sektion ─────────────────────────────────────────────────────────────

UNIFI_SECTION_TEMPLATE = """
<div class="section">
  <div class="section-title">🛜 Nätverk — UniFi</div>
  {% for wan in wans %}
  <div class="wan-row">
    <span class="wan-name">{{ wan.name }}</span>
    {% if wan.uptime_percentage == 100 %}
      <span class="wan-badge wan-ok">Online</span>
    {% else %}
      <span class="wan-badge wan-dn">Nere</span>
    {% endif %}
    <div class="upbar-bg"><div class="upbar {% if wan.uptime_percentage == 100 %}upbar-ok{% else %}upbar-dn{% endif %}" style="width:{{ wan.uptime_percentage or 0 }}%"></div></div>
    <span class="wan-pct">{{ wan.uptime_percentage or 0 }}%</span>
    <span class="wan-isp">{{ wan.isp_name or '' }}</span>
  </div>
  {% if wan.has_issues %}
  <div class="wan-alert">⚠ {{ wan.name }} har haft {{ wan.issue_count }} avbrottstillfällen under perioden</div>
  {% endif %}
  {% endfor %}

  {% if isp_avg_latency is not none %}
  <div class="metrics-row" style="margin-top:14px">
    <div class="mbox"><div class="mbox-val">{{ isp_avg_latency }} ms</div><div class="mbox-lbl">Snittlatens</div></div>
    <div class="mbox"><div class="mbox-val">{{ isp_packet_loss }}%</div><div class="mbox-lbl">Paketförlust</div></div>
    <div class="mbox"><div class="mbox-val">{{ isp_uptime }}%</div><div class="mbox-lbl">ISP-uptime</div></div>
  </div>
  {% endif %}

  <div style="margin-top:14px">
    <table>
      <thead><tr><th>Enhet</th><th>Modell</th><th>Typ</th><th>Firmware</th><th>Status</th></tr></thead>
      <tbody>
        {% for d in device_summaries %}
        <tr>
          <td><div class="dev-name">{{ d.name }}</div></td>
          <td style="color:#555">{{ d.model or '—' }}</td>
          <td>{% if d.product_line == 'protect' %}<span class="badge-sm b-prot">Protect</span>{% else %}<span class="badge-sm b-net">Nätverk</span>{% endif %}</td>
          <td style="font-family:monospace;font-size:11px">{{ d.firmware_version or '—' }} {% if d.needs_update %}<span class="fw-warn">↑ upd</span>{% else %}<span class="fw-ok">✓</span>{% endif %}</td>
          <td>{% if d.is_online %}<span class="badge-sm b-ok">Online</span>{% else %}<span class="badge-sm" style="background:#FFF1F2;color:#BE123C">Offline</span>{% endif %}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  {% if ips_rules %}
  <div class="ips-box" style="margin-top:14px">
    <div class="ips-val">{{ ips_rules | int }}</div>
    <div class="ips-lbl">Aktiva IPS-regler · trafiken inspekteras i realtid</div>
  </div>
  {% endif %}
</div>
"""

# ── Sektioner för ej implementerade integrationer (visas ALDRIG med fejkdata —
#    om en integration inte är verifierad finns den helt enkelt inte i `sections`
#    och renderas aldrig. Dessa mallar används bara om/när adaptrarna är klara.) ──

MICROSOFT_SECTION_TEMPLATE = """
<div class="section">
  <div class="section-title">🪟 Microsoft 365</div>
  <div class="metrics-row">
    <div class="mbox"><div class="mbox-val">{{ total_licenses }}</div><div class="mbox-lbl">Licenser</div></div>
    <div class="mbox"><div class="mbox-val">{{ mfa_enabled_count }}/{{ active_users }}</div><div class="mbox-lbl">MFA aktiverat</div></div>
    {% if secure_score is not none %}
    <div class="mbox"><div class="mbox-val">{{ secure_score }}/{{ secure_score_max }}</div><div class="mbox-lbl">Secure Score</div></div>
    {% endif %}
  </div>
</div>
"""

ACRONIS_SECTION_TEMPLATE = """
<div class="section">
  <div class="section-title">🛡 Acronis Backup</div>
  <table>
    <thead><tr><th>Enhet</th><th>Senaste körning</th><th>Status</th><th>Skyddad data</th></tr></thead>
    <tbody>
      {% for job in jobs %}
      <tr>
        <td><div class="dev-name">{{ job.device_name }}</div></td>
        <td>{{ job.last_run or '—' }}</td>
        <td>{% if job.status == 'ok' %}<span class="badge-sm b-ok">OK</span>{% elif job.status == 'warning' %}<span class="badge-sm b-warn">Varning</span>{% else %}<span class="badge-sm" style="background:#FFF1F2;color:#BE123C">Fel</span>{% endif %}</td>
        <td>{{ job.protected_gb or '—' }} GB</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
"""

CLOUDFACTORY_SECTION_TEMPLATE = """
<div class="section">
  <div class="section-title">📦 Cloudfactory</div>
  <table>
    <thead><tr><th>Produkt</th><th>Antal</th><th>Aktiva</th><th>Förnyas</th></tr></thead>
    <tbody>
      {% for lic in licenses %}
      <tr>
        <td><div class="dev-name">{{ lic.product_name }}</div></td>
        <td>{{ lic.quantity }}</td>
        <td>{{ lic.active }}</td>
        <td>{{ lic.expires_at or '—' }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
"""

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="sv">
<head><meta charset="UTF-8"><style>{{ base_style }}</style></head>
<body>
<div class="page">
  <div class="header">
    {{ logo }}
    <div class="header-right"><span class="period">{{ period_label }}</span>Rapport från TERAFALK</div>
  </div>
  <div class="hero">
    <div class="hero-customer">{{ customer_name }}</div>
    <div class="hero-sub">Rapport genererad {{ generated_date }} · TERAFALK AB</div>
    <div class="hero-chips">
      {% for name in included_integration_names %}
      <span class="hero-chip">{{ name }}</span>
      {% endfor %}
    </div>
  </div>
  <div class="content">
    {{ rendered_sections | safe }}
    <div class="section">
      <div class="service-box">
        <div class="service-title">TERAFALK Managed Services</div>
        <div class="service-items">
          {% for item in service_items %}
          <span class="service-item">{{ item }}</span>
          {% endfor %}
        </div>
      </div>
    </div>
  </div>
  <div class="footer">
    <div class="footer-left">TERAFALK AB · admin@terafalk.com · terafalk.com</div>
    <div class="footer-right">Automatisk rapport · noreply@terafalk.com<br>{{ generated_date }}</div>
  </div>
</div>
</body>
</html>"""


def _month_label(period: str) -> str:
    names = {
        "01": "Januari", "02": "Februari", "03": "Mars", "04": "April",
        "05": "Maj", "06": "Juni", "07": "Juli", "08": "Augusti",
        "09": "September", "10": "Oktober", "11": "November", "12": "December",
    }
    year, month_num = period.split("-")
    return f"{names.get(month_num, month_num)} {year}"


def _render_unifi(data: dict, env: Environment) -> tuple[str, list[str]]:
    site = data["site_summaries"][0] if data.get("site_summaries") else {}
    wans = site.get("wans", [])
    service_items = ["Firmware-patchning", "24/7 övervakning", "IPS-uppdateringar", "WAN-monitoring", "Fri felsökningstid"]

    isp_avg_latency = isp_packet_loss = isp_uptime = None
    metrics = data.get("isp_metrics_raw")
    if metrics:
        try:
            periods = metrics["data"]["metrics"][0]["periods"]
            lat = [p["data"]["wan"].get("avgLatency", 0) for p in periods if p.get("data", {}).get("wan")]
            loss = [p["data"]["wan"].get("packetLoss", 0) for p in periods if p.get("data", {}).get("wan")]
            up = [p["data"]["wan"].get("uptime", 100) for p in periods if p.get("data", {}).get("wan")]
            if lat:
                isp_avg_latency = round(sum(lat) / len(lat))
                isp_packet_loss = round(sum(loss) / len(loss), 1)
                isp_uptime = round(sum(up) / len(up), 2)
        except Exception:
            pass

    html = env.from_string(UNIFI_SECTION_TEMPLATE).render(
        wans=wans,
        device_summaries=data.get("device_summaries", []),
        ips_rules=site.get("ips_rules_count"),
        isp_avg_latency=isp_avg_latency,
        isp_packet_loss=isp_packet_loss,
        isp_uptime=isp_uptime,
    )
    return html, service_items


def _render_microsoft(data: dict, env: Environment) -> tuple[str, list[str]]:
    html = env.from_string(MICROSOFT_SECTION_TEMPLATE).render(**data)
    return html, ["Licenshantering", "MFA-övervakning", "Säkerhetsrapportering"]


def _render_acronis(data: dict, env: Environment) -> tuple[str, list[str]]:
    html = env.from_string(ACRONIS_SECTION_TEMPLATE).render(**data)
    return html, ["Backup-övervakning", "Återställningstest"]


def _render_cloudfactory(data: dict, env: Environment) -> tuple[str, list[str]]:
    html = env.from_string(CLOUDFACTORY_SECTION_TEMPLATE).render(**data)
    return html, ["Licenshantering"]


_RENDERERS = {
    "unifi": ("UniFi", _render_unifi),
    "microsoft": ("Microsoft 365", _render_microsoft),
    "acronis": ("Acronis Backup", _render_acronis),
    "cloudfactory": ("Cloudfactory", _render_cloudfactory),
}


async def generate_pdf(customer_name: str, period: str, sections: dict, customer_id: str) -> str:
    """
    Genererar en PDF-rapport byggd uteslutande av de sektioner som finns i
    `sections` (en nyckel per verifierad och datahämtad integration).
    Returnerar filsökvägen.
    """
    from weasyprint import HTML as WeasyprintHTML

    env = Environment(loader=BaseLoader())

    rendered_html_parts = []
    included_names = []
    service_items: list[str] = []

    # Stabil ordning: unifi, microsoft, acronis, cloudfactory, sen ev. okänt
    order = ["unifi", "microsoft", "acronis", "cloudfactory"]
    keys_in_order = [k for k in order if k in sections] + [k for k in sections if k not in order]

    for key in keys_in_order:
        if key not in _RENDERERS:
            continue
        display_name, renderer = _RENDERERS[key]
        try:
            html, items = renderer(sections[key], env)
            rendered_html_parts.append(html)
            included_names.append(display_name)
            service_items.extend(items)
        except Exception:
            continue

    ctx = {
        "base_style": BASE_STYLE,
        "logo": TERAFALK_LOGO_SVG,
        "customer_name": customer_name,
        "period_label": _month_label(period),
        "generated_date": datetime.now().strftime("%Y-%m-%d"),
        "included_integration_names": included_names,
        "rendered_sections": "\n".join(rendered_html_parts),
        "service_items": sorted(set(service_items), key=service_items.index),
    }

    html_content = env.from_string(PAGE_TEMPLATE).render(**ctx)

    os.makedirs(settings.REPORTS_OUTPUT_DIR, exist_ok=True)
    pdf_path = os.path.join(settings.REPORTS_OUTPUT_DIR, f"{customer_id}_{period}.pdf")
    WeasyprintHTML(string=html_content).write_pdf(pdf_path)
    return pdf_path
