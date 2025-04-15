import logging
from typing import List, Dict, Any
import motor.motor_asyncio
from pymongo.errors import ConnectionFailure, OperationFailure

from src.config import config # Импортируем общую конфигурацию

logger = logging.getLogger(__name__)

# Глобальные переменные для клиента и коллекции (инициализируются в connect_db)
mongo_client: motor.motor_asyncio.AsyncIOMotorClient | None = None
db: motor.motor_asyncio.AsyncIOMotorDatabase | None = None
history_collection: motor.motor_asyncio.AsyncIOMotorCollection | None = None

async def connect_db():
    """Инициализирует подключение к MongoDB."""
    global mongo_client, db, history_collection
    if not config:
        logger.error("Конфигурация не загружена, не могу подключиться к БД.")
        return False
    
    if mongo_client:
        return True
    logger.info(f"Попытка подключения к MongoDB: {config.mongo.uri}")
    
    try:
        # --- Основной блок подключения ---
        mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
            config.mongo.uri,
            # Добавляем таймауты для надежности (опционально, но рекомендуется)
            serverSelectionTimeoutMS=5000, # Таймаут выбора сервера (5 секунд)
            connectTimeoutMS=5000,         # Таймаут подключения (5 секунд)
            socketTimeoutMS=10000          # Таймаут операций сокета (10 секунд)
        )
        # Проверка соединения
        await mongo_client.admin.command('ping')
        logger.info("Пинг MongoDB успешен.")

        db = mongo_client[config.mongo.db_name]
        history_collection = db["chat_histories"]
        logger.info(f"Подключено к MongoDB, база данных: {config.mongo.db_name}")

        # --- Создание индекса ПЕРЕМЕЩЕНО СЮДА (внутрь try) ---
        try:
            # unique=True гарантирует, что у одного user_id будет только один документ истории
            await history_collection.create_index("user_id", unique=True)
            logger.info("Индекс по 'user_id' создан или уже существует.")
        except OperationFailure as index_e:
            # Ошибка создания индекса - не критична для запуска, но важна
            logger.error(f"Не удалось создать/проверить индекс по 'user_id': {index_e}")
            # Можно решить, возвращать False или True. Оставим True, т.к. подключение есть.
        except Exception as index_e: # Ловим другие ошибки индекса
            logger.error(f"Непредвиденная ошибка при создании индекса 'user_id': {index_e}", exc_info=True)

        return True # Подключение успешно

    except ConnectionFailure as e:
        logger.critical(f"Не удалось подключиться к MongoDB (ConnectionFailure): {e}", exc_info=False) # Не нужен полный трейсбек часто
        # Сбрасываем переменные при ошибке
        mongo_client = None
        db = None
        history_collection = None
        return False # Ошибка подключения
    except Exception as e: # Ловим другие возможные ошибки при инициализации (например, таймауты)
        logger.critical(f"Непредвиденная ошибка при подключении к MongoDB: {e}", exc_info=True)
        # Сбрасываем переменные при ошибке
        mongo_client = None
        db = None
        history_collection = None
        return False # Ошибка подключения

async def close_db():
    """Закрывает соединение с MongoDB."""
    global mongo_client, db, history_collection
    if mongo_client:
        mongo_client.close()
        mongo_client = None
        db = None
        history_collection = None
        logger.info("Соединение с MongoDB закрыто.")

async def get_history(user_id: int) -> List[Dict[str, Any]]:
    """Извлекает историю чата для пользователя."""
    if history_collection is None:
        logger.error("MongoDB collection не инициализирована.")
        return []
    try:
        doc = await history_collection.find_one({"user_id": user_id})
        return doc.get("history", []) if doc else []
    except OperationFailure as e:
        logger.error(f"Ошибка MongoDB при получении истории для user_id={user_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении истории для user_id={user_id}: {e}", exc_info=True)
        return []


async def save_history(user_id: int, history: List[Dict[str, Any]]):
    """Сохраняет (обновляет) историю чата для пользователя."""
    if history_collection is None:
        logger.error("MongoDB collection не инициализирована.")
        return False
    try:
        await history_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": history, "user_id": user_id}}, # Убедимся, что user_id есть
            upsert=True # Создать документ, если его нет
        )
        logger.debug(f"История для user_id={user_id} сохранена/обновлена.")
        return True
    except OperationFailure as e:
        logger.error(f"Ошибка MongoDB при сохранении истории для user_id={user_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при сохранении истории для user_id={user_id}: {e}", exc_info=True)
        return False

async def clear_history(user_id: int):
    """Очищает историю чата для пользователя."""
    if history_collection is None:
        logger.error("MongoDB collection не инициализирована.")
        return False
    try:
        result = await history_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": []}} # Устанавливаем пустой массив
        )
        # Или можно удалить документ: result = await history_collection.delete_one({"user_id": user_id})
        logger.info(f"История для user_id={user_id} очищена. Затронуто документов: {result.modified_count}")
        return True
    except OperationFailure as e:
        logger.error(f"Ошибка MongoDB при очистке истории для user_id={user_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при очистке истории для user_id={user_id}: {e}", exc_info=True)
        return False