from pathlib import Path
from typing import Dict, Tuple

from fluent.runtime import FluentLocalization, FluentResourceLoader

# Путь к папке с локалями относительно корня проекта
LOCALES_DIR = Path(__file__).parent.parent / "locales"
DEFAULT_LOCALE = "en" # Язык по умолчанию, если не выбран
SUPPORTED_LOCALES = ["en", "kk", "uk", "zh", "es", "ru"] # Поддерживаемые языки

# Загрузчик ресурсов Fluent
loader = FluentResourceLoader(str(LOCALES_DIR / "{locale}"))

# Словарь с объектами локализации для каждого языка
# Ключ - код языка (str), значение - объект FluentLocalization
LOCALIZATIONS: Dict[str, FluentLocalization] = {
    locale: FluentLocalization([locale, DEFAULT_LOCALE], ["messages.ftl"], loader)
    for locale in SUPPORTED_LOCALES
}

def get_localizer(locale: str | None = None) -> FluentLocalization:
    """Возвращает объект локализации для указанного или дефолтного языка."""
    # Проверяем, есть ли запрошенный язык в наших локализациях
    # Если нет, или если locale is None, используем DEFAULT_LOCALE
    effective_locale = locale if locale in LOCALIZATIONS else DEFAULT_LOCALE
    return LOCALIZATIONS.get(effective_locale, LOCALIZATIONS[DEFAULT_LOCALE])

def get_i18n_args(
    user_locale: str | None = None,
    default_locale: str = DEFAULT_LOCALE
) -> Tuple[FluentLocalization, str]:
    """
    Возвращает объект локализатора и код языка для использования в хэндлерах.
    """
    actual_locale = user_locale if user_locale in SUPPORTED_LOCALES else default_locale
    localizer = get_localizer(actual_locale)
    final_lang_code = localizer.locales[0] if localizer.locales else default_locale
    return localizer, final_lang_code