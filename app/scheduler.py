from __future__ import annotations

import logging

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db import get_engine
from app.timing import MSK

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        jobstores = {
            "default": SQLAlchemyJobStore(engine=get_engine(), tablename="apscheduler_jobs")
        }
        executors = {"default": AsyncIOExecutor()}
        job_defaults = {
            "misfire_grace_time": 3600,
            "coalesce": True,
            "max_instances": 1,
        }
        _scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=MSK,
        )
        log.info("Scheduler initialised (shared engine)")
    return _scheduler
