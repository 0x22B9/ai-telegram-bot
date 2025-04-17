import os
from dataclasses import dataclass, field
from typing import List, Dict, Union
from dotenv import load_dotenv


AVAILABLE_TEXT_MODELS = ["gemini-2.0-flash", "gemini-2.5-pro-exp-03-25"]
DEFAULT_TEXT_MODEL = "gemini-2.0-flash"
DEFAULT_GEMINI_TEMPERATURE = 1
DEFAULT_GEMINI_MAX_TOKENS = 1024

ALLOWED_TEMPERATURES: Dict[str, float] = {
    "precise": 0.3,
    "balanced": 0.7,
    "creative": 1.4,
}
ALLOWED_MAX_TOKENS: Dict[str, int] = {
    "short": 512,
    "medium": 1024,
    "long": 2048,
    "very_long": 8192
}
TEMPERATURE_NAMES: Dict[float, str] = {v: k for k, v in ALLOWED_TEMPERATURES.items()}
MAX_TOKENS_NAMES: Dict[int, str] = {v: k for k, v in ALLOWED_MAX_TOKENS.items()}
VISION_MODEL = "gemini-2.0-flash"
DEFAULT_IMAGE_GEN_MODEL_ID = "stabilityai/stable-diffusion-3-medium-diffusers"

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
class HuggingFaceConfig:
    api_token: str
    image_gen_model_id: str

@dataclass
class Config:
    bot: BotConfig
    gemini: GeminiConfig
    mongo: MongoConfig
    hf: HuggingFaceConfig
    
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
    hf_token = os.getenv("HUGGINGFACE_API_TOKEN")
    img_model = os.getenv("IMAGE_GEN_MODEL_ID", DEFAULT_IMAGE_GEN_MODEL_ID)
    
    # Проверяем наличие обязательных параметров
    if not all([bot_token, gemini_key, mongo_uri, mongo_db, hf_token]):
        print("Ошибка: Не все обязательные переменные окружения найдены "
              "(включая HUGGINGFACE_API_TOKEN).")
        return None

    return Config(
        bot=BotConfig(token=bot_token),
        gemini=GeminiConfig(api_key=gemini_key),
        mongo=MongoConfig(uri=mongo_uri, db_name=mongo_db),
        hf=HuggingFaceConfig(api_token=hf_token, image_gen_model_id=img_model)
    )
    
config = load_config()
if not config:
    print("Критическая ошибка: Не удалось загрузить конфигурацию.")