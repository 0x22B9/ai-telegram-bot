from aiogram import Router, types
from aiogram.filters import CommandStart, Command

# Создаем роутер для общих команд
common_router = Router()

@common_router.message(CommandStart())
async def handle_start(message: types.Message):
    """
    Обработчик команды /start
    """
    await message.answer(f"Привет, {message.from_user.full_name}! Я бот с ИИ на базе Gemini. "
                         "Отправь мне текст или изображение (с подписью или без), и я постараюсь ответить.")

@common_router.message(Command("help"))
async def handle_help(message: types.Message):
    """
    Обработчик команды /help
    """
    await message.answer("Я могу отвечать на ваши текстовые сообщения и анализировать изображения с помощью Gemini AI.\n\n"
                         "**Команды:**\n"
                         "/start - Начать общение\n"
                         "/help - Показать это сообщение\n\n"
                         "**Как использовать:**\n"
                         "- Просто напишите мне текстовое сообщение.\n"
                         "- Отправьте изображение. Вы можете добавить подпись к изображению, чтобы задать конкретный вопрос о нем "
                         "(например, 'Что необычного на этой картинке?'). Если подписи нет, я просто опишу его.")