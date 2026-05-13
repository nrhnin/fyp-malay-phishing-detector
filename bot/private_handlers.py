from telegram import Update
from telegram.ext import ContextTypes

import asyncio
import time

from core.ml_classifier import predict_label
from core.rag_retriever import retrieve_similar_examples
from core.llm_explanation import generate_explanation, verify_safe_message
from core.language_validation import (
    is_supported_language,
    contains_cyrillic_in_url_like_text,
)

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


# Text message handler

# Main handler for private chat text messages
async def handle_private_text(
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
            "Sila taip /scan untuk mengaktifkan Private Chat Mode."
        )
        return

    # Store text message temporarily before delayed processing
    private_message_buffer[user_id].append({
        "text": update.message.text,
        "timestamp": time.time(),
        "message_id": update.message.message_id
    })

    # Cancel previous delayed task if user sends another message quickly
    if user_id in private_process_tasks:
        private_process_tasks[user_id].cancel()

    # Start a new delayed processing task
    private_process_tasks[user_id] = asyncio.create_task(
        process_private_text(
            user_id,
            chat_id,
            context
        )
    )


# Non-text content handler

# Main handler for unsupported non-text content in private chat mode
async def handle_non_text(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.message is None:
        return

    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message_id = update.message.message_id

    # Only handle non-text content in private chat
    if chat_type != "private":
        return

    # If private chat mode is not active, ask user to activate /scan first
    if user_id not in active_private_users:
        await update.message.reply_text(
            "Sila taip /scan untuk mengaktifkan Private Chat Mode.",
            reply_to_message_id=message_id
        )
        return

    # Store unsupported content temporarily before delayed processing
    private_non_text_buffer[user_id].append({
        "timestamp": time.time(),
        "message_id": message_id
    })

    # Cancel previous delayed task if user sends another unsupported item quickly
    if user_id in private_non_text_process_tasks:
        private_non_text_process_tasks[user_id].cancel()

    # Start a new delayed processing task
    private_non_text_process_tasks[user_id] = asyncio.create_task(
        process_non_text(
            user_id,
            chat_id,
            context
        )
    )


# Text message processing

# Process text messages after a short delay
async def process_private_text(
        user_id: int,
        chat_id: int,
        context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        await asyncio.sleep(PRIVATE_PROCESS_DELAY)

        messages = private_message_buffer[user_id]
        now = time.time()

        # Keep only messages within the rate-limit window
        recent_messages = [
            item for item in messages
            if now - item["timestamp"] <= PRIVATE_RATE_LIMIT_WINDOW
        ]

        private_message_buffer[user_id] = recent_messages

        # If user sends more than the allowed threshold, show one spam alert only
        if len(recent_messages) > PRIVATE_RATE_LIMIT_COUNT:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "🛑 Anda menghantar mesej terlalu cepat.\n\n"
                    f"Sebanyak {len(recent_messages)} mesej dikesan dalam "
                    f"{PRIVATE_RATE_LIMIT_WINDOW} saat.\n"
                    "Sila tunggu sebentar sebelum menghantar mesej untuk diimbas semula."
                )
            )

            private_message_buffer[user_id].clear()
            private_process_tasks.pop(user_id, None)
            return

        # Process each buffered text message normally
        for item in recent_messages:
            message_text = item["text"]
            message_id = item["message_id"]

            # Input length check
            if len(message_text) > MAX_PRIVATE_MESSAGE_LENGTH:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "⚠️ Mesej ini terlalu panjang untuk diimbas.\n\n"
                        f"Bot ini hanya menyokong mesej sehingga "
                        f"{MAX_PRIVATE_MESSAGE_LENGTH} aksara bagi setiap imbasan.\n"
                        "Sila ringkaskan mesej atau hantar bahagian penting sahaja untuk diimbas."
                    ),
                    reply_to_message_id=message_id
                )
                continue

            # Homoglyph URL attack check
            if contains_cyrillic_in_url_like_text(message_text):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "⚠️ Amaran: Mesej ini dikesan sebagai phishing/scam.\n\n"
                        "Antara sebab-sebabnya:\n"
                        "• Pautan dalam mesej ini mengandungi aksara yang menyerupai huruf biasa, "
                        "tetapi sebenarnya menggunakan aksara bukan Latin seperti Cyrillic.\n"
                        "• Teknik ini boleh digunakan untuk menyamar sebagai pautan rasmi yang sah.\n\n"
                        "Sila buat semakan terlebih dahulu sebelum melakukan apa-apa tindakan."
                    ),
                    reply_to_message_id=message_id
                )
                continue

            # Language scope check
            if not is_supported_language(message_text):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "⚠️ Format bahasa mesej tidak disokong.\n\n"
                        "Bot ini hanya menyokong pengesanan untuk mesej "
                        "dalam Bahasa Melayu atau campuran Melayu-Inggeris sahaja.\n\n"
                        "Sila hantar semula mesej dalam bahasa yang disokong untuk diimbas."
                    ),
                    reply_to_message_id=message_id
                )
                continue

            # ML classification
            prediction = predict_label(message_text)

            # RAG retrieval using local dataset
            similar_examples = retrieve_similar_examples(
                message_text,
                top_k=3,
                label_filter=1
            )

            # If ML classifies message as phishing, display reasons
            if prediction == 1:
                explanation = generate_explanation(message_text, similar_examples)

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                            "⚠️ Amaran: Mesej ini dikesan sebagai phishing/scam.\n\n"
                            + explanation
                            + "\n\n"
                              "Sila buat semakan terlebih dahulu sebelum melakukan apa-apa tindakan."
                    ),
                    reply_to_message_id=message_id
                )
                continue

            # If ML classifies message as safe, use LLM verification for double-checking
            llm_suspicious = verify_safe_message(message_text, similar_examples)

            if llm_suspicious:
                explanation = generate_explanation(message_text, similar_examples)

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                            "⚠️ Amaran: Mesej ini kemungkinan mempunyai unsur phishing/scam.\n\n"
                            + explanation
                            + "\n\n"
                              "Sila buat semakan terlebih dahulu sebelum melakukan apa-apa tindakan."
                    ),
                    reply_to_message_id=message_id
                )
                continue

            # If ML and LLM verification do not detect suspicious patterns
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "✅ Mesej ini kelihatan selamat.\n\n"
                    "Tiada corak phishing/scam yang jelas dikesan."
                ),
                reply_to_message_id=message_id
            )

        # Clear processed messages and remove active task
        private_message_buffer[user_id].clear()
        private_process_tasks.pop(user_id, None)

    except asyncio.CancelledError:
        # Expected when a newer message arrives before the delay ends
        return


# Non-text / unsupported content processing

# Process unsupported content after a short delay
async def process_non_text(
        user_id: int,
        chat_id: int,
        context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        await asyncio.sleep(PRIVATE_PROCESS_DELAY)

        messages = private_non_text_buffer[user_id]
        now = time.time()

        # Keep only unsupported content within the rate-limit window
        recent_messages = [
            item for item in messages
            if now - item["timestamp"] <= PRIVATE_RATE_LIMIT_WINDOW
        ]

        private_non_text_buffer[user_id] = recent_messages

        # If user sends too many unsupported items, show one general warning only
        if len(recent_messages) > PRIVATE_RATE_LIMIT_COUNT:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "🛑 Terlalu banyak kandungan tidak disokong dihantar.\n\n"
                    f"Sebanyak {len(recent_messages)} kandungan bukan teks dikesan dalam "
                    f"{PRIVATE_RATE_LIMIT_WINDOW} saat.\n"
                    "Bot ini hanya menyokong pengesanan mesej berasaskan teks sahaja.\n"
                    "Sila salin dan hantar kandungan mesej tersebut untuk diimbas semula."
                )
            )

            private_non_text_buffer[user_id].clear()
            private_non_text_process_tasks.pop(user_id, None)
            return

        # If not spam, reply to each unsupported item directly
        for item in recent_messages:
            message_id = item["message_id"]

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "⚠️ Kandungan ini tidak dapat diimbas.\n\n"
                    "Bot ini hanya menyokong pengesanan mesej berasaskan teks sahaja.\n"
                    "Sila salin dan hantar kandungan mesej tersebut untuk diimbas semula."
                ),
                reply_to_message_id=message_id
            )

        # Clear processed unsupported items and remove active task
        private_non_text_buffer[user_id].clear()
        private_non_text_process_tasks.pop(user_id, None)

    except asyncio.CancelledError:
        # Expected when newer unsupported content arrives before the delay ends
        return
