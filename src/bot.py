import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.mongo import MongoStorage

from src.config import config, load_config
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

# --- Функции для жизненного цикла ---
async def on_startup(dispatcher: Dispatcher, bot: Bot):
    """Действия при запуске бота."""
    # Подключаемся к БД
    if not await connect_db():
        logger.critical("Не удалось подключиться к базе данных. Бот не может полноценно работать.")
        # Здесь можно решить, останавливать ли бота или работать без БД
        # Например, можно поднять флаг и проверять его в хэндлерах
    else:
        logger.info("База данных успешно подключена.")
    # Удаляем вебхук
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Вебхук удален.")
    logger.info("Бот запущен.")

async def on_shutdown(dispatcher: Dispatcher):
    """Действия при остановке бота."""
    logger.info("Бот останавливается...")
    # Закрываем соединение с БД
    await close_db()
    # Закрываем сессию бота (если используется storage, который требует закрытия)
    await dispatcher.storage.close()
    logger.info("Хранилище FSM закрыто.")
    # Сессию бота закрывать явно не нужно, если используется polling с диспетчером
    logger.info("Бот остановлен.")

# --- Основная функция для запуска бота ---
async def main():
    if not config:
        logger.critical("Запуск невозможен: конфигурация не загружена.")
        return

    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    try:
        storage = MongoStorage.from_url(url=config.mongo.uri)
        logger.info("Используется MongoStorage для FSM (БД из URI)")
    except Exception as e:
        logger.critical(f"Не удалось инициализировать MongoStorage из URI: {e}", exc_info=True)
        return

    dp = Dispatcher(storage=storage)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    dp.update.outer_middleware(LanguageMiddleware())
    logger.info("Middleware языка зарегистрирован.")

    logger.info("Подключение роутеров...")
    dp.include_router(common_router)
    dp.include_router(settings_router)
    dp.include_router(image_generation_router)
    dp.include_router(document_router)
    dp.include_router(privacy_router)
    dp.include_router(audio_router)
    dp.include_router(image_router)
    dp.include_router(text_router)
    logger.info("Роутеры подключены.")

    logger.info("Запуск polling...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Критическая ошибка во время polling: {e}", exc_info=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную (KeyboardInterrupt/SystemExit).")