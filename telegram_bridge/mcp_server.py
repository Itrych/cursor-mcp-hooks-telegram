from __future__ import annotations

import asyncio
import logging
import sys
from asyncio import AbstractServer
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

from telegram_bridge.config import Settings, load_settings
from telegram_bridge.exceptions import AskTimeout
from telegram_bridge.hook_client import BridgeUnavailable, bridge_request
from telegram_bridge.http_api import is_addr_in_use, start_http_server, stop_http_server
from telegram_bridge.runtime import BridgeRuntime

log = logging.getLogger("telegram_bridge.mcp")

_NO_REPLY = (
    "NO_REPLY: the user did not answer in Telegram before timeout. "
    "Do not assume a choice. Ask again or continue with a safe default."
)


@dataclass
class AppState:
    settings: Settings
    runtime: BridgeRuntime | None
    http: AbstractServer | None
    client_mode: bool


_state: AppState | None = None


def get_state() -> AppState:
    if _state is None:
        raise RuntimeError("Telegram bridge is not started yet.")
    return _state


@asynccontextmanager
async def _lifespan(_server: FastMCP) -> AsyncIterator[AppState]:
    global _state
    settings = load_settings()
    runtime: BridgeRuntime | None = None
    http: AbstractServer | None = None
    owner = BridgeRuntime(settings)
    try:
        http = await start_http_server(settings, owner)
    except OSError as exc:
        if not is_addr_in_use(exc):
            raise
        log.info(
            "Port %s:%s is busy; this MCP process will proxy to the existing bridge.",
            settings.bridge_host,
            settings.bridge_port,
        )
        _state = AppState(settings=settings, runtime=None, http=None, client_mode=True)
        try:
            yield _state
        finally:
            _state = None
        return

    runtime = owner
    try:
        await runtime.start()
        _state = AppState(settings=settings, runtime=runtime, http=http, client_mode=False)
        yield _state
    finally:
        await stop_http_server(http)
        await runtime.stop()
        _state = None


mcp = FastMCP(
    "telegram-bridge",
    instructions=(
        "Human-in-the-loop via Telegram. "
        "Call ask_user_telegram when you need the operator to choose or confirm. "
        "Call notify_user_telegram for status that should not block. "
        "Do not invent Telegram replies."
    ),
    lifespan=_lifespan,
)


async def _ask_via_http(settings: Settings, question: str, options: list[str]) -> str:
    try:
        result = await asyncio.to_thread(
            bridge_request,
            settings,
            "POST",
            "/v1/ask",
            {"question": question, "options": options},
            settings.ask_timeout_sec + 30,
        )
    except BridgeUnavailable:
        return "NO_REPLY: Telegram bridge HTTP is not reachable."
    return str(result.get("answer") or _NO_REPLY)


@mcp.tool()
async def ask_user_telegram(question: str, options: list[str] | None = None) -> str:
    """Ask the human operator in Telegram and wait for a button or a text reply.

    Use this for architecture choices, confirmations, and questions you must not guess.
    `options` become inline buttons. The operator may also reply with free text.
    """
    state = get_state()
    option_list = [item.strip() for item in (options or []) if item and item.strip()]
    if state.client_mode:
        return await _ask_via_http(state.settings, question, option_list)
    assert state.runtime is not None
    try:
        return await state.runtime.ask(question, option_list or None)
    except AskTimeout:
        return _NO_REPLY


@mcp.tool()
async def notify_user_telegram(message: str) -> str:
    """Send a status message to Telegram without waiting for a reply."""
    state = get_state()
    if state.client_mode:
        try:
            await asyncio.to_thread(
                bridge_request,
                state.settings,
                "POST",
                "/v1/notify",
                {"message": message},
                30,
            )
        except BridgeUnavailable:
            return "bridge-unreachable"
        return "sent"
    assert state.runtime is not None
    await state.runtime.notify(message)
    return "sent"


def run_mcp() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )
    mcp.run(transport="stdio")
