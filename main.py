import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramNetworkError
from config import BOT_TOKEN
from database import init_db
from handlers import routers
from scheduler import setup_scheduler, shutdown_scheduler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

shutdown_event = asyncio.Event()

async def main():
    # Init DB
    init_db()
    logger.info("Database initialized")

    # Bot and Dispatcher
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register handlers
    for router in routers:
        dp.include_router(router)
    logger.info(f"Registered {len(routers)} routers")

    # Start scheduler
    setup_scheduler(bot)
    logger.info("Scheduler started")

    retry_count = 0
    max_retries = 10

    try:
        while not shutdown_event.is_set():
            try:
                logger.info("Starting polling...")
                await dp.start_polling(bot)
                # Normal exit (no error) — break loop
                break
            except TelegramNetworkError as e:
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(f"Max retries ({max_retries}) exceeded. Stopping.")
                    break
                wait_time = min(5 * retry_count, 60)
                logger.error(
                    f"Network error: {e}. Retrying in {wait_time}s... "
                    f"({retry_count}/{max_retries})"
                )
                # Wait but allow interruption via shutdown_event
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=wait_time)
                except asyncio.TimeoutError:
                    pass
            except (KeyboardInterrupt, SystemExit):
                logger.info("Shutdown requested")
                break
            except Exception:
                logger.exception("Unexpected error during polling")
                break
    finally:
        shutdown_scheduler()
        await bot.session.close()
        logger.info("Bot stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
