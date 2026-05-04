# Private chat rate limiting settings
PRIVATE_RATE_LIMIT_COUNT = 3
PRIVATE_RATE_LIMIT_WINDOW = 15
PRIVATE_PROCESS_DELAY = 1

# Group chat rate limiting settings
GROUP_RATE_LIMIT_COUNT = 5
GROUP_RATE_LIMIT_WINDOW = 15
GROUP_PROCESS_DELAY = 1
GROUP_PHISHING_THRESHOLD = 2

# Supported language settings
SUPPORTED_LANGUAGE_CODES = {"en", "id", "ms"}
MIN_LANGUAGE_DETECTION_CHARS = 8

# Input length validation settings
MAX_PRIVATE_MESSAGE_LENGTH = 1000