from pathlib import Path
from typing import Dict, Tuple

from fluent.runtime import FluentLocalization, FluentResourceLoader

LOCALES_DIR = Path(__file__).parent.parent / "locales"
DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = ["en", "kk", "uk", "zh", "es", "ru"]

loader = FluentResourceLoader(str(LOCALES_DIR / "{locale}"))

LOCALIZATIONS: Dict[str, FluentLocalization] = {
    locale: FluentLocalization([locale, DEFAULT_LOCALE], ["messages.ftl"], loader)
    for locale in SUPPORTED_LOCALES
}


def get_localizer(locale: str | None = None) -> FluentLocalization:
    """Returns object of FluentLocalization with appropriate or default locale."""
    effective_locale = locale if locale in LOCALIZATIONS else DEFAULT_LOCALE
    return LOCALIZATIONS.get(effective_locale, LOCALIZATIONS[DEFAULT_LOCALE])


def get_i18n_args(
    user_locale: str | None = None, default_locale: str = DEFAULT_LOCALE
) -> Tuple[FluentLocalization, str]:
    """Returns object of FluentLocalization and code language for using in handlers."""
    actual_locale = user_locale if user_locale in SUPPORTED_LOCALES else default_locale
    localizer = get_localizer(actual_locale)
    final_lang_code = localizer.locales[0] if localizer.locales else default_locale
    return localizer, final_lang_code
