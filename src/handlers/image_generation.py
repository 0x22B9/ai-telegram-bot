import logging
import io
import asyncio
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from fluent.runtime import FluentLocalization
from aiogram.enums import ChatAction

from src.services import image_generation as img_gen_service # Импортируем наш сервис
from src.keyboards import get_main_keyboard # Для возврата основной клавиатуры

logger = logging.getLogger(__name__)
image_generation_router = Router()

# Определяем состояния FSM
class ImageGenState(StatesGroup):
    waiting_for_prompt = State()

# Обработчик команды /generate_image
@image_generation_router.message(Command("generate_image"))
async def handle_generate_image_command(message: types.Message, state: FSMContext, localizer: FluentLocalization):
    """Начинает процесс генерации изображения, запрашивая промпт."""
    prompt_request_text = localizer.format_value("generate-image-prompt")
    await message.answer(prompt_request_text)
    await state.set_state(ImageGenState.waiting_for_prompt) # Устанавливаем состояние ожидания

# Обработчик текста, когда бот ожидает промпт
@image_generation_router.message(ImageGenState.waiting_for_prompt, F.text)
async def handle_image_prompt(message: types.Message, state: FSMContext, bot: Bot, localizer: FluentLocalization):
    """Получает промпт, генерирует изображение и отправляет результат."""
    prompt = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id
    logger.info(f"Получен промпт для генерации изображения от user_id={user_id}: {prompt[:50]}...")

    # Сообщаем пользователю, что начали генерацию
    generating_text = localizer.format_value("generating-image")
    status_message = await message.answer(generating_text)

    # Запускаем индикатор загрузки фото
    typing_task = asyncio.create_task(send_upload_photo_periodically(bot, chat_id))

    image_bytes = None
    error_code = img_gen_service.IMAGE_GEN_UNKNOWN_ERROR # По умолчанию

    try:
        # Вызываем сервис генерации
        image_bytes, error_code = await img_gen_service.generate_image_from_prompt(prompt)
    finally:
        # Останавливаем индикатор загрузки
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try: await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError): pass

    # Обрабатываем результат
    if image_bytes and error_code == img_gen_service.IMAGE_GEN_SUCCESS:
        try:
            # Отправляем фото
            photo_input = types.BufferedInputFile(image_bytes, filename="generated_image.png")
            # Отправляем как новое сообщение, а статусное удаляем или редактируем
            main_kbd = get_main_keyboard(localizer) # Получаем основную клавиатуру
            await message.answer_photo(photo=photo_input, caption=f"🖼️ {prompt[:900]}", reply_markup=main_kbd) # Ограничиваем длину caption
            logger.info(f"Сгенерированное изображение отправлено user_id={user_id}")
            # Удаляем сообщение "Генерирую..."
            await status_message.delete()
        except Exception as e:
            logger.error(f"Ошибка отправки сгенерированного изображения user_id={user_id}: {e}", exc_info=True)
            error_text = localizer.format_value("error-telegram-send")
            await status_message.edit_text(error_text) # Редактируем статусное сообщение
    else:
        # Сообщаем об ошибке генерации
        error_key = f"error-image-{error_code.split(':')[-1].lower()}" # Генерируем ключ локализации из кода ошибки
        error_text = localizer.format_value(error_key, fallback=localizer.format_value("error-image-unknown")) # Фоллбэк на общую ошибку
        await status_message.edit_text(error_text)
        logger.warning(f"Ошибка генерации изображения для user_id={user_id}: {error_code}")

    # Завершаем состояние FSM
    await state.clear()

# Обработчик некорректного ввода в состоянии ожидания промпта
@image_generation_router.message(ImageGenState.waiting_for_prompt)
async def handle_invalid_image_prompt_input(message: types.Message, localizer: FluentLocalization):
    """Обрабатывает нетекстовый ввод в состоянии ожидания промпта."""
    error_text = localizer.format_value("error-invalid-prompt-type")
    await message.reply(error_text) # Отвечаем на сообщение пользователя

# Вспомогательная функция для индикатора загрузки фото
async def send_upload_photo_periodically(bot: Bot, chat_id: int):
    """Отправляет 'upload_photo' каждые 5 секунд."""
    try:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in send_upload_photo_periodically for chat {chat_id}: {e}", exc_info=True)