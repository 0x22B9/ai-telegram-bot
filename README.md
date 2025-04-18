# Telegram AI Bot (Gemini & More)

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-blue.svg)](https://github.com/aiogram/aiogram)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

This is an advanced, modular Telegram bot leveraging the power of Google's Gemini AI models for various tasks, including text generation, image analysis, audio transcription, document processing, and image generation via the Hugging Face API. It features a multilingual interface and remembers conversation context.

## ✨ Features

*   **🧠 Gemini Integration**: Utilizes Google Gemini Pro/Flash for intelligent text generation and image understanding.
*   **🗣️ Conversation History (Context Awareness)**: The bot remembers your previous interactions within a session for more coherent and context-aware conversations.
*   **🎙️ Voice Message Processing**: Send a voice message, and the bot will transcribe it using Gemini and respond to the transcribed text.
*   **📄 Document Analysis (PDF, DOCX, TXT)**: Upload PDF, DOCX, or plain text files. The bot extracts the text and uses Gemini for analysis, summarization, or answering questions about the content. (Uses `pypdf` and `python-docx`).
*   **🎨 Image Generation**: Create unique images from text descriptions using the `/generate_image` command (powered by Hugging Face Inference API - e.g., Stable Diffusion).
*   **🌐 Multilingual Support**: Switch the bot's interface language on the fly using the `/language` command. Currently supports:
    *   English (en)
    *   Spanish (es)
    *   Chinese (zh)
    *   Kazakh (kk)
    *   Ukrainian (uk)
    *   Russian (ru)
*   **⚙️ Customizable AI Settings**: Adjust Gemini's `temperature` (creativity) and `max_output_tokens` (response length) using the `/settings` command. Settings are saved per user in MongoDB.
*   **✍️ Real-time Typing Indicator**: Provides visual feedback ("Typing...") while the AI is processing your request.
*   **🔄 Error Handling with Retry Option**: If an AI request fails, a convenient "Retry request?" button appears to try again.
*   **⌨️ Interactive Keyboard**: Custom reply keyboard with main commands for easy access.
*   **🧼 Cleaned AI Responses**: Removes Markdown formatting from Gemini's raw output for better readability in Telegram (using HTML parse mode).
*   **🔐 Privacy Focused**: Includes a `/delete_my_data` command allowing users to completely remove their data (history, settings) from the database.
*   **🚀 Modular Design**: Built with a clean, modular structure using aiogram Routers for easy maintenance and extension.
*   **☁️ Fly.io Ready**: Includes `Dockerfile` and configuration hints for easy deployment on [Fly.io](https://fly.io/).

## 🚀 Getting Started (Local Setup)

1.  **Prerequisites:**
    *   Python 3.12+
    *   Git
    *   Access to a MongoDB database (e.g., MongoDB Atlas free tier)

2.  **Clone the Repository:**
    ```bash
    git clone https://github.com/0x22B9/ai-telegram-bot.git
    cd ai-telegram-bot
    ```

3.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    # or
    .\venv\Scripts\activate   # Windows
    ```

4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Configure Environment Variables:**
    Create a `.env` file in the project root directory (where `requirements.txt` is). Add the following variables, replacing the placeholder values with your actual credentials:

    ```ini
    # .env file
    TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
    GEMINI_API_KEY=YOUR_GOOGLE_GEMINI_API_KEY
    MONGO_URI=YOUR_MONGODB_CONNECTION_STRING # e.g., mongodb+srv://user:password@your-cluster.link.mongodb.net/your-db?retryWrites=true&w=majority&appName=your-cluster
    MONGO_DB_NAME=your_database_name # e.g., your-db
    HUGGINGFACE_API_TOKEN=hf_YOUR_HUGGINGFACE_READ_TOKEN
    IMAGE_GEN_MODEL_ID=stabilityai/stable-diffusion-3-medium-diffusers # Or another model ID
    ```
    *   Get Telegram Token from [@BotFather](https://t.me/BotFather).
    *   Get Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey).
    *   Get Hugging Face Token from [Hugging Face Settings](https://huggingface.co/settings/tokens).
    *   **Important:** Add `.env` to your `.gitignore` file to avoid committing secrets!

6.  **Run the Bot:**
    ```bash
    python -m src.bot
    ```

## 🤖 Bot Commands

*   `/start` - Restart the bot and show the welcome message.
*   `/newchat` - Clear your conversation history and start fresh.
*   `/generate_image` - Generate an image from a text prompt (uses Hugging Face API).
*   `/model` - Choose the Gemini AI model for text generation (e.g., `gemini-1.5-flash-latest`, `gemini-pro`).
*   `/language` - Switch the bot's interface language.
*   `/settings` - Adjust Gemini settings (temperature, max response length).
*   `/help` - Display this list of commands.
*   `/delete_my_data` - Permanently delete all your data (history, settings) associated with the bot.

## ☁️ Deployment (Fly.io)

This bot is configured for easy deployment on [Fly.io](https://fly.io/).

1.  **Install `flyctl`:** Follow the [official instructions](https://fly.io/docs/hands-on/install-flyctl/).
2.  **Login:** `fly auth login`
3.  **Launch (if first time):** `fly launch` (Answer 'no' to Postgres/Redis setup). This creates `fly.toml`. Review the generated `fly.toml` and `Dockerfile`. You might need to remove default HTTP health checks if they cause deployment failures.
4.  **Set Secrets:** **Do not** put secrets in `fly.toml`. Use `fly secrets set`:
    ```bash
    fly secrets set TELEGRAM_BOT_TOKEN="..." GEMINI_API_KEY="..." MONGO_URI="..." MONGO_DB_NAME="..." HUGGINGFACE_API_TOKEN="..." -a your-fly-app-name
    ```
5.  **Deploy:**
    ```bash
    fly deploy -a your-fly-app-name
    ```
6.  **Monitor:**
    ```bash
    fly status -a your-fly-app-name
    fly logs -a your-fly-app-name
    ```
7.  **Automated Deployment (Optional):** Set up GitHub Actions using the provided `.github/workflows/fly_deploy.yml` example (see previous instructions on setting `FLY_API_TOKEN` secret in GitHub).

## 🛠️ Technology Stack

*   **Python 3.12+**
*   **aiogram 3.x**: Asynchronous Telegram Bot Framework
*   **Google Gemini API**: For Text, Image, and Audio processing
*   **Hugging Face Inference API**: For Image Generation
*   **MongoDB**: NoSQL Database for storing user data and history (via `motor`)
*   **Fluent**: For handling localization and multilingual support
*   **pypdf**: Library for extracting text from PDF files
*   **python-docx**: Library for extracting text from DOCX files
*   **Docker**: For containerization
*   **Fly.io**: Platform for hosting the containerized application

## 🌐 Localization (Adding Languages)

The bot uses the [Fluent](https://projectfluent.org/) localization system for its interface text and standard AI prompts. Adding support for a new language is straightforward:

1.  **Create Directory:** Add a new subdirectory inside the `locales/` folder using the [ISO 639-1 language code](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g., `locales/fr/` for French).
2.  **Copy `.ftl` File:** Copy the `messages.ftl` file from an existing language directory (e.g., `locales/en/messages.ftl`) into your new language directory (`locales/fr/messages.ftl`).
3.  **Translate:** Open the newly copied `messages.ftl` file and translate all the string values (the text after the `=`) into the target language. Keep the message IDs (the text before the `=`) exactly the same. Pay attention to variables like `{ $filename }` or `{ $limit_mb }` – they should remain in the translated strings where appropriate.
4.  **Update Language List:** Добавьте в переменную SUPPORTED_LOCALES файла localization.py new language code.
5.  **Test:** Restart the bot and use the `/language` command to switch to the new language and verify the translations.

## 🤝 Contributing

Contributions are welcome! Whether it's fixing bugs, adding features, improving documentation, or translating the bot, your help is appreciated.

**Development Setup:**

Please follow the steps in the "Getting Started (Local Setup)" section to set up your development environment.

**Code Style:**

*   Please adhere to **PEP 8** coding standards.
*   I use **Ruff** for linting. Check for issues: `ruff check .`

**Making Contributions:**

1.  **Fork the repository** on GitHub.
2.  **Create a new branch** for your feature or bug fix: `git checkout -b feature/your-feature-name` or `git checkout -b fix/issue-description`.
3.  **Make your changes** and commit them with clear, descriptive messages.
4.  **Ensure code style** guidelines are followed (run Ruff).
5.  **Push your branch** to your forked repository: `git push origin feature/your-feature-name`.
6.  **Open a Pull Request** from your branch to the `main` branch of the original repository.
7.  Clearly describe the changes you've made in the Pull Request description. Link to any relevant issues.

**Reporting Issues:**

If you find a bug or have a suggestion, please open an issue on the [GitHub Issues page](https://github.com/0x22B9/ai-telegram-bot/issues). Provide as much detail as possible, including steps to reproduce, error messages, and your environment setup.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
