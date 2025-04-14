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
class Config:
    bot: BotConfig
    gemini: GeminiConfig

def load_config(path: str | None = ".env") -> Config:
    """
    Загружает конфигурацию из переменных окружения или .env файла.
    """
    load_dotenv(dotenv_path=path) # Загружает переменные из .env файла

    return Config(
        bot=BotConfig(
            token=os.getenv("TELEGRAM_BOT_TOKEN")
        ),
        gemini=GeminiConfig(
            api_key=os.getenv("GEMINI_API_KEY")
        )
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