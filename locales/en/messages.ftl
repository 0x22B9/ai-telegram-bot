# Command descriptions and common phrases
start-prompt = Choose your preferred language:
start-welcome = Hello, { $user_name }! I'm an AI-based bot. Send me text or an image (with or without a caption), and I'll do my best to respond. Use /help to view commands.
language-chosen = Language set to English. { start-welcome }
language-select-button = English 🇬🇧

help-text =
    I can respond to your text messages and analyze images using Gemini AI.

    <b>Commands:</b>
    /start - Restart the bot (show the welcome message)
    /newchat - Start a new conversation (clear history)
    /generate_image - Generate an image from text
    /model - Select an AI model for text generation
    /language - Change the interface language
    /settings - (ONLY IF YOU KNOW WHAT YOU'RE DOING) Configure Gemini generation settings
    /help - Show this message

    <b>How to use:</b>
    - Just send me a text message.
    - Send an image. You can add a caption to ask a specific question about it (e.g., <code>"What's unusual in this picture?"</code>). If there's no caption, I'll describe it.
    - Send me a .docx, .pdf, .txt file, and I will analyze it.
    - Don’t want to type? Just send a voice message, and I’ll respond to it!

# Processing messages
thinking = 🧠 Thinking about your question...
analyzing = 🖼️ Analyzing the image...
thinking-retry = ⏳ Retrying your previous request...

# Image Generation
generate-image-prompt = 🎨 Enter a text description (prompt) for image generation:
generating-image = ✨ Magic in progress... Generating your image! This may take some time.
error-invalid-prompt-type = Please enter a text description for the image.

# Audio Processing
processing-voice = 🎤 Processing your voice message...
processing-transcribed-text = 🧠 Thinking about your request from audio...
error-transcription-failed = ⚠️ Failed to transcribe audio: { $error }
error-transcription-failed-unknown = ⚠️ Failed to transcribe audio due to an unknown error.
error-processing-voice = ⚠️ An error occurred while processing your voice message.

# Document Processing
error-doc-unsupported-type = ⚠️ File type ({ $mime_type }) is not supported. Please upload PDF, DOCX, or TXT.
error-doc-too-large = ⚠️ File is too large. Maximum size: { $limit_mb } MB.
processing-document = 📄 Processing document '{ $filename }'... This may take a while.
processing-extracted-text = 🧠 Analyzing text from document '{ $filename }'...

# AI Models
model-prompt = Select an AI model for text generation:
model-chosen = AI model set to: { $model_name }

# Creating a new chat
newchat-started = ✨ Alright, let's start a new conversation! I've forgotten the previous context.

# Keyboard
main-keyboard-placeholder = Select a command or enter text...
button-retry-request = 🔁 Retry request?
settings-current-prompt = Current Gemini generation settings:
settings-button-temperature = 🌡️ Temperature: { $value }
settings-button-max-tokens = 📏 Max length: { $value }
settings-prompt-temperature = Select temperature (affects creativity):
settings-prompt-max-tokens = Select maximum response length (in tokens):
settings-option-default = Default ({ $value })
settings-option-temperature-precise = 0.3 (Precise)
settings-option-temperature-balanced = 0.7 (Balanced)
settings-option-temperature-creative = 1.4 (Creative)
settings-option-max-tokens-short = 512 (Short)
settings-option-max-tokens-medium = 1024 (Medium)
settings-option-max-tokens-long = 2048 (Long)
settings-option-max-tokens-very_long = 8192 (Very long)
button-back = ⬅️ Back

# Error messages
error-gemini-fetch = 😔 Failed to get a response from Gemini. Please try again later.
error-image-download = 😔 Failed to load your image. Please try again.
error-image-analysis = 😔 Failed to analyze the image with Gemini. Please try again later.
error-display = 😔 An error occurred while displaying the response. Please try again later.
error-general = 😔 An unexpected error occurred. Please try again later.
error-blocked-content = My response was blocked due to safety restrictions (Reason: { $reason }). Please try rephrasing your request.
error-blocked-image-content = My response to the image was blocked due to safety restrictions (Reason: { $reason }).
error-gemini-api-key = Error: Gemini API key is not configured.
error-gemini-request = An error occurred while contacting Gemini: Contact the administrator!
error-image-analysis-request = An error occurred while analyzing the image: Contact the administrator!
error-retry-not-found = 🤷 Couldn't find the previous request to retry. Maybe the bot was restarted.
error-quota-exceeded = Oops! It seems I'm too popular right now and have reached the AI request limit. Try again a bit later. 🙏
error-settings-save = ❌ Failed to save setting. Try again.
error-image-api_error = ❌ Image generation API error. Try again later.
error-image-timeout_error = ⏳ Image generation server is not responding or the model is loading. Try again later.
error-image-rate_limit_error = 🚦 Too many requests! Image generation limit exceeded. Try again later.
error-image-content_filter_error = 🙅 Request rejected by safety filter. Try modifying the prompt.
error-image-unknown = ❓ Unknown error during image generation.
error-telegram-send = 😔 Failed to send the generated image.
error-doc-parsing-pdf = ❌ Error reading PDF file. It may be corrupted or encrypted.
error-doc-parsing-docx = ❌ Error reading DOCX file. It may be corrupted.
error-doc-parsing-txt = ❌ Error reading text file (encoding issue).
error-doc-parsing-lib_missing = ❌ Required library ({ $library }) for processing this file type is not installed on the server.
error-doc-parsing-emptydoc = ⚠️ Document contains no text or text could not be extracted.
error-doc-parsing-unknown = ❓ Unknown error while extracting text from the document.
error-doc-processing-general = ⚠️ An error occurred while processing your document.
response-truncated = [Response was truncated due to message length limitations]