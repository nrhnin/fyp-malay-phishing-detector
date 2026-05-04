from langdetect import detect, DetectorFactory, LangDetectException

from bot.bot_config import (
    SUPPORTED_LANGUAGE_CODES,
    MIN_LANGUAGE_DETECTION_CHARS,
)


# Make langdetect output more consistent
DetectorFactory.seed = 0


# Check whether the message uses a supported language/script
def is_supported_language(message_text: str) -> bool:
    text = message_text.strip()

    # If message is too short, language detection is unreliable.
    # Allow short messages such as "ok", "hi", "ya", "tak", "yes".
    alphabetic_chars = [char for char in text if char.isalpha()]
    if len(alphabetic_chars) < MIN_LANGUAGE_DETECTION_CHARS:
        return True

    # Reject obvious unsupported writing systems
    unsupported_script_ranges = [
        ("\u0600", "\u06FF"),  # Arabic
        ("\u0750", "\u077F"),  # Arabic Supplement
        ("\u0B80", "\u0BFF"),  # Tamil
        ("\u4E00", "\u9FFF"),  # Chinese characters
        ("\u3040", "\u309F"),  # Japanese Hiragana
        ("\u30A0", "\u30FF"),  # Japanese Katakana
        ("\uAC00", "\uD7AF"),  # Korean Hangul
        ("\u0400", "\u04FF"),  # Cyrillic
    ]

    for char in text:
        for start, end in unsupported_script_ranges:
            if start <= char <= end:
                return False

    # Detect Latin-script language such as English, Malay, Indonesian, French, Spanish, etc.
    try:
        detected_language = detect(text)
    except LangDetectException:
        # If detection fails, allow it to continue.
        # This avoids blocking messages with many URLs, phone numbers, or symbols.
        return True

    return detected_language in SUPPORTED_LANGUAGE_CODES