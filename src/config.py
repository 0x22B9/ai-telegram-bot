import os
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class BotConfig:
    token: str

@dataclass
class GeminiConfig:
    api_key: str

@dataclass
class MongoConfig:
    uri: str
    db_name: str

@dataclass
class Config:
    bot: BotConfig
    gemini: GeminiConfig
    mongo: MongoConfig

def load_config(path: str | None = ".env") -> Config | None:
    """
    Загружает конфигурацию из переменных окружения или .env файла.
    Возвращает None в случае ошибки загрузки основных ключей.
    """
    load_dotenv(dotenv_path=path)

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    gemini_key = os.getenv("GEMINI_API_KEY")
    mongo_uri = os.getenv("MONGO_URI")
    mongo_db = os.getenv("MONGO_DB_NAME")

    # Проверяем наличие обязательных параметров
    if not all([bot_token, gemini_key, mongo_uri, mongo_db]):
        print("Ошибка: Не все обязательные переменные окружения найдены "
              "(TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, MONGO_URI, MONGO_DB_NAME).")
        return None # Возвращаем None, если что-то важное отсутствует

    return Config(
        bot=BotConfig(token=bot_token),
        gemini=GeminiConfig(api_key=gemini_key),
        mongo=MongoConfig(uri=mongo_uri, db_name=mongo_db) # <<< Добавлено
    )

# Проверка при импорте, что ключи загружены
try:
    config = load_config()
    if not config.bot.token or not config.gemini.api_key:
        raise ValueError("TELEGRAM_BOT_TOKEN или GEMINI_API_KEY не найдены в .env или переменных окружения.")
except (ValueError, TypeError) as e:
    print(f"Ошибка загрузки конфигурации: {e}")
    # Можно завершить программу или использовать значения по умолчанию, если это применимо
    # exit() # Раскомментируйте, если хотите прервать выполнение при ошибке
    # Для примера оставим возможность запуска, но выведем ошибку
    config = None # Или установите значения по умолчанию