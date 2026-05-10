from bot.bot_config import MIN_LANGUAGE_DETECTION_CHARS


# Check whether the message uses a supported script/writing system
def is_supported_language(message_text: str) -> bool:
    text = str(message_text).strip()

    # Reject obvious unsupported non-Latin writing systems first
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

    # If no unsupported script is detected, allow empty or very short messages
    if len(text) < MIN_LANGUAGE_DETECTION_CHARS:
        return True

    # If no unsupported script is detected, allow the message
    # This supports Malay, English, Manglish, abbreviations, URLs, numbers, punctuation, and other Latin-based input
    return True
