# Описания команд и общие фразы
start-prompt = Выберите предпочитаемый язык:
start-welcome = Привет, { $user_name }! Я бот на базе ИИ. Отправь мне текст или изображение (с подписью или без), и я постараюсь ответить. Используйте /help для просмотра команд.
language-chosen = Язык установлен на Русский. { start-welcome }
language-select-button = Русский

help-text =
    Я могу отвечать на ваши текстовые сообщения и анализировать изображения с помощью Gemini AI.
    
    <b>Команды:</b>
    /start - Перезапустить бота (показать приветствие)
    /newchat - Начать новый диалог (очистить историю)
    /generate_image - Сгенерировать изображение по тексту
    /model - Выбрать модель ИИ для генерации текста
    /language - Сменить язык интерфейса
    /settings - (ТОЛЬКО ЕСЛИ ТЫ ЗНАЕШЬ ЧТО ДЕЛАЕШЬ) Настроить параметры генерации Gemini
    /help - Показать это сообщение
    /delete_my_data - Удалить все ваши данные из бота
    
    <b>Как использовать:</b>
    - Просто напишите мне текстовое сообщение.
    - Отправьте изображение. Вы можете добавить подпись к изображению, чтобы задать конкретный вопрос о нем (например, <code>"Что необычного на этой картинке?"</code>). Если подписи нет, я просто опишу его.
    - Отправьте мне .docx, .pdf, .txt файл и я его проанализировую.
    - Не хотите печатать текст? Просто отправьте голосовое сообщение, и я отвечу на него!

# Обработка сообщений
thinking = 🧠 Думаю над вашим вопросом...
analyzing = 🖼️ Анализирую изображение...
thinking-retry = ⏳ Повторяю ваш предыдущий запрос...

# Генерация изображений
generate-image-prompt = 🎨 Введите текстовое описание (промпт) для генерации изображения:
generating-image = ✨ Магия в процессе... Генерирую ваше изображение! Это может занять некоторое время.
error-invalid-prompt-type = Пожалуйста, введите текстовое описание для изображения.

# Обработка аудио
processing-voice = 🎤 Обрабатываю ваше голосовое сообщение...
processing-transcribed-text = 🧠 Думаю над вашим запросом из аудио...
error-transcription-failed = ⚠️ Не удалось транскрибировать аудио: { $error }
error-transcription-failed-unknown = ⚠️ Не удалось транскрибировать аудио из-за неизвестной ошибки.
error-processing-voice = ⚠️ Произошла ошибка при обработке вашего голосового сообщения.

# Обработка документов
error-doc-unsupported-type = ⚠️ Тип файла ({ $mime_type }) не поддерживается. Пожалуйста, отправьте PDF, DOCX или TXT.
error-doc-too-large = ⚠️ Файл слишком большой. Максимальный размер: { $limit_mb } МБ.
processing-document = 📄 Обрабатываю документ '{ $filename }'... Это может занять некоторое время.
processing-extracted-text = 🧠 Анализирую текст из документа '{ $filename }'...

# Модели ИИ
model-prompt = Выберите модель ИИ для генерации текста:
model-chosen = Модель ИИ установлена на: { $model_name }

# Создание нового чата
newchat-started = ✨ Хорошо, начнем новый диалог! Я забыл предыдущий контекст.

# Клавиатура
main-keyboard-placeholder = Выберите команду или введите текст...
button-retry-request = 🔁 Повторить запрос?
settings-current-prompt = Текущие настройки генерации Gemini:
settings-button-temperature = 🌡️ Температура: { $value }
settings-button-max-tokens = 📏 Макс. длина: { $value }
settings-prompt-temperature = Выберите температуру (влияет на креативность):
settings-prompt-max-tokens = Выберите максимальную длину ответа (в токенах):
settings-option-default = По умолчанию ({ $value })
settings-option-temperature-precise = 0.3 (Точный)
settings-option-temperature-balanced = 0.7 (Сбалансированный)
settings-option-temperature-creative = 1.4 (Креативный)
settings-option-max-tokens-short = 512 (Короткий)
settings-option-max-tokens-medium = 1024 (Средний)
settings-option-max-tokens-long = 2048 (Длинный)
settings-option-max-tokens-very_long = 8192 (Очень длинный)
button-back = ⬅️ Назад

# Удаление данных
confirm-delete-prompt = ⚠️ <b>Внимание!</b> Вы уверены, что хотите удалить все ваши данные (историю чата, настройки) из этого бота? Это действие необратимо.
button-confirm-delete = Да, удалить мои данные
button-cancel-delete = Нет, отмена
delete-success = ✅ Ваши данные были успешно удалены.
delete-error = ❌ Не удалось удалить ваши данные. Пожалуйста, попробуйте еще раз или свяжитесь с администратором, если проблема повторяется.
delete-cancelled = 👌 Удаление данных отменено.

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
error-retry-not-found = 🤷 Не удалось найти предыдущий запрос для повтора. Возможно, бот перезапускался.
error-quota-exceeded = Ой! Кажется, я сейчас слишком популярен и достиг лимита запросов к ИИ. Попробуйте немного позже. 🙏
error-settings-save = ❌ Не удалось сохранить настройку. Попробуйте еще раз.
error-image-api_error = ❌ Ошибка API генерации изображений. Попробуйте позже.
error-image-timeout_error = ⏳ Сервер генерации изображений не отвечает или модель загружается. Попробуйте позже.
error-image-rate_limit_error = 🚦 Слишком много запросов! Превышен лимит на генерацию изображений. Попробуйте позже.
error-image-content_filter_error = 🙅 Запрос отклонен фильтром безопасности. Попробуйте изменить промпт.
error-image-unknown = ❓ Неизвестная ошибка при генерации изображения.
error-telegram-send = 😔 Не удалось отправить сгенерированное изображение.
error-doc-parsing-pdf = ❌ Ошибка при чтении PDF файла. Возможно, он поврежден или зашифрован.
error-doc-parsing-docx = ❌ Ошибка при чтении DOCX файла. Возможно, он поврежден.
error-doc-parsing-txt = ❌ Ошибка при чтении текстового файла (проблема с кодировкой).
error-doc-parsing-lib_missing = ❌ Необходимая библиотека ({ $library }) для обработки этого типа файла не установлена на сервере.
error-doc-parsing-emptydoc = ⚠️ Документ не содержит текста или текст не удалось извлечь.
error-doc-parsing-unknown = ❓ Неизвестная ошибка при извлечении текста из документа.
error-doc-processing-general = ⚠️ Произошла ошибка при обработке вашего документа.
response-truncated = [Ответ был сокращен из-за ограничений длины сообщения]