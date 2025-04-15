# locales/es/messages.ftl

# Descripciones de comandos y frases comunes
start-prompt = Elige tu idioma preferido:
start-welcome = ¡Hola, { $user_name }! Soy un bot basado en IA. Envíame texto o una imagen (con o sin descripción), y haré lo mejor para responder. Usa /help para ver los comandos.
language-chosen = Idioma establecido a Español. { start-welcome }
language-select-button = Español 🇪🇸

help-text =
    Puedo responder a tus mensajes de texto y analizar imágenes usando Gemini AI.

    <b>Comandos:</b>
    /start - Reiniciar el bot (mostrar saludo)
    /newchat - Iniciar un nuevo diálogo (limpiar historial)
    /model - Seleccionar un modelo de IA para generar texto
    /language - Cambiar el idioma de la interfaz
    /help - Mostrar este mensaje

    <b>Cómo usar:</b>
    - Simplemente envíame un mensaje de texto.
    - Envía una imagen. Puedes añadir una descripción a la imagen para hacer una pregunta específica sobre ella (p.ej., <code>"¿Qué hay de inusual en esta foto?"</code>). Si no hay descripción, simplemente la describiré.

# Procesando mensajes
thinking = 🧠 Pensando en tu consulta...
analyzing = 🖼️ Analizando la imagen...

# Modelos de IA
model-prompt = Selecciona un modelo de IA para generar texto:
model-chosen = El modelo de IA se ha establecido en: { $model_name }

# Creación de un nuevo chat
newchat-started = ✨ ¡Bien, empecemos un nuevo diálogo! He olvidado el contexto anterior.

# Mensajes de error
error-gemini-fetch = 😔 No se pudo obtener una respuesta de Gemini. Por favor, inténtalo más tarde.
error-image-download = 😔 No se pudo cargar tu imagen. Por favor, inténtalo de nuevo.
error-image-analysis = 😔 No se pudo analizar la imagen con Gemini. Por favor, inténtalo más tarde.
error-display = 😔 Ocurrió un error al mostrar la respuesta. Por favor, inténtalo más tarde.
error-general = 😔 Ocurrió un error inesperado. Por favor, inténtalo más tarde.
error-blocked-content = Mi respuesta fue bloqueada debido a restricciones de seguridad (Motivo: { $reason }). Por favor, intenta reformular tu solicitud.
error-blocked-image-content = Mi respuesta a la imagen fue bloqueada debido a restricciones de seguridad (Motivo: { $reason }).
error-gemini-api-key = Error: La clave API de Gemini no está configurada.
error-gemini-request = Ocurrió un error al contactar con Gemini: ¡Póngase en contacto con el administrador!
error-image-analysis-request = Ocurrió un error al analizar la imagen: ¡Póngase en contacto con el administrador!