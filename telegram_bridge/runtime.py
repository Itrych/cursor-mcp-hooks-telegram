from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram_bridge.config import Settings
from telegram_bridge.exceptions import AskTimeout, TelegramApiError
from telegram_bridge.pending import PendingAsk, PendingStore
from telegram_bridge.telegram_api import TelegramApi

log = logging.getLogger("telegram_bridge")

CALLBACK_PREFIX = "q:"
MAX_OPTION_LABEL = 40


def _option_rows(request_id: str, options: list[str]) -> list[list[dict[str, str]]]:
    rows: list[list[dict[str, str]]] = []
    for index, label in enumerate(options):
        text = label if len(label) <= MAX_OPTION_LABEL else label[: MAX_OPTION_LABEL - 1] + "…"
        rows.append(
            [{"text": text, "callback_data": f"{CALLBACK_PREFIX}{request_id}:{index}"}]
        )
    return rows


def _parse_callback(data: str) -> tuple[str, int] | None:
    if not data.startswith(CALLBACK_PREFIX):
        return None
    body = data[len(CALLBACK_PREFIX) :]
    request_id, sep, index_raw = body.rpartition(":")
    if not sep or not request_id:
        return None
    try:
        return request_id, int(index_raw)
    except ValueError:
        return None


class BridgeRuntime:
    def __init__(self, settings: Settings, api: TelegramApi | None = None) -> None:
        self.settings = settings
        self.api = api or TelegramApi(settings.api_base)
        self.pending = PendingStore()
        self._stop = asyncio.Event()
        self._poll_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        await asyncio.to_thread(self.api.delete_webhook, True)
        self._stop.clear()
        self._poll_task = asyncio.create_task(self._poll_loop(), name="telegram-poll")

    async def stop(self) -> None:
        self._stop.set()
        if self._poll_task is not None:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

    async def notify(self, message: str) -> None:
        await asyncio.to_thread(
            self.api.send_message,
            self.settings.chat_id,
            message,
            None,
        )

    async def ask(
        self,
        question: str,
        options: list[str] | None = None,
        timeout_sec: int | None = None,
    ) -> str:
        option_list = [item.strip() for item in (options or []) if item.strip()]
        item = self.pending.add(question, option_list)
        text = question.strip()
        if option_list:
            text += "\n\nМожно нажать кнопку или ответить текстом (лучше reply на это сообщение)."
        else:
            text += "\n\nОтветьте текстом в этот чат (лучше reply на это сообщение)."

        markup = None
        if option_list:
            markup = {"inline_keyboard": _option_rows(item.request_id, option_list)}

        try:
            sent = await asyncio.to_thread(
                self.api.send_message,
                self.settings.chat_id,
                text,
                markup,
            )
        except Exception as exc:
            self.pending.fail(item.request_id, exc)
            raise

        message_id = int(sent["message_id"])
        self.pending.bind_message(item.request_id, message_id)

        wait_sec = timeout_sec if timeout_sec is not None else self.settings.ask_timeout_sec
        try:
            return await asyncio.wait_for(asyncio.shield(item.future), timeout=wait_sec)
        except asyncio.TimeoutError as exc:
            if item.future.done() and not item.future.cancelled():
                return item.future.result()
            self.pending.abandon(item.request_id)
            await self._safe_clear_keyboard(message_id)
            raise AskTimeout(
                f"No Telegram reply in {wait_sec} seconds."
            ) from exc

    async def _safe_clear_keyboard(self, message_id: int) -> None:
        try:
            await asyncio.to_thread(
                self.api.clear_inline_keyboard,
                self.settings.chat_id,
                message_id,
            )
        except TelegramApiError:
            log.debug("Could not clear inline keyboard for message %s", message_id)

    async def _poll_loop(self) -> None:
        offset: int | None = None
        while not self._stop.is_set():
            try:
                updates = await asyncio.to_thread(
                    self.api.get_updates,
                    offset,
                    25,
                    ["message", "callback_query"],
                )
            except asyncio.CancelledError:
                raise
            except TelegramApiError:
                log.exception("getUpdates failed")
                await asyncio.sleep(3)
                continue
            for update in updates:
                update_id = int(update["update_id"])
                offset = update_id + 1
                try:
                    await self._handle_update(update)
                except Exception:
                    log.exception("Failed to handle update %s", update_id)

    async def _handle_update(self, update: dict[str, Any]) -> None:
        if "callback_query" in update:
            await self._handle_callback(update["callback_query"])
            return
        message = update.get("message")
        if isinstance(message, dict):
            await self._handle_message(message)

    def _is_allowed_chat(self, chat_id: int) -> bool:
        return chat_id == self.settings.chat_id

    async def _handle_callback(self, query: dict[str, Any]) -> None:
        callback_id = str(query.get("id", ""))
        data = str(query.get("data") or "")
        from_chat = query.get("message", {}).get("chat", {}).get("id")
        if from_chat is None or not self._is_allowed_chat(int(from_chat)):
            if callback_id:
                await asyncio.to_thread(self.api.answer_callback_query, callback_id, "Ignored")
            return

        parsed = _parse_callback(data)
        if parsed is None:
            await asyncio.to_thread(self.api.answer_callback_query, callback_id, "Unknown button")
            return
        request_id, index = parsed
        item = self.pending.get(request_id)
        if item is None:
            await asyncio.to_thread(self.api.answer_callback_query, callback_id, "Already answered")
            return
        if index < 0 or index >= len(item.options):
            await asyncio.to_thread(self.api.answer_callback_query, callback_id, "Invalid option")
            return

        answer = item.options[index]
        message_id = item.message_id
        resolved = self.pending.resolve(request_id, answer)
        if resolved is None:
            return
        await asyncio.to_thread(self.api.answer_callback_query, callback_id, "OK")
        if message_id is not None:
            await self._safe_clear_keyboard(message_id)

    async def _handle_message(self, message: dict[str, Any]) -> None:
        chat_id = int(message.get("chat", {}).get("id", 0))
        if not self._is_allowed_chat(chat_id):
            return
        text = (message.get("text") or "").strip()
        if not text or text.startswith("/"):
            return

        reply = message.get("reply_to_message")
        item: PendingAsk | None = None
        if isinstance(reply, dict) and "message_id" in reply:
            item = self.pending.get_by_message(int(reply["message_id"]))
        if item is None:
            if self.pending.count() == 1:
                item = self.pending.oldest()
            elif self.pending.count() > 1:
                await asyncio.to_thread(
                    self.api.send_message,
                    self.settings.chat_id,
                    "Сейчас несколько вопросов. Ответьте reply на нужное сообщение.",
                    None,
                )
                return
        if item is None:
            return

        message_id = item.message_id
        resolved = self.pending.resolve(item.request_id, text)
        if resolved is None:
            return
        if message_id is not None:
            await self._safe_clear_keyboard(message_id)
