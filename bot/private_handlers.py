from telegram import Update
from telegram.ext import ContextTypes

import asyncio
import time

from core.ml_classifier import predict_label
from core.rag_retriever import retrieve_similar_examples
from core.llm_explanation import generate_explanation, verify_safe_message
from core.language_validation import is_supported_language

from bot.bot_config import (
    PRIVATE_RATE_LIMIT_COUNT,
    PRIVATE_RATE_LIMIT_WINDOW,
    PRIVATE_PROCESS_DELAY,
    MAX_PRIVATE_MESSAGE_LENGTH,
)

from bot.bot_state import (
    active_private_users,
    private_message_buffer,
    private_process_tasks,
    private_non_text_buffer,
    private_non_text_process_tasks,
)


# Process private chat text messages after a short delay
async def process_private_messages_after_delay(
        user_id: int,
        chat_id: int,
        context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        await asyncio.sleep(PRIVATE_PROCESS_DELAY)

        messages = private_message_buffer[user_id]
        now = time.time()

        recent_messages = [
            item for item in messages
            if now - item["timestamp"] <= PRIVATE_RATE_LIMIT_WINDOW
        ]

        private_message_buffer[user_id] = recent_messages

        # If user sends more than 3 messages within 15 seconds, show one spam alert only
        if len(recent_messages) > PRIVATE_RATE_LIMIT_COUNT:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "🛑 Anda menghantar mesej terlalu cepat.\n\n"
                    f"Sebanyak {len(recent_messages)} mesej dikesan dalam {PRIVATE_RATE_LIMIT_WINDOW} saat.\n"
                    "Sila tunggu sebentar sebelum menghantar mesej untuk diimbas semula."
                )
            )

            private_message_buffer[user_id].clear()
            private_process_tasks.pop(user_id, None)
            return

        for item in recent_messages:
            message_text = item["text"]
            message_id = item["message_id"]

            # Private mode input length check
            if len(message_text) > MAX_PRIVATE_MESSAGE_LENGTH:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "⚠️ Mesej ini terlalu panjang untuk diimbas.\n\n"
                        f"Bot ini hanya menyokong mesej sehingga {MAX_PRIVATE_MESSAGE_LENGTH} aksara bagi setiap imbasan.\n"
                        "Sila ringkaskan mesej atau hantar bahagian penting sahaja untuk diimbas."
                    ),
                    reply_to_message_id=message_id
                )
                continue

            # Private mode language scope check
            if not is_supported_language(message_text):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "⚠️ Bahasa mesej tidak disokong.\n\n"
                        "Bot ini hanya menyokong pengesanan phishing/scam untuk mesej dalam Bahasa Melayu atau campuran Bahasa-Inggeris sahaja.\n\n"
                        "Sila hantar semula mesej dalam bahasa yang disokong untuk diimbas."
                    ),
                    reply_to_message_id=message_id
                )
                continue

            prediction = predict_label(message_text)

            similar_examples = retrieve_similar_examples(
                message_text,
                top_k=3,
                label_filter=1
            )

            if prediction == 1:
                explanation = generate_explanation(message_text, similar_examples)

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                            "⚠️ Amaran: Mesej ini disyaki sebagai phishing/scam.\n\n"
                            + explanation
                    ),
                    reply_to_message_id=message_id
                )
                continue

            llm_suspicious = verify_safe_message(message_text, similar_examples)

            if llm_suspicious:
                explanation = generate_explanation(message_text, similar_examples)

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                            "⚠️ Amaran: Mesej ini kemungkinan mempunyai unsur phishing/scam.\n\n"
                            "Sila buat semakan terlebih dahulu sebelum melakukan apa-apa tindakan.\n\n"
                            + explanation
                    ),
                    reply_to_message_id=message_id
                )
                continue

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "✅ Mesej ini kelihatan selamat.\n\n"
                    "Tiada corak phishing/scam yang jelas dikesan."
                ),
                reply_to_message_id=message_id
            )

        private_message_buffer[user_id].clear()
        private_process_tasks.pop(user_id, None)

    except asyncio.CancelledError:
        return


# Process unsupported private chat content after a short delay
async def process_private_non_text_after_delay(
        user_id: int,
        chat_id: int,
        context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        await asyncio.sleep(PRIVATE_PROCESS_DELAY)

        messages = private_non_text_buffer[user_id]
        now = time.time()

        recent_messages = [
            item for item in messages
            if now - item["timestamp"] <= PRIVATE_RATE_LIMIT_WINDOW
        ]

        private_non_text_buffer[user_id] = recent_messages

        # If user sends more than 3 unsupported items, show one general warning only
        if len(recent_messages) > PRIVATE_RATE_LIMIT_COUNT:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "🛑 Terlalu banyak kandungan tidak disokong dihantar.\n\n"
                    f"Sebanyak {len(recent_messages)} kandungan bukan teks dikesan dalam {PRIVATE_RATE_LIMIT_WINDOW} saat.\n"
                    "Bot ini hanya menyokong pengesanan phishing/scam berasaskan teks sahaja.\n"
                    "Sila salin dan hantar kandungan teks mesej tersebut untuk diimbas semula."
                )
            )

            private_non_text_buffer[user_id].clear()
            private_non_text_process_tasks.pop(user_id, None)
            return

        for item in recent_messages:
            message_id = item["message_id"]

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "⚠️ Kandungan ini tidak dapat diimbas.\n\n"
                    "Bot ini hanya menyokong pengesanan phishing/scam berasaskan teks sahaja.\n"
                    "Sila salin dan hantar kandungan teks mesej tersebut untuk diimbas semula."
                ),
                reply_to_message_id=message_id
            )

        private_non_text_buffer[user_id].clear()
        private_non_text_process_tasks.pop(user_id, None)

    except asyncio.CancelledError:
        return


# Handle private chat text messages
async def handle_private_text_message(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.message is None or update.message.text is None:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # In private chat, only scan messages after user activates /scan
    if user_id not in active_private_users:
        await update.message.reply_text(
            "Sila taip /scan untuk mengaktifkan Private Chat Detector Mode."
        )
        return

    private_message_buffer[user_id].append({
        "text": update.message.text,
        "timestamp": time.time(),
        "message_id": update.message.message_id
    })

    if user_id in private_process_tasks:
        private_process_tasks[user_id].cancel()

    private_process_tasks[user_id] = asyncio.create_task(
        process_private_messages_after_delay(
            user_id,
            chat_id,
            context
        )
    )


# Handle non-text content in private chat mode
async def handle_non_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message_id = update.message.message_id

    # Only handle non-text content in private chat
    if chat_type != "private":
        return

    # If private detector mode is not active, ask user to activate /scan first
    if user_id not in active_private_users:
        await update.message.reply_text(
            "Sila taip /scan untuk mengaktifkan Private Chat Detector Mode.",
            reply_to_message_id=message_id
        )
        return

    private_non_text_buffer[user_id].append({
        "timestamp": time.time(),
        "message_id": message_id
    })

    if user_id in private_non_text_process_tasks:
        private_non_text_process_tasks[user_id].cancel()

    private_non_text_process_tasks[user_id] = asyncio.create_task(
        process_private_non_text_after_delay(
            user_id,
            chat_id,
            context
        )
    )