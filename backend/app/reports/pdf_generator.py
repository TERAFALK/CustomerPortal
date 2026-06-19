"""
PDF-generering med WeasyPrint och en HTML-mall i TERAFALK:s design.
"""

import os
from datetime import datetime

from jinja2 import Environment, BaseLoader

from app.core.config import settings

TERAFALK_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="47" viewBox="0 0 91 43" fill="none">
<path d="M0.0117188 0.308043H41.9517V7.80805H24.7317V42.308H17.2317V7.80805H0.0117188V0.308043ZM59.34 0.248044H90.06V7.74804H59.4C57.3 7.74804 55.56 9.48805 55.56 11.588V15.488H82.56V22.988H55.5V42.248H48.06V11.588C48.06 5.34805 53.1 0.248044 59.34 0.248044Z" fill="white"/>
</svg>"""

PDF_TEMPLATE = """<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@300;400;600;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Exo 2',Arial,sans-serif;color:#141414;font-size:13px;line-height:1.5;background:#fff}

.page{max-width:760px;margin:0 auto;padding:0}

/* Header */
.header{background:#0047A3;padding:28px 36px;display:flex;align-items:center;justify-content:space-between}
.header-right{text-align:right;color:rgba(255,255,255,0.7);font-size:11px}
.header-right .period{font-size:14px;font-weight:700;color:#fff;display:block;margin-bottom:2px}

/* Hero */
.hero{background:#F4F8FF;padding:24px 36px;border-bottom:2px solid #0047A3}
.hero-customer{font-size:22px;font-weight:700;color:#0047A3;margin-bottom:2px}
.hero-sub{font-size:12px;color:#666;margin-bottom:16px}
.hero-stats{display:flex;gap:0}
.hs{flex:1;padding:14px 16px;background:#fff;border:1px solid #dde8f5;border-left:3px solid #0047A3}
.hs:not(:first-child){border-left-color:#dde8f5;margin-left:8px}
.hs:first-child{border-left-color:#0047A3}
.hs-val{font-size:24px;font-weight:700;color:#141414}
.hs-lbl{font-size:10px;color:#888;font-weight:600;text-transform:uppercase;letter-spacing:0.07em;margin-top:2px}

/* Content */
.content{padding:28px 36px}

.section{margin-bottom:24px}
.section-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#0047A3;border-bottom:1px solid #dde8f5;padding-bottom:6px;margin-bottom:12px}

/* WAN */
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

/* ISP metrics */
.metrics-row{display:flex;gap:10px;margin-bottom:10px}
.mbox{flex:1;background:#F4F8FF;border-radius:6px;padding:12px 14px;text-align:center}
.mbox-val{font-size:20px;font-weight:700}
.mbox-lbl{font-size:10px;color:#888;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-top:2px}

/* Devices table */
table{width:100%;border-collapse:collapse}
th{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#888;padding:8px 10px;text-align:left;border-bottom:2px solid #dde8f5}
td{padding:9px 10px;font-size:12px;border-bottom:1px solid #f0f4fa}
tr:last-child td{border-bottom:none}
.dev-name{font-weight:700}
.dev-sub{font-size:11px;color:#999}
.badge-sm{font-size:10px;font-weight:600;padding:2px 7px;border-radius:10px}
.b-ok{background:#ECFDF5;color:#15803D}
.b-warn{background:#FFFBEB;color:#92400E}
.b-net{background:#EEF4FF;color:#0047A3}
.b-prot{background:#F0F9FF;color:#0369a1}
.fw-ok{color:#22C55E;font-weight:700}
.fw-warn{color:#F59E0B;font-weight:700}

/* IPS */
.ips-box{background:#F4F8FF;border-left:3px solid #0047A3;padding:12px 16px;border-radius:0 6px 6px 0}
.ips-val{font-size:18px;font-weight:700;color:#0047A3}
.ips-lbl{font-size:11px;color:#666;margin-top:2px}

/* Service box */
.service-box{background:#F1F9F0;border:1px solid #BBF7D0;border-radius:6px;padding:14px 16px}
.service-title{font-size:12px;font-weight:700;color:#15803D;margin-bottom:6px}
.service-items{display:flex;flex-wrap:wrap;gap:6px}
.service-item{font-size:11px;background:#fff;border:1px solid #BBF7D0;border-radius:12px;padding:3px 10px;color:#166534}

/* Footer */
.footer{background:#141414;padding:18px 36px;display:flex;align-items:center;justify-content:space-between}
.footer-left{font-size:11px;color:rgba(255,255,255,0.5)}
.footer-right{font-size:11px;color:rgba(255,255,255,0.35);text-align:right}

@media print{
  .page{max-width:100%}
  body{font-size:11px}
}
</style>
</head>
<body>
<div class="page">

<div class="header">
  {{ logo }}
  <div class="header-right">
    <span class="period">{{ period_label }}</span>
    Managed Network-rapport
  </div>
</div>

<div class="hero">
  <div class="hero-customer">{{ customer_name }}</div>
  <div class="hero-sub">Rapport genererad {{ generated_date }} · TERAFALK AB Managed Network</div>
  <div class="hero-stats">
    <div class="hs">
      <div class="hs-val">{{ total_devices }}</div>
      <div class="hs-lbl">Enheter</div>
    </div>
    <div class="hs">
      <div class="hs-val">{{ wan_uptime }}%</div>
      <div class="hs-lbl">WAN-uptime</div>
    </div>
    <div class="hs">
      <div class="hs-val">{{ avg_latency }} ms</div>
      <div class="hs-lbl">Snittlatens</div>
    </div>
    <div class="hs">
      <div class="hs-val">{{ offline_devices }}</div>
      <div class="hs-lbl">Offline</div>
    </div>
  </div>
</div>

<div class="content">

  <!-- WAN-status -->
  <div class="section">
    <div class="section-title">WAN-status & ISP</div>
    {% for wan in wans %}
    <div class="wan-row">
      <span class="wan-name">{{ wan.name }}</span>
      {% if wan.uptime_percentage == 100 %}
        <span class="wan-badge wan-ok">Online</span>
      {% else %}
        <span class="wan-badge wan-dn">Nere</span>
      {% endif %}
      <div class="upbar-bg">
        <div class="upbar {% if wan.uptime_percentage == 100 %}upbar-ok{% else %}upbar-dn{% endif %}"
             style="width:{{ wan.uptime_percentage or 0 }}%"></div>
      </div>
      <span class="wan-pct">{{ wan.uptime_percentage or 0 }}%</span>
      <span class="wan-isp">{{ wan.isp_name or '' }}</span>
    </div>
    {% if wan.has_issues %}
    <div class="wan-alert">⚠ {{ wan.name }} har haft {{ wan.issue_count }} avbrottstillfällen under perioden</div>
    {% endif %}
    {% endfor %}
  </div>

  <!-- ISP-mått -->
  {% if isp_avg_latency is not none %}
  <div class="section">
    <div class="section-title">ISP-mått (perioden)</div>
    <div class="metrics-row">
      <div class="mbox"><div class="mbox-val">{{ isp_avg_latency }} ms</div><div class="mbox-lbl">Snittlatens</div></div>
      <div class="mbox"><div class="mbox-val">{{ isp_packet_loss }}%</div><div class="mbox-lbl">Paketförlust</div></div>
      <div class="mbox"><div class="mbox-val">{{ isp_uptime }}%</div><div class="mbox-lbl">ISP-uptime</div></div>
      <div class="mbox"><div class="mbox-val">{{ isp_dl }} / {{ isp_ul }} Mbit</div><div class="mbox-lbl">Ner / Upp</div></div>
    </div>
  </div>
  {% endif %}

  <!-- Enheter -->
  <div class="section">
    <div class="section-title">Enheter ({{ total_devices }})</div>
    <table>
      <thead>
        <tr>
          <th>Enhet</th>
          <th>Modell</th>
          <th>Typ</th>
          <th>Firmware</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {% for d in device_summaries %}
        <tr>
          <td><div class="dev-name">{{ d.name }}</div></td>
          <td style="color:#555">{{ d.model or '—' }}</td>
          <td>
            {% if d.product_line == 'protect' %}
              <span class="badge-sm b-prot">Protect</span>
            {% else %}
              <span class="badge-sm b-net">Nätverk</span>
            {% endif %}
          </td>
          <td style="font-family:monospace;font-size:11px">
            {{ d.firmware_version or '—' }}
            {% if d.needs_update %}
              <span class="fw-warn">↑ upd</span>
            {% else %}
              <span class="fw-ok">✓</span>
            {% endif %}
          </td>
          <td>
            {% if d.is_online %}
              <span class="badge-sm b-ok">Online</span>
            {% else %}
              <span class="badge-sm" style="background:#FFF1F2;color:#BE123C">Offline</span>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- IPS -->
  {% if ips_rules %}
  <div class="section">
    <div class="section-title">Säkerhet — IPS</div>
    <div class="ips-box">
      <div class="ips-val">{{ ips_rules | int }}</div>
      <div class="ips-lbl">Aktiva IPS-regler (Emergingthreats-signaturdatabas) · trafiken inspekteras i realtid</div>
    </div>
  </div>
  {% endif %}

  <!-- Vad ingår -->
  <div class="section">
    <div class="service-box">
      <div class="service-title">Vad ingår i Managed Network</div>
      <div class="service-items">
        <span class="service-item">Firmware-patchning</span>
        <span class="service-item">24/7 övervakning</span>
        <span class="service-item">IPS-uppdateringar</span>
        <span class="service-item">WAN-monitoring</span>
        <span class="service-item">Fri felsökningstid</span>
        <span class="service-item">Månadsrapporter</span>
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


async def generate_pdf(data: dict, customer_id: str, period: str) -> str:
    """Genererar en PDF-rapport och returnerar filsökvägen."""
    from weasyprint import HTML as WeasyprintHTML

    # Bygg template-kontext
    site = data["site_summaries"][0] if data["site_summaries"] else {}
    wans = site.get("wans", [])

    # Beräkna ISP-snitt från metrics
    isp_avg_latency = None
    isp_packet_loss = None
    isp_uptime = None
    isp_dl = None
    isp_ul = None
    metrics = data.get("isp_metrics")
    if metrics:
        try:
            periods = metrics["data"]["metrics"][0]["periods"]
            latencies = [p["data"]["wan"].get("avgLatency", 0) for p in periods if p.get("data", {}).get("wan")]
            losses = [p["data"]["wan"].get("packetLoss", 0) for p in periods if p.get("data", {}).get("wan")]
            uptimes = [p["data"]["wan"].get("uptime", 100) for p in periods if p.get("data", {}).get("wan")]
            dls = [p["data"]["wan"].get("download_kbps", 0) for p in periods if p.get("data", {}).get("wan")]
            uls = [p["data"]["wan"].get("upload_kbps", 0) for p in periods if p.get("data", {}).get("wan")]
            if latencies:
                isp_avg_latency = round(sum(latencies) / len(latencies))
                isp_packet_loss = round(sum(losses) / len(losses), 1)
                isp_uptime = round(sum(uptimes) / len(uptimes), 2)
                isp_dl = round(sum(dls) / len(dls) / 1000)
                isp_ul = round(sum(uls) / len(uls) / 1000)
        except Exception:
            pass

    month_names = {
        "01": "januari", "02": "februari", "03": "mars", "04": "april",
        "05": "maj", "06": "juni", "07": "juli", "08": "augusti",
        "09": "september", "10": "oktober", "11": "november", "12": "december",
    }
    year, month_num = period.split("-")
    period_label = f"{month_names.get(month_num, month_num).capitalize()} {year}"

    wan_uptime = wans[0].get("uptime_percentage", 100) if wans else 100

    ctx = {
        "logo": TERAFALK_LOGO_SVG,
        "customer_name": data["customer_name"],
        "period_label": period_label,
        "generated_date": datetime.now().strftime("%Y-%m-%d"),
        "total_devices": site.get("total_devices", len(data["device_summaries"])),
        "offline_devices": site.get("offline_devices", 0),
        "wan_uptime": wan_uptime,
        "avg_latency": isp_avg_latency or "—",
        "wans": wans,
        "isp_avg_latency": isp_avg_latency,
        "isp_packet_loss": isp_packet_loss,
        "isp_uptime": isp_uptime,
        "isp_dl": isp_dl,
        "isp_ul": isp_ul,
        "device_summaries": data["device_summaries"],
        "ips_rules": site.get("ips_rules_count"),
    }

    env = Environment(loader=BaseLoader())
    tmpl = env.from_string(PDF_TEMPLATE)
    html_content = tmpl.render(**ctx)

    os.makedirs(settings.REPORTS_OUTPUT_DIR, exist_ok=True)
    pdf_path = os.path.join(settings.REPORTS_OUTPUT_DIR, f"{customer_id}_{period}.pdf")
    WeasyprintHTML(string=html_content).write_pdf(pdf_path)
    return pdf_path
