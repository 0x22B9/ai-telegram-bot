import logging
from typing import List, Dict, Any, Optional, Tuple
import motor.motor_asyncio
from pymongo.errors import ConnectionFailure, OperationFailure

from src.config import config, DEFAULT_GEMINI_TEMPERATURE, DEFAULT_GEMINI_MAX_TOKENS

logger = logging.getLogger(__name__)

# Глобальные переменные для клиента и коллекции (инициализируются в connect_db)
mongo_client: motor.motor_asyncio.AsyncIOMotorClient | None = None
db: motor.motor_asyncio.AsyncIOMotorDatabase | None = None
user_data_collection: motor.motor_asyncio.AsyncIOMotorCollection | None = None

async def connect_db():
    """Инициализирует подключение к MongoDB."""
    global mongo_client, db, user_data_collection # history_collection -> user_data_collection
    if not config:
        logger.error("Конфигурация не загружена, не могу подключиться к БД.")
        return False

    if mongo_client is None:
        logger.info(f"Подключение к MongoDB: {config.mongo.uri}")
        try:
            mongo_client = motor.motor_asyncio.AsyncIOMotorClient(config.mongo.uri)
            await mongo_client.admin.command('ping')
            db = mongo_client[config.mongo.db_name]
            # Используем новое имя коллекции
            user_data_collection = db["user_data"]
            # Можно создать индекс по user_id
            await user_data_collection.create_index("user_id", unique=True)
            logger.info(f"Успешно подключено к MongoDB, база данных: {config.mongo.db_name}, коллекция: user_data")
            return True
        except ConnectionFailure as e:
            logger.critical(f"Не удалось подключиться к MongoDB: {e}", exc_info=True)
            mongo_client = None
            db = None
            user_data_collection = None
            return False
        except Exception as e:
            logger.critical(f"Непредвиденная ошибка при подключении к MongoDB: {e}", exc_info=True)
            mongo_client = None
            db = None
            user_data_collection = None
            return False
    return True

async def close_db():
    """Закрывает соединение с MongoDB."""
    global mongo_client, db, user_data_collection
    if mongo_client:
        mongo_client.close()
        mongo_client = None
        db = None
        user_data_collection = None
        logger.info("Соединение с MongoDB закрыто.")

async def get_history(user_id: int) -> List[Dict[str, Any]]:
    """Извлекает ТОЛЬКО историю чата для пользователя."""
    # --- Используем user_data_collection ---
    if user_data_collection is None:
        logger.error("get_history: MongoDB collection не инициализирована.")
        return []
    # -------------------------------------
    try:
        # Извлекаем только поле history
        doc = await user_data_collection.find_one(
            {"user_id": user_id},
            projection={"history": 1, "_id": 0} # Запросить только history
        )
        return doc.get("history", []) if doc else []
    except OperationFailure as e:
        logger.error(f"Ошибка MongoDB при получении истории для user_id={user_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении истории для user_id={user_id}: {e}", exc_info=True)
        return []

# --- Новая функция для получения настроек ---
async def get_user_settings(user_id: int) -> Tuple[float, int]:
    """
    Извлекает настройки Gemini для пользователя.
    Возвращает кортеж (temperature, max_tokens).
    Использует значения по умолчанию, если настройки не найдены.
    """
    if user_data_collection is None:
        logger.error("get_user_settings: MongoDB collection не инициализирована.")
        return DEFAULT_GEMINI_TEMPERATURE, DEFAULT_GEMINI_MAX_TOKENS
    try:
        doc = await user_data_collection.find_one(
            {"user_id": user_id},
            # Запрашиваем только нужные поля настроек
            projection={"gemini_temperature": 1, "gemini_max_tokens": 1, "_id": 0}
        )
        if doc:
            temperature = doc.get("gemini_temperature", DEFAULT_GEMINI_TEMPERATURE)
            max_tokens = doc.get("gemini_max_tokens", DEFAULT_GEMINI_MAX_TOKENS)
            return temperature, max_tokens
        else:
            # Если документа нет, возвращаем дефолтные
            return DEFAULT_GEMINI_TEMPERATURE, DEFAULT_GEMINI_MAX_TOKENS
    except OperationFailure as e:
        logger.error(f"Ошибка MongoDB при получении настроек для user_id={user_id}: {e}")
        return DEFAULT_GEMINI_TEMPERATURE, DEFAULT_GEMINI_MAX_TOKENS
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении настроек для user_id={user_id}: {e}", exc_info=True)
        return DEFAULT_GEMINI_TEMPERATURE, DEFAULT_GEMINI_MAX_TOKENS

# --- Новая функция для сохранения ОДНОЙ настройки ---
async def save_user_setting(user_id: int, setting_name: str, setting_value: Any):
    """Сохраняет (обновляет) одну настройку для пользователя."""
    if user_data_collection is None:
        logger.error("save_user_setting: MongoDB collection не инициализирована.")
        return False
    # Проверяем, что имя настройки допустимо (предосторожность)
    if setting_name not in ["gemini_temperature", "gemini_max_tokens"]:
        logger.error(f"Попытка сохранить недопустимую настройку '{setting_name}' для user_id={user_id}")
        return False
    try:
        await user_data_collection.update_one(
            {"user_id": user_id},
            {"$set": {setting_name: setting_value, "user_id": user_id}}, # Убедимся, что user_id есть
            upsert=True # Создать документ, если его нет
        )
        logger.info(f"Настройка '{setting_name}' для user_id={user_id} сохранена/обновлена значением {setting_value}.")
        return True
    except OperationFailure as e:
        logger.error(f"Ошибка MongoDB при сохранении настройки '{setting_name}' для user_id={user_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при сохранении настройки '{setting_name}' для user_id={user_id}: {e}", exc_info=True)
        return False

async def save_history(user_id: int, history: List[Dict[str, Any]]):
    """Сохраняет (обновляет) ТОЛЬКО историю чата для пользователя."""
    if user_data_collection is None:
        logger.error("save_history: MongoDB collection не инициализирована.")
        return False
    try:
        await user_data_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": history, "user_id": user_id}}, # Обновляем только history
            upsert=True
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
    """Очищает ТОЛЬКО историю чата для пользователя (настройки остаются)."""
    if user_data_collection is None:
        logger.error("clear_history: MongoDB collection не инициализирована.")
        return False
    try:
        # Используем $unset чтобы удалить поле, или $set с пустым массивом
        result = await user_data_collection.update_one(
            {"user_id": user_id},
            # {"$unset": {"history": ""}} # Удаляет поле
            {"$set": {"history": []}} # Устанавливает пустой массив (предпочтительнее)
        )
        logger.info(f"История для user_id={user_id} очищена. Затронуто документов: {result.modified_count}")
        return True
    except OperationFailure as e:
        logger.error(f"Ошибка MongoDB при очистке истории для user_id={user_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при очистке истории для user_id={user_id}: {e}", exc_info=True)
        return False
    
async def delete_user_data(user_id: int) -> bool:
    """
    Полностью удаляет документ пользователя (включая историю и настройки) из БД.
    Возвращает True, если документ был найден и удален, иначе False.
    """
    if user_data_collection is None:
        logger.error("delete_user_data: MongoDB collection не инициализирована.")
        return False
    try:
        logger.warning(f"Попытка удаления всех данных для user_id={user_id}")
        result = await user_data_collection.delete_one({"user_id": user_id})
        if result.deleted_count > 0:
            logger.info(f"Все данные для user_id={user_id} успешно удалены.")
            return True
        else:
            logger.info(f"Данные для user_id={user_id} не найдены для удаления.")
            return False # Пользователя и так не было в БД
    except OperationFailure as e:
        logger.error(f"Ошибка MongoDB при удалении данных для user_id={user_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при удалении данных для user_id={user_id}: {e}", exc_info=True)
        return False