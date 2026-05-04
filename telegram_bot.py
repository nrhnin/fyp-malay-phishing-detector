from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import os
from dotenv import load_dotenv

from bot.command_handlers import (
    start_command,
    help_command,
    scan_command,
    stop_command,
)

from bot.private_handlers import (
    handle_private_text_message,
    handle_non_text_message,
)

from bot.group_handlers import handle_group_text_message


# Load environment variables from .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing. Please set it in the .env file.")


# Main message router
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.message.text is None:
        return

    chat_type = update.effective_chat.type

    if chat_type == "private":
        await handle_private_text_message(update, context)
        return

    if chat_type in ["group", "supergroup"]:
        await handle_group_text_message(update, context)
        return


# Print any runtime error to terminal for debugging
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Error: {context.error}")


# Initializes the Telegram bot and registers commands + message handlers
def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("stop", stop_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND, handle_non_text_message))

    app.add_error_handler(error_handler)

    PORT = int(os.getenv("PORT", 10000))
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH")
    WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN")

    if not WEBHOOK_URL:
        raise ValueError("WEBHOOK_URL is missing. Please set it in Render environment variables.")

    if not WEBHOOK_SECRET_PATH:
        raise ValueError("WEBHOOK_SECRET_PATH is missing. Please set it in Render environment variables.")

    if not WEBHOOK_SECRET_TOKEN:
        raise ValueError("WEBHOOK_SECRET_TOKEN is missing. Please set it in Render environment variables.")

    print("Bot is running in Render webhook mode...")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_SECRET_PATH,
        webhook_url=f"{WEBHOOK_URL}/{WEBHOOK_SECRET_PATH}",
        secret_token=WEBHOOK_SECRET_TOKEN,
    )


if __name__ == "__main__":
    main()