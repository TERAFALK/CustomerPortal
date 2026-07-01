"""
Microsoft Graph API-klient med client credentials flow.
"""

import csv
import io
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphClient:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        if self._token:
            return self._token
        r = await client.post(
            f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": "https://graph.microsoft.com/.default",
            },
        )
        r.raise_for_status()
        self._token = r.json()["access_token"]
        return self._token

    async def _get(self, client: httpx.AsyncClient, path: str, params: dict | None = None) -> dict:
        token = await self._get_token(client)
        r = await client.get(
            f"{GRAPH_BASE}{path}",
            headers={"Authorization": f"Bearer {token}", "ConsistencyLevel": "eventual"},
            params=params,
        )
        r.raise_for_status()
        return r.json()

    async def fetch_all(self) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            (licenses_raw, users_raw, mfa_raw, score_raw,
             roles_raw, od_csv, sp_csv, intune_raw) = await _gather(
                self._fetch_licenses(client),
                self._fetch_users(client),
                self._fetch_mfa(client),
                self._fetch_secure_score(client),
                self._fetch_admin_roles(client),
                self._fetch_onedrive_usage(client),
                self._fetch_sharepoint_usage(client),
                self._fetch_intune_devices(client),
            )

        licenses, sku_id_map = _build_licenses(licenses_raw)
        user_list, total_users, enabled_users = _build_users(users_raw, sku_id_map)
        mfa_by_upn = _build_mfa_map(mfa_raw)
        _apply_mfa_to_users(user_list, mfa_by_upn)
        mfa_registered, mfa_total = _count_mfa(user_list, mfa_by_upn)
        secure_score, secure_score_max = _extract_secure_score(score_raw)
        admin_roles = _build_admin_roles(roles_raw)
        inactive_licensed = _build_inactive_users(user_list, users_raw)
        onedrive_users, onedrive_total_gb = _build_onedrive(od_csv)
        sharepoint_sites, sharepoint_total_gb = _build_sharepoint(sp_csv)
        intune_devices = _build_intune_devices(intune_raw)

        return {
            "integration": "microsoft",
            "available": True,
            "total_users": total_users,
            "enabled_users": enabled_users,
            "users": user_list,
            "licenses": licenses,
            "mfa_registered": mfa_registered,
            "mfa_total": mfa_total,
            "mfa_available": mfa_total > 0,
            "secure_score": secure_score,
            "secure_score_max": secure_score_max,
            "admin_roles": admin_roles,
            "inactive_licensed_users": inactive_licensed,
            "onedrive_users": onedrive_users,
            "onedrive_total_gb": onedrive_total_gb,
            "sharepoint_sites": sharepoint_sites,
            "sharepoint_total_gb": sharepoint_total_gb,
            "intune_devices": intune_devices,
        }

    async def _fetch_licenses(self, client):
        return await self._get(client, "/subscribedSkus")

    async def _fetch_users(self, client):
        try:
            return await self._get(client, "/users", params={
                "$count": "true",
                "$select": "id,displayName,userPrincipalName,mail,jobTitle,accountEnabled,assignedLicenses,signInActivity",
                "$top": "999",
            })
        except Exception:
            return await self._get(client, "/users", params={
                "$count": "true",
                "$select": "id,displayName,userPrincipalName,mail,jobTitle,accountEnabled,assignedLicenses",
                "$top": "999",
            })

    async def _fetch_admin_roles(self, client):
        try:
            return await self._get(client, "/roleManagement/directory/roleAssignments", params={
                "$expand": "principal($select=displayName,userPrincipalName,id),roleDefinition($select=displayName,isBuiltIn)",
                "$top": "200",
            })
        except Exception as e:
            logger.warning("Admin-roller ej tillgängliga (kräver RoleManagement.Read.Directory): %s", e)
            return {"value": []}

    async def _fetch_onedrive_usage(self, client):
        try:
            token = await self._get_token(client)
            # Graph svarar med 302 → förautentiserad nedladdnings-URL. Följ redirecten
            # (httpx tar automatiskt bort Authorization-headern vid byte av host).
            r = await client.get(
                f"{GRAPH_BASE}/reports/getOneDriveUsageAccountDetail(period='D30')",
                headers={"Authorization": f"Bearer {token}"},
                follow_redirects=True,
            )
            r.raise_for_status()
            return r.text
        except Exception as e:
            logger.warning("OneDrive-rapport ej tillgänglig: %s", e)
            return ""

    async def _fetch_sharepoint_usage(self, client):
        try:
            token = await self._get_token(client)
            r = await client.get(
                f"{GRAPH_BASE}/reports/getSharePointSiteUsageDetail(period='D30')",
                headers={"Authorization": f"Bearer {token}"},
                follow_redirects=True,
            )
            r.raise_for_status()
            return r.text
        except Exception as e:
            logger.warning("SharePoint-rapport ej tillgänglig: %s", e)
            return ""

    async def _fetch_intune_devices(self, client):
        try:
            return await self._get(client, "/deviceManagement/managedDevices", params={
                "$select": "deviceName,userDisplayName,userPrincipalName,operatingSystem,osVersion,complianceState,lastSyncDateTime,managementState",
                "$top": "999",
            })
        except Exception as e:
            logger.warning("Intune-enheter ej tillgängliga (kräver DeviceManagementManagedDevices.Read.All): %s", e)
            return {"value": []}

    async def _fetch_mfa(self, client):
        # Försök 1: v1.0 (kräver UserAuthenticationMethod.Read.All)
        try:
            result = await self._get(client, "/reports/authenticationMethods/userRegistrationDetails", params={"$top": "999"})
            logger.info("MFA (v1.0) svarade med %d poster", len(result.get("value") or []))
            return result
        except Exception:
            pass

        # Försök 2: beta-API (kräver Reports.Read.All)
        try:
            token = await self._get_token(client)
            r = await client.get(
                "https://graph.microsoft.com/beta/reports/credentialUserRegistrationDetails",
                headers={"Authorization": f"Bearer {token}"},
                params={"$top": "999"},
            )
            r.raise_for_status()
            data = r.json()
            logger.info("MFA (beta) svarade med %d poster", len(data.get("value") or []))
            normalized = [
                {
                    "userPrincipalName": u.get("userPrincipalName", ""),
                    "isMfaRegistered": u.get("isMfaRegistered", False),
                    "isMfaCapable": u.get("isMfaRegistered", False),
                }
                for u in (data.get("value") or [])
            ]
            return {"value": normalized}
        except Exception as e:
            logger.warning("MFA-data ej tillgänglig (prövade v1.0 + beta): %s", e)
            return {"value": []}

    async def _fetch_secure_score(self, client):
        try:
            return await self._get(client, "/security/secureScores", params={"$top": "1"})
        except Exception as e:
            logger.warning("Secure Score ej tillgänglig: %s", e)
            return {"value": []}


_SKU_IGNORE = {"FLOW_FREE", "POWER_BI_STANDARD", "TEAMS_EXPLORATORY", "WINDOWS_STORE", "DEVELOPERPACK_E5"}

_HIGH_RISK_ROLES = {
    "Global Administrator", "Privileged Role Administrator",
    "Privileged Authentication Administrator", "Security Administrator",
}

_COMPLIANCE_LABEL = {
    "compliant": "Godkänd", "noncompliant": "Ej godkänd",
    "unknown": "Okänd", "notApplicable": "Ej tillämplig",
    "inGracePeriod": "Respitperiod", "configManager": "Config Manager",
}


def _build_licenses(raw: dict) -> tuple[list[dict], dict[str, str]]:
    sku_id_map: dict[str, str] = {}
    licenses: list[dict] = []
    for s in (raw.get("value") or []):
        part = s.get("skuPartNumber", "")
        sku_id = s.get("skuId", "")
        friendly = _friendly_sku(part)
        if sku_id:
            sku_id_map[sku_id] = friendly
        if part in _SKU_IGNORE or s.get("capabilityStatus") != "Enabled":
            continue
        licenses.append({
            "name": friendly,
            "sku": part,
            "sku_id": sku_id,
            "total": s.get("prepaidUnits", {}).get("enabled", 0),
            "assigned": s.get("consumedUnits", 0),
        })
    return licenses, sku_id_map


def _build_users(raw: dict, sku_id_map: dict[str, str]) -> tuple[list[dict], int, int]:
    users = raw.get("value") or []
    total_users = raw.get("@odata.count") or len(users)
    enabled_users = sum(1 for u in users if u.get("accountEnabled"))
    user_list = [
        {
            "name": u.get("displayName") or u.get("userPrincipalName", ""),
            "email": u.get("mail") or u.get("userPrincipalName", ""),
            "title": u.get("jobTitle") or "",
            "enabled": u.get("accountEnabled", False),
            "licenses": [
                sku_id_map.get(lic.get("skuId", ""), lic.get("skuId", ""))
                for lic in (u.get("assignedLicenses") or [])
                if lic.get("skuId") in sku_id_map
            ],
        }
        for u in users
    ]
    return user_list, total_users, enabled_users


def _build_mfa_map(raw: dict) -> dict[str, dict]:
    def _is_protected(u: dict) -> bool:
        return bool(
            u.get("isMfaRegistered") or u.get("isMfaCapable")
            or u.get("isPasswordlessCapable") or u.get("methodsRegistered")
        )

    return {
        u.get("userPrincipalName", "").lower(): {
            "protected": _is_protected(u),
            "methods": u.get("methodsRegistered") or [],
        }
        for u in (raw.get("value") or [])
    }


def _apply_mfa_to_users(user_list: list[dict], mfa_by_upn: dict[str, dict]) -> None:
    if not mfa_by_upn:
        return
    for u in user_list:
        info = mfa_by_upn.get(u["email"].lower())
        if info:
            u["mfa"] = info["protected"]
            u["mfa_methods"] = info["methods"]


def _count_mfa(user_list: list[dict], mfa_by_upn: dict[str, dict]) -> tuple[int, int]:
    licensed_active_upns = {
        u["email"].lower() for u in user_list if u["enabled"] and u["licenses"]
    }
    mfa_total = len(licensed_active_upns)
    mfa_registered = sum(
        1 for upn, info in mfa_by_upn.items()
        if upn in licensed_active_upns and info["protected"]
    )
    return mfa_registered, mfa_total


def _extract_secure_score(raw: dict) -> tuple:
    scores = raw.get("value") or []
    if not scores:
        return None, None
    sc = scores[0]
    return sc.get("currentScore"), sc.get("maxScore")


def _build_admin_roles(raw: dict) -> list[dict]:
    role_map: dict[str, list[str]] = {}
    for assignment in (raw.get("value") or []):
        rd = assignment.get("roleDefinition") or {}
        role_name = rd.get("displayName", "")
        principal = assignment.get("principal") or {}
        member_name = principal.get("displayName") or principal.get("userPrincipalName", "")
        if role_name and member_name:
            role_map.setdefault(role_name, []).append(member_name)
    return [
        {"role": role, "members": members, "high_risk": role in _HIGH_RISK_ROLES}
        for role, members in sorted(role_map.items())
        if members
    ]


def _build_inactive_users(user_list: list[dict], users_raw: dict) -> list[dict]:
    now_utc = datetime.now(timezone.utc)
    raw_users = users_raw.get("value") or []
    sign_in_by_email = {
        (u.get("mail") or u.get("userPrincipalName", "")).lower(): u.get("signInActivity")
        for u in raw_users
    }
    inactive: list[dict] = []
    for u in user_list:
        if not u["enabled"] or not u["licenses"]:
            continue
        sign_in = sign_in_by_email.get(u["email"].lower())
        if sign_in is None:
            continue
        last_dt_str = sign_in.get("lastSignInDateTime") if sign_in else None
        days: int | None = None
        if last_dt_str:
            try:
                last_dt = datetime.fromisoformat(last_dt_str.replace("Z", "+00:00"))
                days = (now_utc - last_dt).days
            except Exception:
                pass
        if days is None or days > 30:
            inactive.append({
                "name": u["name"],
                "email": u["email"],
                "licenses": u["licenses"],
                "last_signin_days": days,
                "never_signed_in": last_dt_str is None,
            })
    return inactive


def _build_onedrive(csv_text: str) -> tuple[list[dict], float]:
    if not csv_text:
        return [], 0.0
    users: list[dict] = []
    total_gb = 0.0
    for row in _parse_graph_report_csv(csv_text):
        if row.get("Is Deleted", "").lower() == "true":
            continue
        used = _bytes_to_gb(row.get("Storage Used (Byte)", 0))
        total_gb += used
        users.append({
            "name": row.get("Owner Display Name", "") or row.get("User Principal Name", ""),
            "email": row.get("User Principal Name", ""),
            "used_gb": used,
            "last_activity": row.get("Last Activity Date", "") or None,
        })
    users.sort(key=lambda x: x["used_gb"], reverse=True)
    return users, round(total_gb, 2)


def _build_sharepoint(csv_text: str) -> tuple[list[dict], float]:
    if not csv_text:
        return [], 0.0
    sites: list[dict] = []
    total_gb = 0.0
    for row in _parse_graph_report_csv(csv_text):
        if row.get("Is Deleted", "").lower() == "true":
            continue
        used = _bytes_to_gb(row.get("Storage Used (Byte)", 0))
        total_gb += used
        url = row.get("Site URL", "")
        name = url.rstrip("/").split("/")[-1] or url
        sites.append({
            "name": name,
            "url": url,
            "owner": row.get("Owner Display Name", ""),
            "used_gb": used,
            "last_activity": row.get("Last Activity Date", "") or None,
        })
    sites.sort(key=lambda x: x["used_gb"], reverse=True)
    return sites, round(total_gb, 2)


def _build_intune_devices(raw: dict) -> list[dict]:
    now_utc = datetime.now(timezone.utc)
    devices: list[dict] = []
    for d in (raw.get("value") or []):
        last_sync = d.get("lastSyncDateTime", "")
        sync_days: int | None = None
        try:
            sync_dt = datetime.fromisoformat(last_sync.replace("Z", "+00:00"))
            sync_days = (now_utc - sync_dt).days
        except Exception:
            pass
        compliance = d.get("complianceState", "unknown")
        os_name = d.get("operatingSystem", "")
        os_version = d.get("osVersion", "")
        if os_name.lower() == "windows":
            os_name = _windows_version(os_version)
        devices.append({
            "name": d.get("deviceName", ""),
            "user": d.get("userDisplayName", "") or d.get("userPrincipalName", ""),
            "os": os_name,
            "os_version": os_version,
            "compliance": _COMPLIANCE_LABEL.get(compliance, compliance),
            "compliance_key": compliance,
            "last_sync_days": sync_days,
        })
    devices.sort(key=lambda x: (x["compliance_key"] != "compliant", x["name"]))
    return devices


def _windows_version(os_version: str) -> str:
    """Härleder Windows 10/11 och version från byggnumret som Intune returnerar."""
    try:
        build = int(os_version.split(".")[2])
    except (IndexError, ValueError):
        return "Windows"
    if build >= 26100:
        win_ver = "Windows 11 24H2"
    elif build >= 22631:
        win_ver = "Windows 11 23H2"
    elif build >= 22621:
        win_ver = "Windows 11 22H2"
    elif build >= 22000:
        win_ver = "Windows 11"
    elif build >= 19045:
        win_ver = "Windows 10 22H2"
    elif build >= 19044:
        win_ver = "Windows 10 21H2"
    elif build >= 19043:
        win_ver = "Windows 10 21H1"
    else:
        win_ver = "Windows 10"
    return win_ver


def _parse_graph_report_csv(text: str) -> list[dict]:
    """Parsar Graph-rapport-CSV och hanterar UTF-8-BOM från Microsoft."""
    return list(csv.DictReader(io.StringIO(text.lstrip('﻿'))))


def _bytes_to_gb(value) -> float:
    try:
        return round(int(value) / 1_073_741_824, 2)
    except (TypeError, ValueError):
        return 0.0


async def _gather(*coros):
    import asyncio
    return await asyncio.gather(*coros, return_exceptions=False)


_SKU_NAMES = {
    # Microsoft 365 Business
    "O365_BUSINESS_PREMIUM": "Microsoft 365 Business Premium",
    "O365_BUSINESS_ESSENTIALS": "Microsoft 365 Business Basic",
    "O365_BUSINESS": "Microsoft 365 Apps for Business",
    "SMB_BUSINESS_PREMIUM": "Microsoft 365 Business Premium",
    "SMB_BUSINESS": "Microsoft 365 Apps for Business",
    "SMB_BUSINESS_ESSENTIALS": "Microsoft 365 Business Basic",
    "SPB": "Microsoft 365 Business Premium",
    "MICROSOFT_BUSINESS_CENTER": "Microsoft 365 Business Center",
    # Microsoft 365 Enterprise
    "SPE_E3": "Microsoft 365 E3",
    "SPE_E5": "Microsoft 365 E5",
    "SPE_F1": "Microsoft 365 F3",
    "SPE_E3_USGOV_DOD": "Microsoft 365 E3 (Gov)",
    "SPE_E3_USGOV_GCCHIGH": "Microsoft 365 E3 (Gov High)",
    # Office 365
    "ENTERPRISEPACK": "Office 365 E3",
    "ENTERPRISEPREMIUM": "Office 365 E5",
    "STANDARDPACK": "Office 365 E1",
    "DESKLESSPACK": "Office 365 F3",
    "ENTERPRISEPACK_USGOV_DOD": "Office 365 E3 (Gov)",
    # Exchange
    "EXCHANGESTANDARD": "Exchange Online (Plan 1)",
    "EXCHANGEENTERPRISE": "Exchange Online (Plan 2)",
    "EXCHANGEESSENTIALS": "Exchange Online Essentials",
    "EXCHANGE_S_DESKLESS": "Exchange Online Kiosk",
    # Teams
    "TEAMS_ESSENTIALS": "Microsoft Teams Essentials",
    "TEAMS_FREE": "Microsoft Teams (gratis)",
    "TEAMS_EXPLORATORY": "Microsoft Teams Exploratory",
    "Microsoft_Teams_Rooms_Basic": "Teams Rooms Basic",
    "Microsoft_Teams_Rooms_Standard": "Teams Rooms Standard",
    # Security & Compliance
    "EMS": "Enterprise Mobility + Security E3",
    "EMSPREMIUM": "Enterprise Mobility + Security E5",
    "AAD_PREMIUM": "Azure AD Premium P1",
    "AAD_PREMIUM_P2": "Azure AD Premium P2",
    "INTUNE_A": "Microsoft Intune Plan 1",
    "INTUNE_A_D": "Microsoft Intune Plan 2",
    "DEFENDER_ENDPOINT_P1": "Microsoft Defender for Endpoint P1",
    "DEFENDER_ENDPOINT_P2": "Microsoft Defender for Endpoint P2",
    "ATP_ENTERPRISE": "Microsoft Defender for Office 365 P1",
    "THREAT_INTELLIGENCE": "Microsoft Defender for Office 365 P2",
    "INFORMATION_PROTECTION_COMPLIANCE": "Microsoft 365 E5 Compliance",
    # Power Platform
    "POWER_BI_PRO": "Power BI Pro",
    "POWER_BI_PREMIUM_PER_USER": "Power BI Premium Per User",
    "POWER_BI_STANDARD": "Power BI (gratis)",
    "POWERAPPS_PER_USER": "Power Apps per user",
    "FLOW_PER_USER": "Power Automate per user",
    "FLOW_FREE": "Power Automate (gratis)",
    # Project & Visio
    "PROJECTPREMIUM": "Project Plan 5",
    "PROJECTPROFESSIONAL": "Project Plan 3",
    "PROJECTESSENTIALS": "Project Plan 1",
    "VISIOCLIENT": "Visio Plan 2",
    "VISIO_PLAN1_DEPT": "Visio Plan 1",
    # Copilot & AI
    "Microsoft_365_Copilot": "Microsoft 365 Copilot",
    "COPILOT_FOR_MICROSOFT_365": "Microsoft 365 Copilot",
    # Dynamics 365
    "DYN365_ENTERPRISE_SALES": "Dynamics 365 Sales Enterprise",
    "DYN365_SALES_PREMIUM_VIRAL": "Dynamics 365 Sales Premium (Trial)",
    "DYN365_TEAM_MEMBERS": "Dynamics 365 Team Members",
    "DYN365_BUSINESS_CENTRAL_ESSENTIAL": "Dynamics 365 Business Central Essential",
    "DYN365_BUSINESS_CENTRAL_PREMIUM": "Dynamics 365 Business Central Premium",
    # Other
    "DEVELOPERPACK_E5": "Microsoft 365 E5 Developer",
    "WINDOWS_STORE": "Microsoft Store for Business",
    "MCOCAP": "Microsoft Teams Phone",
    "MCOSTANDARD": "Skype for Business Online (Plan 2)",
}


def _friendly_sku(sku: str) -> str:
    if sku in _SKU_NAMES:
        return _SKU_NAMES[sku]
    # Fallback: replace underscores, fix casing (keep all-uppercase words as-is)
    parts = sku.replace("_", " ").split()
    formatted = " ".join(p if p.isupper() and len(p) > 2 else p.capitalize() for p in parts)
    return formatted
