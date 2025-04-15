# Описания команд и общие фразы
start-prompt = Выберите предпочитаемый язык:
start-welcome = Привет, { $user_name }! Я бот на базе ИИ. Отправь мне текст или изображение (с подписью или без), и я постараюсь ответить. Используйте /help для просмотра команд.
language-chosen = Язык установлен на Русский. { start-welcome }
language-select-button = Русский

help-text =
    Я могу отвечать на ваши текстовые сообщения и анализировать изображения с помощью Gemini AI.
    
    Команды:
    /start - Перезапустить бота (показать приветствие)
    /newchat - Начать новый диалог (очистить историю)
    /language - Сменить язык интерфейса
    /help - Показать это сообщение
    
    Как использовать:
    - Просто напишите мне текстовое сообщение.
    - Отправьте изображение. Вы можете добавить подпись к изображению, чтобы задать конкретный вопрос о нем (например, "Что необычного на этой картинке?"). Если подписи нет, я просто опишу его.

# Обработка сообщений
thinking = 🧠 Думаю над вашим вопросом...
analyzing = 🖼️ Анализирую изображение...

# Создание нового чата
newchat-started = ✨ Хорошо, начнем новый диалог! Я забыл предыдущий контекст.

# Сообщения об ошибках
error-gemini-fetch = 😔 Не удалось получить ответ от Gemini. Попробуйте позже.
error-image-download = 😔 Не удалось загрузить ваше изображение. Попробуйте еще раз.
error-image-analysis = 😔 Не удалось проанализировать изображение с помощью Gemini. Попробуйте позже.
error-display = 😔 Произошла ошибка при отображении ответа. Попробуйте позже.
error-general = 😔 Произошла непредвиденная ошибка. Попробуйте позже.
error-blocked-content = Мой ответ был заблокирован из-за ограничений безопасности (Причина: { $reason }). Попробуйте переформулировать запрос.
error-blocked-image-content = Мой ответ на изображение был заблокирован из-за ограничений безопасности (Причина: { $reason }).
error-gemini-api-key = Ошибка: Ключ Gemini API не настроен.
error-gemini-request = Произошла ошибка при обращении к Gemini: Свяжитесь с администратором!
error-image-analysis-request = Произошла ошибка при анализе изображения: Свяжитесь с администратором!