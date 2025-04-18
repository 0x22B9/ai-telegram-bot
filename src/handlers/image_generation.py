import logging
import asyncio
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from fluent.runtime import FluentLocalization
from aiogram.enums import ChatAction

from src.services import image_generation as img_gen_service
from src.keyboards import get_main_keyboard

logger = logging.getLogger(__name__)
image_generation_router = Router()

class ImageGenState(StatesGroup):
    waiting_for_prompt = State()

@image_generation_router.message(Command("generate_image"))
async def handle_generate_image_command(message: types.Message, state: FSMContext, localizer: FluentLocalization):
    """Starts the image generation process."""
    prompt_request_text = localizer.format_value("generate-image-prompt")
    await message.answer(prompt_request_text)
    await state.set_state(ImageGenState.waiting_for_prompt)

@image_generation_router.message(ImageGenState.waiting_for_prompt, F.text)
async def handle_image_prompt(message: types.Message, state: FSMContext, bot: Bot, localizer: FluentLocalization):
    """Gets prompt for image generation."""
    prompt = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id
    logger.info(f"Got image prompt from user_id={user_id}: {prompt[:50]}...")

    generating_text = localizer.format_value("generating-image")
    status_message = await message.answer(generating_text)

    typing_task = asyncio.create_task(send_upload_photo_periodically(bot, chat_id))

    image_bytes = None
    error_code = img_gen_service.IMAGE_GEN_UNKNOWN_ERROR

    try:
        image_bytes, error_code = await img_gen_service.generate_image_from_prompt(prompt)
    finally:
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try: await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError): pass

    if image_bytes and error_code == img_gen_service.IMAGE_GEN_SUCCESS:
        try:
            photo_input = types.BufferedInputFile(image_bytes, filename="generated_image.png")
            main_kbd = get_main_keyboard(localizer)
            await message.answer_photo(photo=photo_input, caption=f"🖼️ {prompt[:900]}", reply_markup=main_kbd)
            logger.info(f"Generated image sent to user_id={user_id}")
            await status_message.delete()
        except Exception as e:
            logger.error(f"Error sending image to user_id={user_id}: {e}", exc_info=True)
            error_text = localizer.format_value("error-telegram-send")
            await status_message.edit_text(error_text)
    else:
        error_key = f"error-image-{error_code.split(':')[-1].lower()}"
        error_text = localizer.format_value(error_key, fallback=localizer.format_value("error-image-unknown"))
        await status_message.edit_text(error_text)
        logger.warning(f"Error generating image for user_id={user_id}: {error_code}")

    await state.clear()

@image_generation_router.message(ImageGenState.waiting_for_prompt)
async def handle_invalid_image_prompt_input(message: types.Message, localizer: FluentLocalization):
    """Handles invalid image prompt input."""
    error_text = localizer.format_value("error-invalid-prompt-type")
    await message.reply(error_text)

async def send_upload_photo_periodically(bot: Bot, chat_id: int):
    """Sends 'upload_photo' action every 5 sec."""
    try:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in send_upload_photo_periodically for chat {chat_id}: {e}", exc_info=True)