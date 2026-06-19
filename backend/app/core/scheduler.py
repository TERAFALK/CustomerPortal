"""
Schemaläggare för automatiska månadsrapporter.
APScheduler kör i bakgrunden inuti FastAPI-processen.
Kan enkelt bytas mot en extern celery-worker om behovet växer.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings

logger = logging.getLogger(__name__)
_scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    async def _run_monthly_reports():
        # Importeras här för att undvika cirkulära importer
        from app.reports.runner import run_all_reports
        logger.info("Schemalagd rapportkörning startar")
        await run_all_reports()

    _scheduler.add_job(
        _run_monthly_reports,
        trigger=CronTrigger(
            day=settings.REPORT_SCHEDULE_DAY,
            hour=settings.REPORT_SCHEDULE_HOUR,
            minute=settings.REPORT_SCHEDULE_MINUTE,
        ),
        id="monthly_reports",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Scheduler startad — rapporter körs dag %s kl %02d:%02d",
        settings.REPORT_SCHEDULE_DAY,
        settings.REPORT_SCHEDULE_HOUR,
        settings.REPORT_SCHEDULE_MINUTE,
    )
