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
    /generate_image - Generar una imagen a partir de texto
    /model - Seleccionar un modelo de IA para generar texto
    /language - Cambiar el idioma de la interfaz
    /settings - (SOLO SI SABES LO QUE ESTÁS HACIENDO) Configurar parámetros de generación de Gemini
    /help - Mostrar este mensaje
    /delete_my_data - Eliminar todos tus datos del bot

    <b>Cómo usar:</b>
    - Simplemente envíame un mensaje de texto.
    - Envía una imagen. Puedes añadir una descripción a la imagen para hacer una pregunta específica sobre ella (p.ej., <code>"¿Qué hay de inusual en esta foto?"</code>). Si no hay descripción, simplemente la describiré.
    - Envíame un archivo .docx, .pdf, .txt y lo analizaré.
    - ¿No quieres escribir? ¡Solo envía un mensaje de voz y te responderé!

# Procesando mensajes
thinking = 🧠 Pensando en tu consulta...
analyzing = 🖼️ Analizando la imagen...
thinking-retry = ⏳ Reintentando tu solicitud anterior...

# Generación de imágenes
generate-image-prompt = 🎨 Ingresa una descripción de texto (prompt) para la generación de imágenes:
generating-image = ✨ ¡Magia en proceso... Generando tu imagen! Esto puede tomar algo de tiempo.
error-invalid-prompt-type = Por favor, ingresa una descripción de texto para la imagen.

# Procesamiento de audio
processing-voice = 🎤 Procesando tu mensaje de voz...
processing-transcribed-text = 🧠 Pensando en tu solicitud a partir del audio...
error-transcription-failed = ⚠️ No se pudo transcribir el audio: { $error }
error-transcription-failed-unknown = ⚠️ No se pudo transcribir el audio debido a un error desconocido.
error-processing-voice = ⚠️ Ocurrió un error al procesar tu mensaje de voz.

# Procesamiento de Documentos
error-doc-unsupported-type = ⚠️ El tipo de archivo ({ $mime_type }) no es compatible. Por favor, sube un PDF, DOCX o TXT.
error-doc-too-large = ⚠️ El archivo es demasiado grande. Tamaño máximo: { $limit_mb } MB.
processing-document = 📄 Procesando documento '{ $filename }'... Esto puede tomar un tiempo.
processing-extracted-text = 🧠 Analizando texto del documento '{ $filename }'...

# Modelos de IA
model-prompt = Selecciona un modelo de IA para generar texto:
model-chosen = El modelo de IA se ha establecido en: { $model_name }

# Creación de un nuevo chat
newchat-started = ✨ ¡Bien, empecemos un nuevo diálogo! He olvidado el contexto anterior.

# Indicaciones para IA
prompt-analyze-document = Analiza el texto de este documento '{ $filename }' en español:
prompt-describe-image-default = Describe esta imagen en español.
response-text-truncated-for-ai = [... Texto truncado antes de enviarlo a la IA debido a los límites de longitud ...]

# Teclado
main-keyboard-placeholder = Seleccione un comando o escriba un texto...
button-retry-request = 🔁 ¿Reintentar solicitud?
settings-current-prompt = Configuración actual de generación de Gemini:
settings-button-temperature = 🌡️ Temperatura: { $value }
settings-button-max-tokens = 📏 Longitud máxima: { $value }
settings-prompt-temperature = Selecciona la temperatura (afecta la creatividad):
settings-prompt-max-tokens = Selecciona la longitud máxima de la respuesta (en tokens):
settings-option-default = Predeterminado ({ $value })
settings-option-temperature-precise = 0.3 (Preciso)
settings-option-temperature-balanced = 0.7 (Equilibrado)
settings-option-temperature-creative = 1.4 (Creativo)
settings-option-max-tokens-short = 512 (Corto)
settings-option-max-tokens-medium = 1024 (Medio)
settings-option-max-tokens-long = 2048 (Largo)
settings-option-max-tokens-very_long = 8192 (Muy largo)
button-back = ⬅️ Atrás

# Eliminación de datos
confirm-delete-prompt = ⚠️ <b>¡Advertencia!</b> ¿Estás seguro de que quieres eliminar todos tus datos (historial de chat, configuraciones) de este bot? Esta acción es irreversible.
button-confirm-delete = Sí, eliminar mis datos
button-cancel-delete = No, cancelar
delete-success = ✅ Tus datos han sido eliminados con éxito.
delete-error = ❌ No se pudieron eliminar tus datos. Por favor, intenta de nuevo o contacta al administrador si el problema persiste.
delete-cancelled = 👌 Eliminación de datos cancelada.

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
error-retry-not-found = 🤷 No se pudo encontrar la solicitud anterior para reintentar. Es posible que el bot se haya reiniciado.
error-quota-exceeded = ¡Uy! Parece que estoy demasiado popular ahora mismo y he alcanzado el límite de solicitudes de IA. Intenta de nuevo un poco más tarde. 🙏
error-settings-save = ❌ No se pudo guardar la configuración. Intenta de nuevo.
error-image-api_error = ❌ Error en la API de generación de imágenes. Intenta de nuevo más tarde.
error-image-timeout_error = ⏳ El servidor de generación de imágenes no responde o el modelo está cargando. Intenta de nuevo más tarde.
error-image-rate_limit_error = 🚦 ¡Demasiadas solicitudes! Se excedió el límite de generación de imágenes. Intenta de nuevo más tarde.
error-image-content_filter_error = 🙅 Solicitud rechazada por el filtro de seguridad. Intenta modificar el prompt.
error-image-unknown = ❓ Error desconocido durante la generación de la imagen.
error-telegram-send = 😔 No se pudo enviar la imagen generada.
error-doc-parsing-pdf = ❌ Error al leer el archivo PDF. Puede estar dañado o encriptado.
error-doc-parsing-docx = ❌ Error al leer el archivo DOCX. Puede estar dañado.
error-doc-parsing-txt = ❌ Error al leer el archivo de texto (problema de codificación).
error-doc-parsing-lib_missing = ❌ La biblioteca necesaria ({ $library }) para procesar este tipo de archivo no está instalada en el servidor.
error-doc-parsing-emptydoc = ⚠️ El documento no contiene texto o no se pudo extraer el texto.
error-doc-parsing-unknown = ❓ Error desconocido al extraer texto del documento.
error-doc-processing-general = ⚠️ Ocurrió un error al procesar tu documento.
response-truncated = [La respuesta fue truncada debido a limitaciones de longitud del mensaje]
error-download-image = 😔 No se pudo cargar tu imagen. Por favor, intenta de nuevo.
error-image-analysis-failed = ❌ No se pudo analizar la imagen con IA. Intenta de nuevo más tarde.
error-image-analysis-unknown = ❓ Ocurrió un error desconocido durante el análisis de la imagen.
error-gemini-api-key-invalid = 🔑 Error: Clave de API de Gemini inválida o revocada. Verifica la configuración.
error-gemini-service-unavailable = ☁️ El servicio de Gemini está temporalmente fuera de servicio. Por favor, inténtalo de nuevo más tarde.
error-gemini-unknown = ❓ Se produjo un error desconocido de la API de Gemini ({ $type }). Contacta al administrador.
error-image-connection-error = 🌐 No se pudo conectar al servicio de generación de imágenes. Verifica la red o inténtalo más tarde.
error-telegram-download = 😔 No se pudo descargar el archivo de Telegram. Por favor, envíalo de nuevo.
error-telegram-upload = 😔 No se pudo subir el archivo/la foto a Telegram.
error-db-save = 💾 No se pudieron guardar los datos en la base de datos. Es posible que la configuración o el historial no se hayan actualizado.
error-telegram-network = 🌐 Error de red al conectar con Telegram. Por favor, comprueba tu conexión o inténtalo de nuevo más tarde.
error-message-deleted = 🤷 Parece que el mensaje al que respondía ha sido eliminado.
delete-not-found = Parece que no había datos asociados a tu cuenta para eliminar.