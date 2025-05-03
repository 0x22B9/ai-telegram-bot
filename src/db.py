import logging
from typing import Any, Dict, List, Tuple

import motor.motor_asyncio
from pymongo.errors import (
    ConnectionFailure,
    NetworkTimeout,
    OperationFailure,
    ServerSelectionTimeoutError,
)

from src.config import DEFAULT_GEMINI_MAX_TOKENS, DEFAULT_GEMINI_TEMPERATURE, config

logger = logging.getLogger(__name__)

mongo_client: motor.motor_asyncio.AsyncIOMotorClient | None = None
db: motor.motor_asyncio.AsyncIOMotorDatabase | None = None
user_data_collection: motor.motor_asyncio.AsyncIOMotorCollection | None = None


async def connect_db():
    """Inits connection to MongoDB."""
    global mongo_client, db, user_data_collection
    if not config:
        logger.error("Config is not loaded. Cannot connect to MongoDB.")
        return False

    if mongo_client is None:
        logger.info(f"Connecting to MongoDB: {config.mongo.uri}")
        try:
            mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
                config.mongo.uri, serverSelectionTimeoutMS=5000
            )
            await mongo_client.admin.command("ping")
            db = mongo_client[config.mongo.db_name]
            user_data_collection = db["user_data"]
            await user_data_collection.create_index("user_id", unique=True)
            logger.info(
                f"Successfully connected to MongoDB, DB: {config.mongo.db_name}, collection: user_data"
            )
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.critical(
                f"Cannot connect to MongoDB (ConnectionFailure or Timeout): {e}",
                exc_info=True,
            )
            mongo_client = None
            db = None
            user_data_collection = None
            return False
        except Exception as e:
            logger.critical(
                f"Unexpected error while connecting to MongoDB: {e}", exc_info=True
            )
            mongo_client = None
            db = None
            user_data_collection = None
            return False
    return True


async def close_db():
    """Closes connection to MongoDB."""
    global mongo_client, db, user_data_collection
    if mongo_client:
        mongo_client.close()
        mongo_client = None
        db = None
        user_data_collection = None
        logger.info("Closed connection to MongoDB.")


async def get_history(user_id: int) -> List[Dict[str, Any]]:
    """Extracts only the history field for the user."""
    if user_data_collection is None:
        logger.error("get_history: MongoDB collection isn't initialized.")
        return []
    try:
        doc = await user_data_collection.find_one(
            {"user_id": user_id}, projection={"history": 1, "_id": 0}
        )
        return doc.get("history", []) if doc else []
    except (OperationFailure, NetworkTimeout) as e:
        logger.error(
            f"MongoDB OperationFailure or NetworkTimeout while getting history for user_id={user_id}: {e}"
        )
        return []
    except Exception as e:
        logger.error(
            f"Unexpected error while getting history for user_id={user_id}: {e}",
            exc_info=True,
        )
        return []


async def get_user_settings(user_id: int) -> Tuple[float, int]:
    """
    Extracts Gemini settings for user.
    Return (temperature, max_tokens).
    Uses default values, if settings are not found .
    """
    if user_data_collection is None:
        logger.error("get_user_settings: MongoDB collection isn't initialized.")
        return DEFAULT_GEMINI_TEMPERATURE, DEFAULT_GEMINI_MAX_TOKENS
    try:
        doc = await user_data_collection.find_one(
            {"user_id": user_id},
            projection={"gemini_temperature": 1, "gemini_max_tokens": 1, "_id": 0},
        )
        if doc:
            temperature = doc.get("gemini_temperature", DEFAULT_GEMINI_TEMPERATURE)
            max_tokens = doc.get("gemini_max_tokens", DEFAULT_GEMINI_MAX_TOKENS)
            return temperature, max_tokens
        else:
            return DEFAULT_GEMINI_TEMPERATURE, DEFAULT_GEMINI_MAX_TOKENS
    except (OperationFailure, NetworkTimeout) as e:
        logger.error(
            f"Error MongoDB while getting settings (OperationFailure or NetworkTimeout) for user_id={user_id}: {e}"
        )
        return DEFAULT_GEMINI_TEMPERATURE, DEFAULT_GEMINI_MAX_TOKENS
    except Exception as e:
        logger.error(
            f"Unexpected error while getting settings for user_id={user_id}: {e}",
            exc_info=True,
        )
        return DEFAULT_GEMINI_TEMPERATURE, DEFAULT_GEMINI_MAX_TOKENS


async def save_user_setting(user_id: int, setting_name: str, setting_value: Any):
    """Saves (updating) one setting for user."""
    if user_data_collection is None:
        logger.error("save_user_setting: MongoDB collection isn't initialized.")
        return False
    if setting_name not in ["gemini_temperature", "gemini_max_tokens"]:
        logger.error(
            f"Trying to save unknown setting '{setting_name}' for user_id={user_id}"
        )
        return False
    try:
        await user_data_collection.update_one(
            {"user_id": user_id},
            {"$set": {setting_name: setting_value, "user_id": user_id}},
            upsert=True,
        )
        logger.info(
            f"Setting '{setting_name}' for user_id={user_id} saved/updated with value {setting_value}."
        )
        return True
    except (OperationFailure, NetworkTimeout) as e:
        logger.error(
            f"Error MongoDB while saving setting '{setting_name}' for user_id={user_id}: {e}"
        )
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error while saving setting '{setting_name}' for user_id={user_id}: {e}",
            exc_info=True,
        )
        return False


async def save_history(user_id: int, history: List[Dict[str, Any]]):
    """Saves (updating) ONLY chat history for user."""
    if user_data_collection is None:
        logger.error("save_history: MongoDB collection isn't initialized.")
        return False
    try:
        await user_data_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": history, "user_id": user_id}},
            upsert=True,
        )
        logger.debug(f"History for user_id={user_id} saved/updated.")
        return True
    except (OperationFailure, NetworkTimeout) as e:
        logger.error(f"Error MongoDB while saving history for user_id={user_id}: {e}")
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error while saving history for user_id={user_id}: {e}",
            exc_info=True,
        )
        return False


async def clear_history(user_id: int):
    """Clear ONLY chat history for user (settings are not affected)."""
    if user_data_collection is None:
        logger.error("clear_history: MongoDB collection isn't initialized.")
        return False
    try:
        result = await user_data_collection.update_one(
            {"user_id": user_id}, {"$set": {"history": []}}
        )
        logger.info(
            f"History for user_id={user_id} cleared. Affected documents: {result.modified_count}"
        )
        return True
    except (OperationFailure, NetworkTimeout) as e:
        logger.error(f"Error MongoDB while clearing history for user_id={user_id}: {e}")
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error while clearing history for user_id={user_id}: {e}",
            exc_info=True,
        )
        return False


async def delete_user_data(user_id: int) -> bool:
    """
    Completely deletes the user’s document (including history and settings) from the DB.
    Returns True if the document was found and deleted, otherwise False.
    """
    if user_data_collection is None:
        logger.error("delete_user_data: MongoDB collection isn't initialized.")
        return False
    try:
        logger.warning(f"Trying to delete all data for user_id={user_id}")
        result = await user_data_collection.delete_one({"user_id": user_id})
        if result.deleted_count > 0:
            logger.info(f"All data for user_id={user_id} deleted.")
            return True
        else:
            logger.info(f"Data for deletion for user_id={user_id} is not found.")
            return False
    except (OperationFailure, NetworkTimeout) as e:
        logger.error(f"Error MongoDB while deleting data for user_id={user_id}: {e}")
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error while deleting data for user_id={user_id}: {e}",
            exc_info=True,
        )
        return False
