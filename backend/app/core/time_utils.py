from datetime import datetime
from zoneinfo import ZoneInfo

TZ_STOCKHOLM = ZoneInfo("Europe/Stockholm")


def now_stockholm() -> datetime:
    """Aktuell tid i Europe/Stockholm (hanterar sommar/vintertid automatiskt)."""
    return datetime.now(TZ_STOCKHOLM)
