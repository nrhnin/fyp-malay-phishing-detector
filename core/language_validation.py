import re

from bot.bot_config import MIN_LANGUAGE_DETECTION_CHARS


# Check whether text contains Cyrillic characters
def contains_cyrillic(text: str) -> bool:
    return any("\u0400" <= char <= "\u04FF" for char in text)


# Extract URL-like or domain-like text from a message
def extract_url_like_tokens(text: str) -> list[str]:
    url_pattern = r"(https?://\S+|www\.\S+|[^\s]+\.[a-zA-Z]{2,}[^\s]*)"
    return re.findall(url_pattern, text)


# Detect possible homoglyph attack where Cyrillic characters appear inside links/domains
def contains_cyrillic_in_url_like_text(message_text: str) -> bool:
    text = str(message_text).strip()
    url_like_tokens = extract_url_like_tokens(text)

    for token in url_like_tokens:
        if contains_cyrillic(token):
            return True

    return False


# Check whether the message uses a supported script/writing system
def is_supported_language(message_text: str) -> bool:
    text = str(message_text).strip()

    # Reject obvious unsupported non-Latin writing systems
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

    # If no unsupported script is detected, allow the message.
    return True
