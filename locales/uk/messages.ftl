# Описи команд та загальні фрази
start-prompt = Оберіть бажану мову:
start-welcome = Привіт, { $user_name }! Я бот на основі ШІ. Надішли мені текст або зображення (з підписом або без), і я постараюся відповісти. Використовуй /help для перегляду команд.
language-chosen = Мову встановлено на Українську. { start-welcome }
language-select-button = Українська 🇺🇦

help-text =
    Я можу відповідати на ваші текстові повідомлення та аналізувати зображення за допомогою Gemini AI.

    <b>Команди:</b>
    /start - Перезапустити бота (показати привітання)
    /newchat - Почати новий діалог (очистити історію)
    /generate_image - Згенерувати зображення з тексту
    /model - Обрати модель ШІ для генерації тексту
    /language - Змінити мову інтерфейсу
    /settings - (ТІЛЬКИ ЯКЩО ТИ ЗНАЄШ, ЩО РОБИШ) Налаштувати параметри генерації Gemini
    /help - Показати це повідомлення

    <b>Як використовувати:</b>
    - Просто напишіть мені текстове повідомлення.
    - Надішліть зображення. Ви можете додати підпис до зображення, щоб поставити конкретне запитання про нього (наприклад, <code>"Що незвичайного на цій картинці?"</code>). Якщо підпису немає, я просто опишу його.
    - Надішліть мені файл .docx, .pdf, .txt, і я його проаналізую.
    - Не хочете друкувати? Просто надішліть голосове повідомлення, і я на нього відповім!

# Обробка повідомлень
thinking = 🧠 Думаю над вашим запитом...
analyzing = 🖼️ Аналізую зображення...
thinking-retry = ⏳ Повторюю ваш попередній запит...

# Генерація зображень
generate-image-prompt = 🎨 Введіть текстовий опис (промпт) для генерації зображення:
generating-image = ✨ Магія в процесі... Генерую ваше зображення! Це може зайняти деякий час.
error-invalid-prompt-type = Будь ласка, введіть текстовий опис для зображення.

# Обробка аудіо
processing-voice = 🎤 Обробляю ваше голосове повідомлення...
processing-transcribed-text = 🧠 Думаю над вашим запитом з аудіо...
error-transcription-failed = ⚠️ Не вдалося транскрибувати аудіо: { $error }
error-transcription-failed-unknown = ⚠️ Не вдалося транскрибувати аудіо через невідому помилку.
error-processing-voice = ⚠️ Сталася помилка під час обробки вашого голосового повідомлення.

# Обробка документів
error-doc-unsupported-type = ⚠️ Тип файлу ({ $mime_type }) не підтримується. Будь ласка, завантажте PDF, DOCX або TXT.
error-doc-too-large = ⚠️ Файл занадто великий. Максимальний розмір: { $limit_mb } МБ.
processing-document = 📄 Обробляю документ '{ $filename }'... Це може зайняти деякий час.
processing-extracted-text = 🧠 Аналізую текст із документа '{ $filename }'...

# Моделі ШІ
model-prompt = Оберіть модель ШІ для генерації тексту:
model-chosen = Модель ШІ встановлено на: { $model_name }

# Створення нового чату  
newchat-started = ✨ Гаразд, почнімо новий діалог! Я забув попередній контекст.

# Клавіатура
main-keyboard-placeholder = Виберіть команду або введіть текст...
button-retry-request = 🔁 Повторити запит?
settings-current-prompt = Поточні налаштування генерації Gemini:
settings-button-temperature = 🌡️ Температура: { $value }
settings-button-max-tokens = 📏 Максимальна довжина: { $value }
settings-prompt-temperature = Виберіть температуру (впливає на креативність):
settings-prompt-max-tokens = Виберіть максимальну довжину відповіді (у токенах):
settings-option-default = За замовчуванням ({ $value })
settings-option-temperature-precise = 0.3 (Точний)
settings-option-temperature-balanced = 0.7 (Збалансований)
settings-option-temperature-creative = 1.4 (Креативний)
settings-option-max-tokens-short = 512 (Короткий)
settings-option-max-tokens-medium = 1024 (Середній)
settings-option-max-tokens-long = 2048 (Довгий)
settings-option-max-tokens-very_long = 8192 (Дуже довгий)
button-back = ⬅️ Назад

# Повідомлення про помилки
error-gemini-fetch = 😔 Не вдалося отримати відповідь від Gemini. Спробуйте пізніше.
error-image-download = 😔 Не вдалося завантажити ваше зображення. Спробуйте ще раз.
error-image-analysis = 😔 Не вдалося проаналізувати зображення за допомогою Gemini. Спробуйте пізніше.
error-display = 😔 Сталася помилка під час відображення відповіді. Спробуйте пізніше.
error-general = 😔 Сталася неочікувана помилка. Спробуйте пізніше.
error-blocked-content = Мою відповідь було заблоковано через обмеження безпеки (Причина: { $reason }). Спробуйте переформулювати запит.
error-blocked-image-content = Мою відповідь на зображення було заблоковано через обмеження безпеки (Причина: { $reason }).
error-gemini-api-key = Помилка: Ключ Gemini API не налаштовано.
error-gemini-request = Сталася помилка під час звернення до Gemini: Зв'яжіться з адміністратором!
error-image-analysis-request = Сталася помилка під час аналізу зображення: Зв'яжіться з адміністратором!
error-retry-not-found = 🤷 Не вдалося знайти попередній запит для повтору. Можливо, бот перезапускався.
error-quota-exceeded = Ой! Здається, я зараз надто популярний і досяг ліміту запитів до ШІ. Спробуйте ще раз трохи пізніше. 🙏
error-settings-save = ❌ Не вдалося зберегти налаштування. Спробуйте ще раз.
error-image-api_error = ❌ Помилка API генерації зображень. Спробуйте пізніше.
error-image-timeout_error = ⏳ Сервер генерації зображень не відповідає або модель завантажується. Спробуйте пізніше.
error-image-rate_limit_error = 🚦 Занадто багато запитів! Перевищено ліміт на генерацію зображень. Спробуйте пізніше.
error-image-content_filter_error = 🙅 Запит відхилено фільтром безпеки. Спробуйте змінити промпт.
error-image-unknown = ❓ Невідома помилка під час генерації зображення.
error-telegram-send = 😔 Не вдалося надіслати згенероване зображення.
error-doc-parsing-pdf = ❌ Помилка при читанні PDF-файлу. Можливо, він пошкоджений або зашифрований.
error-doc-parsing-docx = ❌ Помилка при читанні DOCX-файлу. Можливо, він пошкоджений.
error-doc-parsing-txt = ❌ Помилка при читанні текстового файлу (проблема з кодуванням).
error-doc-parsing-lib_missing = ❌ Необхідна бібліотека ({ $library }) для обробки цього типу файлу не встановлена на сервері.
error-doc-parsing-emptydoc = ⚠️ Документ не містить тексту або текст не вдалося витягти.
error-doc-parsing-unknown = ❓ Невідома помилка при витягуванні тексту з документа.
error-doc-processing-general = ⚠️ Сталася помилка під час обробки вашого документа.
response-truncated = [Відповідь була скорочена через обмеження довжини повідомлення]