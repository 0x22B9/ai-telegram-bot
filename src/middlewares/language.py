from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from src.localization import get_i18n_args

class LanguageMiddleware(BaseMiddleware):
    """
    Middleware для определения и установки языка пользователя.
    Добавляет 'localizer' и 'lang_code' в данные события.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user") # Получаем пользователя из данных события

        if user is None:
            # Если пользователя нет (например, channel post), используем дефолтный язык
            localizer, lang_code = get_i18n_args()
        else:
            # Получаем state и storage из данных события
            state: FSMContext = data.get("state")
            if state:
                # Пытаемся получить язык из хранилища FSM
                user_data = await state.get_data()
                user_lang_code = user_data.get("language_code")
                localizer, lang_code = get_i18n_args(user_lang_code)
            else:
                 # Если state нет (редкий случай), используем дефолт
                 localizer, lang_code = get_i18n_args()

        # Добавляем локализатор и код языка в данные для хэндлеров
        data["localizer"] = localizer
        data["lang_code"] = lang_code

        # Вызываем следующий обработчик в цепочке
        return await handler(event, data)