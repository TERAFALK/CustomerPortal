"""Rate limiter.

Nyckelfunktionen identifierar i första hand den inloggade användaren (robust
bakom omvänd proxy där alla klienter annars delar proxyns IP). Faller tillbaka
på klientens IP via X-Forwarded-For för oautentiserade endpoints (t.ex. login).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def _rate_key(request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            from app.core.security import decode_token
            return "user:" + decode_token(auth[7:])
        except Exception:
            pass
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return "ip:" + xff.split(",")[0].strip()
    return "ip:" + get_remote_address(request)


# Med REDIS_URL delas rate-limit-räknarna mellan repliker; annars in-memory per process.
_limiter_kwargs = {"key_func": _rate_key}
if settings.REDIS_URL:
    _limiter_kwargs["storage_uri"] = settings.REDIS_URL

limiter = Limiter(**_limiter_kwargs)
