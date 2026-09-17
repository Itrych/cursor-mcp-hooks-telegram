from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field


@dataclass
class PendingAsk:
    request_id: str
    question: str
    options: list[str]
    message_id: int | None = None
    future: asyncio.Future[str] = field(default_factory=lambda: asyncio.get_running_loop().create_future())


class PendingStore:
    def __init__(self) -> None:
        self._items: dict[str, PendingAsk] = {}
        self._by_message: dict[int, str] = {}

    @staticmethod
    def new_id() -> str:
        return secrets.token_hex(6)

    def add(self, question: str, options: list[str]) -> PendingAsk:
        request_id = self.new_id()
        item = PendingAsk(request_id=request_id, question=question, options=options)
        self._items[request_id] = item
        return item

    def bind_message(self, request_id: str, message_id: int) -> None:
        item = self._items.get(request_id)
        if item is None:
            return
        item.message_id = message_id
        self._by_message[message_id] = request_id

    def get(self, request_id: str) -> PendingAsk | None:
        return self._items.get(request_id)

    def get_by_message(self, message_id: int) -> PendingAsk | None:
        request_id = self._by_message.get(message_id)
        if request_id is None:
            return None
        return self._items.get(request_id)

    def oldest(self) -> PendingAsk | None:
        if not self._items:
            return None
        return next(iter(self._items.values()))

    def count(self) -> int:
        return len(self._items)

    def resolve(self, request_id: str, answer: str) -> PendingAsk | None:
        item = self._items.pop(request_id, None)
        if item is None:
            return None
        if item.message_id is not None:
            self._by_message.pop(item.message_id, None)
        if not item.future.done():
            item.future.set_result(answer)
        return item

    def fail(self, request_id: str, error: BaseException) -> PendingAsk | None:
        item = self._items.pop(request_id, None)
        if item is None:
            return None
        if item.message_id is not None:
            self._by_message.pop(item.message_id, None)
        if not item.future.done():
            item.future.set_exception(error)
        return item

    def abandon(self, request_id: str) -> PendingAsk | None:
        item = self._items.pop(request_id, None)
        if item is None:
            return None
        if item.message_id is not None:
            self._by_message.pop(item.message_id, None)
        if not item.future.done():
            item.future.cancel()
        return item
