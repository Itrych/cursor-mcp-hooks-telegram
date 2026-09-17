from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from telegram_bridge.exceptions import ConfigError

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def _get(name: str, file_values: dict[str, str], default: str | None = None) -> str | None:
    if name in os.environ and os.environ[name] != "":
        return os.environ[name]
    if name in file_values and file_values[name] != "":
        return file_values[name]
    return default


@dataclass(frozen=True)
class Settings:
    bot_token: str
    chat_id: int
    bridge_host: str
    bridge_port: int
    bridge_api_token: str
    ask_timeout_sec: int

    @property
    def api_base(self) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}"


def load_settings() -> Settings:
    file_values = _parse_env_file(ENV_FILE)
    token = _get("TELEGRAM_BOT_TOKEN", file_values)
    chat_id_raw = _get("TELEGRAM_CHAT_ID", file_values)
    if not token:
        raise ConfigError(
            "TELEGRAM_BOT_TOKEN is missing. Copy .env.example to .env and fill it in."
        )
    if not chat_id_raw:
        raise ConfigError(
            "TELEGRAM_CHAT_ID is missing. See _docs/telegram-bot-setup.md."
        )
    try:
        chat_id = int(chat_id_raw)
    except ValueError as exc:
        raise ConfigError("TELEGRAM_CHAT_ID must be an integer.") from exc

    port_raw = _get("BRIDGE_PORT", file_values, "8765") or "8765"
    timeout_raw = _get("ASK_TIMEOUT_SEC", file_values, "900") or "900"
    try:
        port = int(port_raw)
        timeout = int(timeout_raw)
    except ValueError as exc:
        raise ConfigError("BRIDGE_PORT and ASK_TIMEOUT_SEC must be integers.") from exc
    if timeout <= 0:
        raise ConfigError("ASK_TIMEOUT_SEC must be > 0.")

    host = _get("BRIDGE_HOST", file_values, "127.0.0.1") or "127.0.0.1"
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ConfigError("BRIDGE_HOST must be a loopback address.")

    api_token = _get("BRIDGE_API_TOKEN", file_values, "") or ""
    if not api_token:
        raise ConfigError("BRIDGE_API_TOKEN is missing. Put a random string in .env.")

    return Settings(
        bot_token=token,
        chat_id=chat_id,
        bridge_host=host,
        bridge_port=port,
        bridge_api_token=api_token,
        ask_timeout_sec=timeout,
    )
