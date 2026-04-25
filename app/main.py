from __future__ import annotations

import asyncio
import logging

from app.bot import get_bot, get_dispatcher
from app.config import get_settings
from app.db import init_db
from app.handlers import admin, fallback, secret_word, start
from app.scheduler import get_scheduler
from app.texts import load_messages
from app.utils.logging import setup_logging

log = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    load_messages()
    log.info("messages.yaml validated")

    init_db()
    log.info("DB initialised at %s", settings.db_path)

    scheduler = get_scheduler()
    scheduler.start()
    log.info("Scheduler started (smoke_test=%s)", settings.smoke_test)

    bot = get_bot()
    dp = get_dispatcher()

    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(secret_word.router)
    dp.include_router(fallback.router)

    me = await bot.get_me()
    log.info("Bot started as @%s (id=%s)", me.username, me.id)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
