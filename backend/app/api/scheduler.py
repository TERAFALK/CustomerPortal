from fastapi import APIRouter, Depends
from app.api.auth import current_user
from app.db.models import User
from app.core.config import settings

router = APIRouter()


@router.get("/status")
async def scheduler_status(_: User = Depends(current_user)):
    return {
        "schedule": f"Dag {settings.REPORT_SCHEDULE_DAY} varje månad kl {settings.REPORT_SCHEDULE_HOUR:02d}:{settings.REPORT_SCHEDULE_MINUTE:02d}",
        "timezone": "Europe/Stockholm",
    }
