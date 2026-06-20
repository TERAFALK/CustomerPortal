"""
UniFi-adapter — kopplar UnifiClient till det gemensamma integrationsgränssnittet.

Data struktureras per host (= en kunds Fabric/konsol). En kund kan ha flera
hosts om de t.ex. har separata lokaler med varje sin UDM. Varje host har sina
egna enheter och WANs. Oanvända WAN-portar (uptime_percentage = None) filtreras bort.
"""

import asyncio
from collections import defaultdict

import httpx

from app.core.security import decrypt
from app.db.models import IntegrationCredential
from app.integrations.unifi.client import UnifiClient


class UnifiIntegration:
    async def verify(self, credential: IntegrationCredential) -> tuple[bool, str]:
        if not credential.api_key:
            return False, "Ingen API-nyckel sparad"
        key = decrypt(credential.api_key)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    "https://api.ui.com/v1/hosts",
                    headers={"X-API-Key": key, "Accept": "application/json"},
                    params={"pageSize": 1},
                )
            if r.status_code == 200:
                return True, "OK"
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:
            return False, str(e)

    async def fetch_report_data(self, credential: IntegrationCredential) -> dict:
        if not credential.api_key:
            raise ValueError("Ingen UniFi API-nyckel konfigurerad")
        api_key = decrypt(credential.api_key)
        return await asyncio.to_thread(self._fetch_sync, api_key)

    @staticmethod
    def _fetch_sync(api_key: str) -> dict:
        with UnifiClient(api_key) as client:
            sites = client.list_sites()
            host_groups = client.list_devices_grouped()
            isp_metrics = None
            if sites:
                try:
                    isp_metrics = client.query_isp_metrics(
                        site_id=sites[0].site_id,
                        host_id=sites[0].host_id,
                    )
                except Exception:
                    pass

        # Gruppera site-statistik per host_id
        sites_by_host: dict = defaultdict(list)
        for s in sites:
            sites_by_host[s.host_id].append(s)

        hosts = []
        all_devices_flat = []

        for hg in host_groups:
            host_id = hg["host_id"]
            host_name = hg["host_name"]
            devices = hg["devices"]
            host_sites = sites_by_host.get(host_id, [])

            # Aggregera stats från alla siter för denna host
            total_devices = sum(s.total_devices for s in host_sites) or len(devices)
            offline_devices = sum(s.offline_devices for s in host_sites)
            pending_updates = sum(s.pending_updates for s in host_sites)
            ips_rules = next(
                (s.ips_rules_count for s in host_sites if s.ips_rules_count), None
            )

            # Samla WANs från alla siter — filtrera bort oanvända portar
            raw_wans = []
            for s in host_sites:
                raw_wans.extend(s.wans)
            active_wans = [w for w in raw_wans if w.uptime_percentage is not None]

            device_list = [
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
            ]

            hosts.append({
                "host_id": host_id,
                "host_name": host_name,
                "total_devices": total_devices,
                "offline_devices": offline_devices,
                "pending_updates": pending_updates,
                "ips_rules_count": ips_rules,
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
                    for w in active_wans
                ],
                "devices": device_list,
            })
            all_devices_flat.extend(device_list)

        return {
            "integration": "unifi",
            "available": True,
            "hosts": hosts,
            "devices": all_devices_flat,  # flat lista för PDF-compat
            "total_devices": sum(h["total_devices"] for h in hosts),
            "offline_devices": sum(h["offline_devices"] for h in hosts),
            "isp_metrics_raw": isp_metrics,
        }
