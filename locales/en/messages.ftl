# Command descriptions and common phrases
start-prompt = Choose your preferred language:
start-welcome = Hello, { $user_name }! I'm an AI bot powered by Gemini. Send me text or an image (with or without a caption), and I'll try to respond. Use /help to see commands.
language-chosen = Language set to English. { start-welcome }
language-select-button = English 🇬🇧

help-text =
    I can respond to your text messages and analyze images using Gemini AI.

    **Commands:**
    /start - Restart the bot and choose language
    /help - Show this message

    **How to use:**
    - Just send me a text message.
    - Send an image. You can add a caption to ask a specific question about it (e.g., "What's unusual in this picture?"). If there's no caption, I'll describe it.

# Processing messages
thinking = 🧠 Thinking about your question...
analyzing = 🖼️ Analyzing the image...

# Error messages
error-gemini-fetch = 😔 Failed to get a response from Gemini. Please try again later.
error-image-download = 😔 Failed to load your image. Please try again.
error-image-analysis = 😔 Failed to analyze the image with Gemini. Please try again later.
error-display = 😔 An error occurred while displaying the response. Please try again later.
error-general = 😔 An unexpected error occurred. Please try again later.
error-blocked-content = My response was blocked due to safety restrictions (Reason: { $reason }). Please try rephrasing your request.
error-blocked-image-content = My response to the image was blocked due to safety restrictions (Reason: { $reason }).
error-gemini-api-key = Error: Gemini API key is not configured.
error-gemini-request = An error occurred while contacting Gemini: { $error }
error-image-analysis-request = An error occurred while analyzing the image: { $error }