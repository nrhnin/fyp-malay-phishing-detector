from telegram import Update
from telegram.ext import ContextTypes

import asyncio
import time

from core.ml_classifier import predict_label
from core.rag_retriever import retrieve_similar_examples
from core.llm_explanation import generate_explanation, verify_safe_message

from bot.bot_config import (
    GROUP_RATE_LIMIT_COUNT,
    GROUP_RATE_LIMIT_WINDOW,
    GROUP_PROCESS_DELAY,
    GROUP_PHISHING_THRESHOLD,
)

from bot.bot_state import (
    group_message_buffer,
    group_process_tasks,
)


# Text message handler

# Main handler for group chat text messages
async def handle_group_text_message(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.message is None or update.message.text is None:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    username = update.effective_user.username
    full_name = update.effective_user.full_name

    user_display = f"@{username}" if username else full_name

    # Use both chat_id and user_id so different users/groups do not share the same buffer
    group_key = (chat_id, user_id)

    # Store the group message temporarily before delayed processing
    group_message_buffer[group_key].append({
        "text": update.message.text,
        "timestamp": time.time(),
        "message_id": update.message.message_id,
        "user_display": user_display
    })

    # Cancel previous delayed task if the same user sends another message quickly
    if group_key in group_process_tasks:
        group_process_tasks[group_key].cancel()

    # Start a new delayed processing task
    group_process_tasks[group_key] = asyncio.create_task(
        process_group_messages_after_delay(
            group_key,
            chat_id,
            context
        )
    )


# Text message processing

# Process group chat text messages after a short delay
async def process_group_messages_after_delay(
        group_key: tuple,
        chat_id: int,
        context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        await asyncio.sleep(GROUP_PROCESS_DELAY)

        messages = group_message_buffer[group_key]
        now = time.time()

        # Keep only messages within the group rate-limit window
        recent_messages = [
            item for item in messages
            if now - item["timestamp"] <= GROUP_RATE_LIMIT_WINDOW
        ]

        group_message_buffer[group_key] = recent_messages

        phishing_messages = []

        # Scan all recent messages from the same user in the same group
        for item in recent_messages:
            message_text = item["text"]

            # ML classification
            prediction = predict_label(message_text)

            # RAG retrieval using local dataset
            similar_examples = retrieve_similar_examples(
                message_text,
                top_k=3,
                label_filter=1
            )

            # If ML classifies message as phishing/scam
            if prediction == 1:
                phishing_messages.append({
                    "message_id": item["message_id"],
                    "text": message_text,
                    "similar_examples": similar_examples,
                    "alert_type": "ml_phishing"
                })
                continue

            # If ML classifies message as safe, use LLM verification as double-check
            llm_suspicious = verify_safe_message(message_text, similar_examples)

            if llm_suspicious:
                phishing_messages.append({
                    "message_id": item["message_id"],
                    "text": message_text,
                    "similar_examples": similar_examples,
                    "alert_type": "llm_suspicious"
                })

        message_count = len(recent_messages)
        phishing_count = len(phishing_messages)

        user_display = recent_messages[-1]["user_display"] if recent_messages else "Pengguna ini"

        # Condition:
        # 1. User sends more than 5 messages in 15 seconds
        # 2. At least 2 messages are phishing
        # Output: One general group spam/scam alert only
        if (
                message_count > GROUP_RATE_LIMIT_COUNT
                and phishing_count >= GROUP_PHISHING_THRESHOLD
        ):
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "🛑 Amaran aktiviti mencurigakan.\n\n"
                    f"{user_display} telah menghantar {message_count} mesej dalam "
                    f"{GROUP_RATE_LIMIT_WINDOW} saat.\n"
                    f"Daripada jumlah tersebut, {phishing_count} mesej dikesan "
                    "berkemungkinan phishing/scam.\n\n"
                    "Sila berhati-hati dan elakkan berinteraksi dengan mesej tersebut."
                )
            )

            group_message_buffer[group_key].clear()
            group_process_tasks.pop(group_key, None)
            return

        # If only one phishing/scam message is detected, display normal phishing
        if phishing_count == 1:
            phishing_item = phishing_messages[0]
            explanation = generate_explanation(
                phishing_item["text"],
                phishing_item["similar_examples"]
            )

            if phishing_item["alert_type"] == "ml_phishing":
                alert_text = (
                        "⚠️ Amaran: Mesej ini disyaki sebagai phishing/scam.\n\n"
                        + explanation
                )
            else:
                alert_text = (
                        "⚠️ Amaran: Mesej ini kemungkinan mempunyai unsur phishing/scam.\n\n"
                        "Sila buat semakan terlebih dahulu sebelum melakukan apa-apa tindakan.\n\n"
                        + explanation
                )

            await context.bot.send_message(
                chat_id=chat_id,
                text=alert_text,
                reply_to_message_id=phishing_item["message_id"]
            )

            group_message_buffer[group_key].clear()
            group_process_tasks.pop(group_key, None)
            return

        # If there are multiple phishing messages but the user did not exceed the group spam threshold, reply to each phishing message normally
        if phishing_count > 1:
            for phishing_item in phishing_messages:
                explanation = generate_explanation(
                    phishing_item["text"],
                    phishing_item["similar_examples"]
                )

                if phishing_item["alert_type"] == "ml_phishing":
                    alert_text = (
                            "⚠️ Amaran: Mesej ini disyaki sebagai phishing/scam.\n\n"
                            + explanation
                    )
                else:
                    alert_text = (
                            "⚠️ Amaran: Mesej ini kemungkinan mempunyai unsur phishing/scam.\n\n"
                            "Sila buat semakan terlebih dahulu sebelum melakukan apa-apa tindakan.\n\n"
                            + explanation
                    )

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=alert_text,
                    reply_to_message_id=phishing_item["message_id"]
                )

        # If all messages are safe, group mode stays silent.
        group_message_buffer[group_key].clear()
        group_process_tasks.pop(group_key, None)

    except asyncio.CancelledError:
        # Expected when the same user sends another group message before the delay ends
        return
