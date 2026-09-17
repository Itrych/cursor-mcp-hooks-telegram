class BridgeError(Exception):
    """Base error for the Telegram bridge."""


class ConfigError(BridgeError):
    """Missing or invalid configuration."""


class TelegramApiError(BridgeError):
    """Telegram Bot API returned an error or an unexpected payload."""


class AskTimeout(BridgeError):
    """The user did not answer before ASK_TIMEOUT_SEC."""
