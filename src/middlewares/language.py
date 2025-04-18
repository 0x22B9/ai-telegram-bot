from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from src.localization import get_i18n_args

class LanguageMiddleware(BaseMiddleware):
    """
    Middleware for localization.
    Adds 'localizer', 'lang_code' to event data.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")

        if user is None:
            localizer, lang_code = get_i18n_args()
        else:
            state: FSMContext = data.get("state")
            if state:
                user_data = await state.get_data()
                user_lang_code = user_data.get("language_code")
                localizer, lang_code = get_i18n_args(user_lang_code)
            else:
                 localizer, lang_code = get_i18n_args()

        data["localizer"] = localizer
        data["lang_code"] = lang_code

        return await handler(event, data)