from typing import Callable, Dict, Any, Awaitable
import logging

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from src.localization import get_i18n_args

logger = logging.getLogger(__name__)

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
        user_lang_code = None

        if user is None:
            localizer, lang_code = get_i18n_args()
            logger.debug("LanguageMiddleware: No user found, using default locale.")
        else:
            state: FSMContext = data.get("state")
            if state:
                user_data = await state.get_data()
                user_lang_code = user_data.get("language_code")
                logger.debug(f"LanguageMiddleware: User ID {user.id}, language from state: {user_lang_code}")
                localizer, lang_code = get_i18n_args(user_lang_code)
            else:
                 logger.warning(f"LanguageMiddleware: No FSM state found for user {user.id}, using default locale.")
                 localizer, lang_code = get_i18n_args()

        data["localizer"] = localizer
        data["lang_code"] = lang_code

        return await handler(event, data)