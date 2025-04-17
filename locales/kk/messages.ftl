# Команда сипаттамалары және жалпы фразалар
start-prompt = Өзіңізге ыңғайлы тілді таңдаңыз:
start-welcome = Сәлем, { $user_name }! Мен ЖИ негізіндегі ботпын. Маған мәтін немесе сурет (тақырыппен немесе онсыз) жіберіңіз, мен жауап беруге тырысамын. Командаларды көру үшін /help пайдаланыңыз.
language-chosen = Тіл қазақ тіліне орнатылды. { start-welcome }
language-select-button = Қазақша 🇰🇿

help-text =
    Мен Gemini AI көмегімен сіздің мәтіндік хабарламаларыңызға жауап бере аламын және суреттерді талдай аламын.

    <b>Командалар:</b>
    /start - Ботты қайта іске қосу (сәлемдесуді көрсету)
    /newchat - Жаңа диалог бастау (тарихты тазалау)
    /model - Мәтін генерациялау үшін ЖИ моделін таңдау
    /language - Тілді өзгерту
    /settings - (ТЕК ЕГЕР СЕН НЕ ІСТЕП ЖАТҚАНЫҢДЫ БІЛСЕҢ) Gemini генерация параметрлерін теңшеу
    /help - Осы хабарламаны көрсету

    <b>Қалай пайдалануға болады:</b>
    - Маған жай ғана мәтіндік хабарлама жазыңыз.
    - Сурет жіберіңіз. Суретке қатысты нақты сұрақ қою үшін жазба қосуға болады (мысалы, <code>"Бұл суретте не ерекше?"</code>). Егер жазба болмаса, мен оны сипаттаймын.

# Хабарламаларды өңдеу
thinking = 🧠 Сұрағыңызды ойланудамын...
analyzing = 🖼️ Суретті талдаудамын...

# ЖИ модельдері
model-prompt = Мәтін генерациялау үшін ЖИ моделін таңдаңыз:
model-chosen = ЖИ моделі орнатылды: { $model_name }
thinking-retry = ⏳ Алдыңғы сұрауыңызды қайталап жатырмын...

# Жаңа чат ашу
newchat-started = ✨ Жақсы, жаңа диалогты бастайық! Мен алдыңғы контексті ұмытып кеттім.

# Пернетақта
main-keyboard-placeholder = Команданы таңдаңыз немесе мәтін енгізіңіз...
button-retry-request = 🔁 Сұранысты қайталау?
settings-current-prompt = Gemini генерациясының ағымдағы параметрлері:
settings-button-temperature = 🌡️ Температура: { $value }
settings-button-max-tokens = 📏 Максималды ұзындық: { $value }
settings-prompt-temperature = Температураны таңдаңыз (шығармашылыққа әсер етеді):
settings-prompt-max-tokens = Жауаптың максималды ұзындығын таңдаңыз (токендерде):
settings-option-default = Әдепкі ({ $value })
settings-option-temperature-precise = 0.3 (Дәл)
settings-option-temperature-balanced = 0.7 (Теңгерімді)
settings-option-temperature-creative = 1.4 (Шығармашылық)
settings-option-max-tokens-short = 512 (Қысқа)
settings-option-max-tokens-medium = 1024 (Орташа)
settings-option-max-tokens-long = 2048 (Ұзын)
settings-option-max-tokens-very_long = 8192 (Өте ұзын)
button-back = ⬅️ Артқа

# Қате туралы хабарламалар
error-gemini-fetch = 😔 Gemini-ден жауап алу мүмкін болмады. Кейінірек қайталап көріңіз.
error-image-download = 😔 Суретіңізді жүктеу мүмкін болмады. Қайталап көріңіз.
error-image-analysis = 😔 Gemini көмегімен суретті талдау мүмкін болмады. Кейінірек қайталап көріңіз.
error-display = 😔 Жауапты көрсету кезінде қате пайда болды. Кейінірек қайталап көріңіз.
error-general = 😔 Күтпеген қате пайда болды. Кейінірек қайталап көріңіз.
error-blocked-content = Менің жауабым қауіпсіздік шектеулеріне байланысты бұғатталды (Себеп: { $reason }). Сұранысыңызды басқаша тұжырымдап көріңіз.
error-blocked-image-content = Суретке берген жауабым қауіпсіздік шектеулеріне байланысты бұғатталды (Себеп: { $reason }).
error-gemini-api-key = Қате: Gemini API кілті конфигурацияланбаған.
error-gemini-request = Gemini-мен байланысу кезінде қате пайда болды: Әкімшімен хабарласыңыз!
error-image-analysis-request = Суретті талдау кезінде қате пайда болды: Әкімшімен хабарласыңыз!
error-retry-not-found = 🤷 Қайталау үшін алдыңғы сұрауды табу мүмкін болмады. Бот қайта іске қосылған болуы мүмкін.
error-quota-exceeded = Ой! Мен қазір тым танымал болып, ЖИ сұраныстарының шегіне жеттім. Біраздан кейін қайталап көріңіз. 🙏
error-settings-save = ❌ Параметрді сақтау мүмкін болмады. Қайтадан көріңіз.