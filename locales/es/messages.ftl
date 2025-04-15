# locales/es/messages.ftl

# Descripciones de comandos y frases comunes
start-prompt = Elige tu idioma preferido:
start-welcome = ¡Hola, { $user_name }! Soy un bot de IA impulsado por Gemini. Envíame texto o una imagen (con o sin descripción), e intentaré responder. Usa /help para ver los comandos.
language-chosen = Idioma establecido a Español. { start-welcome }
language-select-button = Español 🇪🇸

help-text =
    Puedo responder a tus mensajes de texto y analizar imágenes usando Gemini AI.

    Comandos:
    /start - Reiniciar el bot (mostrar saludo)
    /language - Cambiar el idioma de la interfaz
    /help - Mostrar este mensaje

    Cómo usar:
    - Simplemente envíame un mensaje de texto.
    - Envía una imagen. Puedes añadir una descripción a la imagen para hacer una pregunta específica sobre ella (p.ej., "¿Qué hay de inusual en esta foto?"). Si no hay descripción, simplemente la describiré.

# Procesando mensajes
thinking = 🧠 Pensando en tu consulta...
analyzing = 🖼️ Analizando la imagen...

# Mensajes de error
error-gemini-fetch = 😔 No se pudo obtener una respuesta de Gemini. Por favor, inténtalo más tarde.
error-image-download = 😔 No se pudo cargar tu imagen. Por favor, inténtalo de nuevo.
error-image-analysis = 😔 No se pudo analizar la imagen con Gemini. Por favor, inténtalo más tarde.
error-display = 😔 Ocurrió un error al mostrar la respuesta. Por favor, inténtalo más tarde.
error-general = 😔 Ocurrió un error inesperado. Por favor, inténtalo más tarde.
error-blocked-content = Mi respuesta fue bloqueada debido a restricciones de seguridad (Motivo: { $reason }). Por favor, intenta reformular tu solicitud.
error-blocked-image-content = Mi respuesta a la imagen fue bloqueada debido a restricciones de seguridad (Motivo: { $reason }).
error-gemini-api-key = Error: La clave API de Gemini no está configurada.
error-gemini-request = Ocurrió un error al contactar con Gemini: { $error }
error-image-analysis-request = Ocurrió un error al analizar la imagen: { $error }