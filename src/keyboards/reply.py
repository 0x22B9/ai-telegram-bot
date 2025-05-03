from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from fluent.runtime import FluentLocalization


def get_main_keyboard(localizer: FluentLocalization) -> ReplyKeyboardMarkup:
    """Creates and returns Reply keyboard with main buttons."""
    builder = ReplyKeyboardBuilder()

    builder.button(text="/newchat")
    builder.button(text="/language")
    builder.button(text="/generate_image")
    builder.button(text="/help")

    builder.adjust(2, 2)

    placeholder = localizer.format_value("main-keyboard-placeholder")

    keyboard = builder.as_markup(
        resize_keyboard=True, input_field_placeholder=placeholder
    )
    return keyboard
