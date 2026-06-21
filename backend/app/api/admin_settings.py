"""Admin-endpoints för att läsa och uppdatera app-inställningar."""

from fastapi import APIRouter, Depends

from app.api.auth import require_admin
from app.core import app_settings
from app.db.models import User

router = APIRouter()

_SECRET_PLACEHOLDER = "••••••••"


@router.get("")
async def get_settings(_: User = Depends(require_admin)):
    return app_settings.all_settings(mask_secrets=True)


@router.put("")
async def update_settings(body: dict, _: User = Depends(require_admin)):
    for key, value in body.items():
        if not isinstance(value, str):
            continue
        if value == _SECRET_PLACEHOLDER or value == "":
            continue  # hoppa över oförändrade/tomma secrets
        await app_settings.update(key, value)
    return app_settings.all_settings(mask_secrets=True)
