from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup
from fluent.runtime import FluentLocalization

def get_main_keyboard(localizer: FluentLocalization) -> ReplyKeyboardMarkup:
    """
    Создает и возвращает главную Reply клавиатуру с основными командами.
    """
    builder = ReplyKeyboardBuilder()

    # Добавляем кнопки с текстом команд
    builder.button(text="/newchat")
    builder.button(text="/language")
    builder.button(text="/generate_image")
    builder.button(text="/help")

    # Выстраиваем кнопки в 2 ряда по 2 кнопки
    builder.adjust(2, 2)

    # Получаем локализованный плейсхолдер
    placeholder = localizer.format_value('main-keyboard-placeholder')

    # Создаем объект клавиатуры
    keyboard = builder.as_markup(
        resize_keyboard=True, # Делает кнопки меньше/адаптивнее
        input_field_placeholder=placeholder # Подсказка в поле ввода
    )
    return keyboard