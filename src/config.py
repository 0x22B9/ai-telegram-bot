import os
from dataclasses import dataclass, field
from typing import List, Dict, Union
from dotenv import load_dotenv

# --- Добавлено: Настройки моделей Gemini ---
# Используйте официальные идентификаторы моделей из документации Google AI
AVAILABLE_TEXT_MODELS = ["gemini-2.0-flash", "gemini-2.5-pro-exp-03-25"]
# Модель по умолчанию (Flash часто быстрее и дешевле для чата)
DEFAULT_TEXT_MODEL = "gemini-2.0-flash"
DEFAULT_GEMINI_TEMPERATURE = 0.7
DEFAULT_GEMINI_MAX_TOKENS = 1024 # Средняя длина ответа

# Допустимые значения для выбора пользователем
ALLOWED_TEMPERATURES: Dict[str, float] = {
    "precise": 0.3,
    "balanced": 0.7,
    "creative": 1.0,
}
ALLOWED_MAX_TOKENS: Dict[str, int] = {
    "short": 512,   # Уменьшил с 256 для большей полезности
    "medium": 1024,
    "long": 2048,
    "very_long": 4096 # Увеличил для возможности больших ответов
}
# Сопоставление числовых значений с их "именами" для отображения
TEMPERATURE_NAMES: Dict[float, str] = {v: k for k, v in ALLOWED_TEMPERATURES.items()}
MAX_TOKENS_NAMES: Dict[int, str] = {v: k for k, v in ALLOWED_MAX_TOKENS.items()}
# Модель для анализа изображений (обычно отдельная)
VISION_MODEL = "gemini-2.0-flash" # Или более новая, если появится совместимая
# ------------------------------------------

@dataclass
class BotConfig:
    token: str

@dataclass
class GeminiConfig:
    api_key: str
    default_temperature: float = DEFAULT_GEMINI_TEMPERATURE
    default_max_tokens: int = DEFAULT_GEMINI_MAX_TOKENS
    allowed_temperatures: Dict[str, float] = field(default_factory=lambda: ALLOWED_TEMPERATURES)
    allowed_max_tokens: Dict[str, int] = field(default_factory=lambda: ALLOWED_MAX_TOKENS)

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