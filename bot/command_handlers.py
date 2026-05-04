from telegram import Update
from telegram.ext import ContextTypes

from bot.bot_state import (
    active_private_users,
    private_message_buffer,
    private_process_tasks,
    private_non_text_buffer,
    private_non_text_process_tasks,
)


# Send a startup message when user types /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "👋 Selamat datang ke Malay Phishing and Scam Detector.\n\n"
            "Bot ini boleh digunakan dalam dua cara:\n\n"
            "1. Private Chat Detector\n"
            "Taip /scan untuk aktifkan mode semakan mesej secara peribadi.\n\n"
            "2. Group Scanner\n"
            "Tambah bot ini ke dalam group Telegram supaya mesej dalam group boleh dipantau secara automatik.\n\n"
            "Taip /help untuk panduan ringkas."
        )


# Send a help message when user types /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "📌 Panduan penggunaan:\n\n"
            "Private chat:\n"
            "• Taip /scan untuk aktifkan Private Chat Detector Mode.\n"
            "• Selepas itu, hantar mesej yang ingin diperiksa.\n"
            "• Bot hanya menyokong mesej teks dalam Bahasa Melayu atau campuran Bahasa-Inggeris sahaja.\n"
            "• Taip /stop untuk hentikan Private Chat Detector Mode.\n\n"
            "Group chat:\n"
            "• Tambah bot ke dalam group Telegram.\n"
            "• Bot akan mengimbas mesej teks secara automatik.\n"
            "• Jika mesej disyaki phishing/scam, bot akan menghantar amaran.\n\n"
            "Arahan:\n"
            "/start - Aktifkan bot\n"
            "/scan - Aktifkan Private Chat Detector Mode\n"
            "/stop - Hentikan Private Chat Detector Mode\n"
            "/help - Lihat panduan penggunaan"
        )


# Activate private detector mode
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        chat_type = update.effective_chat.type

        if chat_type != "private":
            await update.message.reply_text(
                "Arahan /scan hanya digunakan dalam chat peribadi.\n\n"
                "Dalam group chat, bot akan mengimbas mesej secara automatik."
            )
            return

        user_id = update.effective_user.id
        active_private_users.add(user_id)

        # Clear old buffered private text messages/tasks
        private_message_buffer[user_id].clear()

        if user_id in private_process_tasks:
            private_process_tasks[user_id].cancel()
            private_process_tasks.pop(user_id, None)

        # Clear old buffered unsupported content/tasks
        private_non_text_buffer[user_id].clear()

        if user_id in private_non_text_process_tasks:
            private_non_text_process_tasks[user_id].cancel()
            private_non_text_process_tasks.pop(user_id, None)

        await update.message.reply_text(
            "🟢 Private Chat Detector Mode telah diaktifkan.\n\n"
            "Sila hantar atau tampal mesej yang ingin diperiksa."
        )


# Stop private chat detection for the current user
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        chat_type = update.effective_chat.type

        if chat_type != "private":
            await update.message.reply_text(
                "Arahan /stop hanya digunakan dalam chat peribadi.\n\n"
                "Dalam group chat, bot akan terus mengimbas mesej secara automatik."
            )
            return

        user_id = update.effective_user.id
        active_private_users.discard(user_id)

        # Clear pending private text messages/tasks
        private_message_buffer[user_id].clear()

        if user_id in private_process_tasks:
            private_process_tasks[user_id].cancel()
            private_process_tasks.pop(user_id, None)

        # Clear pending unsupported content/tasks
        private_non_text_buffer[user_id].clear()

        if user_id in private_non_text_process_tasks:
            private_non_text_process_tasks[user_id].cancel()
            private_non_text_process_tasks.pop(user_id, None)

        await update.message.reply_text(
            "⛔️ Private Detector Mode telah dihentikan.\n\n"
            "Taip /scan untuk mengaktifkan semula."
        )