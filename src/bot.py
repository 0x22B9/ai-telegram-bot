import asyncio
import logging

# Добавляем импорт DefaultBotProperties
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties # <<< ДОБАВИТЬ ЭТОТ ИМПОРТ
from aiogram.fsm.storage.memory import MemoryStorage # Или другое хранилище

from src.config import config, load_config
from src.handlers import common_router, text_router, image_router
from src.middlewares import LanguageMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

async def main():
    loaded_config = load_config()

    if not loaded_config or not loaded_config.bot.token or not loaded_config.gemini.api_key:
        logger.critical("Не удалось загрузить конфигурацию. Проверьте .env файл.")
        return

    bot = Bot(
        token=loaded_config.bot.token,
        default=DefaultBotProperties(parse_mode="Markdown"))
    # Используйте RedisStorage или другое персистентное хранилище для продакшена,
    # чтобы выбор языка сохранялся между перезапусками!
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # --- Регистрация Middleware ---
    # Важно: регистрируем ДО роутеров, чтобы localizer был доступен везде
    dp.update.outer_middleware(LanguageMiddleware())
    logger.info("Middleware языка зарегистрирован.")

    # --- Подключение роутеров ---
    logger.info("Подключение роутеров...")
    # Порядок важен, если есть пересекающиеся фильтры, но здесь не критично
    dp.include_router(common_router) # Обработчики /start, /help, колбэки
    dp.include_router(text_router)   # Обработчик текста
    dp.include_router(image_router)  # Обработчик изображений
    logger.info("Роутеры подключены.")

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Вебхук удален.")

    logger.info("Запуск бота (polling)...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
    finally:
        # Закрытие сессии бота теперь не рекомендуется делать явно здесь,
        # так как Dispatcher управляет жизненным циклом бота при polling.
        # await bot.session.close() # <<< ЭТУ СТРОКУ МОЖНО УДАЛИТЬ ИЛИ ЗАКОММЕНТИРОВАТЬ
        logger.info("Завершение работы бота.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")