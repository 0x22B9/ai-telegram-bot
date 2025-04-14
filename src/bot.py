import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage # Простое хранилище состояний в памяти
from aiogram.client.default import DefaultBotProperties

# Импортируем конфигурацию (убедитесь, что она загружена в config.py)
from src.config import load_config

# Импортируем роутеры из handlers
from src.handlers import common, text, image

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


async def main():
    """
    Главная асинхронная функция для запуска бота.
    """
    # Загружаем конфигурацию (если не загрузилась при импорте)
    # Можно убрать эту строку, если уверены, что config.py всегда отработает при импорте
    loaded_config = load_config()

    if not loaded_config or not loaded_config.bot.token or not loaded_config.gemini.api_key:
        logger.critical("Не удалось загрузить конфигурацию. Проверьте .env файл и переменные окружения.")
        return # Прерываем выполнение, если конфиг не загружен

    # Инициализация бота и диспетчера
    bot = Bot(
    token=loaded_config.bot.token,
    default=DefaultBotProperties(parse_mode="Markdown"))
    storage = MemoryStorage() # Вы можете заменить на RedisStorage или другое для продакшена
    dp = Dispatcher(storage=storage)

    # Подключение роутеров
    logger.info("Подключение роутеров...")
    dp.include_router(common.common_router)
    dp.include_router(text.text_router)
    dp.include_router(image.image_router)
    # Добавьте другие роутеры здесь, если они появятся
    logger.info("Роутеры подключены.")

    # Удаление вебхука перед запуском polling (на всякий случай)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Вебхук удален (если был).")

    # Запуск polling
    logger.info("Запуск бота (polling)...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
    finally:
        await bot.session.close()
        logger.info("Сессия бота закрыта.")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")