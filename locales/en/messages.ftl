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
    /model - Select an AI model for text generation
    /language - Change the interface language
    /help - Show this message

    <b>How to use:</b>
    - Just send me a text message.
    - Send an image. You can add a caption to ask a specific question about it (e.g., <code>"What's unusual in this picture?"</code>). If there's no caption, I'll describe it.

# Processing messages
thinking = 🧠 Thinking about your question...
analyzing = 🖼️ Analyzing the image...

# AI Models
model-prompt = Select an AI model for text generation:
model-chosen = AI model set to: { $model_name }

# Creating a new chat
newchat-started = ✨ Alright, let's start a new conversation! I've forgotten the previous context.

# Keyboard
main-keyboard-placeholder = Select a command or enter text...

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