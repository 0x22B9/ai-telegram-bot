import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.mongo import MongoStorage

from src.config import config
from src.middlewares import LanguageMiddleware
from src.db import connect_db, close_db
from src.handlers import (
    common_router, text_router, image_router,
    settings_router, image_generation_router, audio_router,
    document_router, privacy_router
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

async def on_startup(dispatcher: Dispatcher, bot: Bot):
    """Actions when the bot starts up."""
    if not await connect_db():
        logger.critical("Cannot connect to MongoDB. Some bot features may not work.")
    else:
        logger.info("DB succesfully connected.")
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook deleted. Bot started.")

async def on_shutdown(dispatcher: Dispatcher):
    """Actions when the bot stops."""
    logger.info("Bot stopping...")
    await close_db()
    await dispatcher.storage.close()
    logger.info("FSM Storage closed. Bot stopped.")

async def main():
    if not config:
        logger.critical("Bot can't start. No config found.")
        return

    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    try:
        storage = MongoStorage.from_url(url=config.mongo.uri)
        logger.info("Using MongoStorage for FSM (DB from URI)")
    except Exception as e:
        logger.critical(f"Cannot initialize MongoStorage from URI: {e}", exc_info=True)
        return

    dp = Dispatcher(storage=storage)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    dp.update.outer_middleware(LanguageMiddleware())
    logger.info("LanguageMiddleware() registered.")

    logger.info("Connecting routers...")
    dp.include_router(common_router)
    dp.include_router(settings_router)
    dp.include_router(image_generation_router)
    dp.include_router(document_router)
    dp.include_router(privacy_router)
    dp.include_router(audio_router)
    dp.include_router(image_router)
    dp.include_router(text_router)
    logger.info("Routers connected.")

    logger.info("Polling started...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Critical error while polling: {e}", exc_info=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user (KeyboardInterrupt/SystemExit).")