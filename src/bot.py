import asyncio
import logging

# Добавляем импорт DefaultBotProperties
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties # <<< ДОБАВИТЬ ЭТОТ ИМПОРТ
from aiogram.fsm.storage.mongo import MongoStorage

from src.config import config, load_config
from src.handlers import common_router, text_router, image_router
from src.middlewares import LanguageMiddleware
from src.db import connect_db, close_db

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
        default=DefaultBotProperties(parse_mode="HTML"))
    # Используйте RedisStorage или другое персистентное хранилище для продакшена,
    # чтобы выбор языка сохранялся между перезапусками!
    try:
        storage = MongoStorage.from_url(
            url=config.mongo.uri
            # collection="aiogram_fsm_states" # Можно указать имя коллекции, если нужно
        )
        logger.info(f"Используется MongoStorage для FSM (БД из URI: {config.mongo.uri.split('/')[-1].split('?')[0]})") # Логируем предполагаемую БД из URI
    except Exception as e:
        logger.critical(f"Не удалось инициализировать MongoStorage из URI: {e}", exc_info=True)
        logger.critical("Убедитесь, что имя базы данных указано в MONGO_URI в .env файле (например, ...mongodb.net/имя_базы?...)")
        return # Не запускаем бота без хранилища FSM
    dp = Dispatcher(storage=storage)

    # --- Регистрация обработчиков жизненного цикла ---
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

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
        # Передаем аргументы в on_startup через dispatcher
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Критическая ошибка во время polling: {e}", exc_info=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")