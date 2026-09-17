from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from telegram_bridge.exceptions import TelegramApiError

_JSON_HEADERS = {"Content-Type": "application/json; charset=utf-8"}


class TelegramApi:
    def __init__(self, api_base: str, timeout_sec: int = 60) -> None:
        self._api_base = api_base.rstrip("/")
        self._timeout_sec = timeout_sec

    def call(self, method: str, payload: dict[str, Any] | None = None) -> Any:
        url = f"{self._api_base}/{method}"
        body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers=_JSON_HEADERS,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_sec) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise TelegramApiError(f"{method} failed HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise TelegramApiError(f"{method} network error: {exc.reason}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TelegramApiError(f"{method} returned non-JSON.") from exc
        if not data.get("ok"):
            raise TelegramApiError(f"{method} rejected: {data.get('description', data)}")
        return data.get("result")

    def delete_webhook(self, drop_pending_updates: bool = True) -> None:
        self.call(
            "deleteWebhook",
            {"drop_pending_updates": drop_pending_updates},
        )

    def get_updates(
        self,
        offset: int | None,
        timeout: int,
        allowed_updates: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": timeout,
            "allowed_updates": allowed_updates
            or ["message", "callback_query"],
        }
        if offset is not None:
            payload["offset"] = offset
        result = self.call("getUpdates", payload)
        if result is None:
            return []
        if not isinstance(result, list):
            raise TelegramApiError("getUpdates result is not a list.")
        return result

    def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        result = self.call("sendMessage", payload)
        if not isinstance(result, dict):
            raise TelegramApiError("sendMessage result is not an object.")
        return result

    def answer_callback_query(self, callback_query_id: str, text: str | None = None) -> None:
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        self.call("answerCallbackQuery", payload)

    def clear_inline_keyboard(self, chat_id: int, message_id: int) -> None:
        self.call(
            "editMessageReplyMarkup",
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": {"inline_keyboard": []},
            },
        )
