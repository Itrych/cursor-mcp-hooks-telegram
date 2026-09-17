from __future__ import annotations

import asyncio
import errno
import hmac
import json
import logging
from typing import Any
from urllib.parse import unquote

from telegram_bridge.config import Settings
from telegram_bridge.exceptions import AskTimeout
from telegram_bridge.permission import permission_from_answer
from telegram_bridge.runtime import BridgeRuntime

log = logging.getLogger("telegram_bridge.http")

_MAX_BODY = 64 * 1024
_WIN_EADDRINUSE = 10048


def is_addr_in_use(exc: OSError) -> bool:
    if exc.errno in {errno.EADDRINUSE, _WIN_EADDRINUSE}:
        return True
    return getattr(exc, "winerror", None) == _WIN_EADDRINUSE


def _header_map(raw_headers: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in raw_headers:
        name, sep, value = line.partition(":")
        if not sep:
            continue
        headers[name.strip().lower()] = value.strip()
    return headers


def _authorized(headers: dict[str, str], token: str) -> bool:
    if not token:
        return False
    got = headers.get("x-bridge-token", "")
    auth = headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        got = auth[7:].strip()
    try:
        return hmac.compare_digest(got.encode("utf-8"), token.encode("utf-8"))
    except Exception:
        return False


def _http_response(status: str, payload: dict[str, Any], extra_headers: dict[str, str] | None = None) -> bytes:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Length": str(len(body)),
        "Connection": "close",
    }
    if extra_headers:
        headers.update(extra_headers)
    header_block = "".join(f"{key}: {value}\r\n" for key, value in headers.items())
    return f"HTTP/1.1 {status}\r\n{header_block}\r\n".encode("ascii") + body


async def _read_request(
    reader: asyncio.StreamReader,
) -> tuple[str, str, dict[str, str], bytes]:
    header_bytes = await reader.readuntil(b"\r\n\r\n")
    header_text = header_bytes.decode("iso-8859-1")
    lines = header_text.split("\r\n")
    request_line = lines[0]
    parts = request_line.split()
    if len(parts) < 2:
        raise ValueError("Malformed request line.")
    method, path = parts[0].upper(), unquote(parts[1])
    header_lines: list[str] = []
    for line in lines[1:]:
        if line == "":
            break
        header_lines.append(line)
    headers = _header_map(header_lines)
    length = int(headers.get("content-length", "0") or "0")
    if length < 0 or length > _MAX_BODY:
        raise ValueError("Invalid Content-Length.")
    body = b""
    if length:
        body = await reader.readexactly(length)
    return method, path, headers, body


async def _handle_shell_confirm(runtime: BridgeRuntime, payload: dict[str, Any]) -> dict[str, Any]:
    command = str(payload.get("command") or "").strip()
    cwd = str(payload.get("cwd") or "").strip()
    question = (
        "Агент хочет выполнить команду:\n\n"
        f"{command or '(empty)'}\n\n"
        f"Папка: {cwd or '(unknown)'}\n\n"
        "Разрешить?"
    )
    try:
        answer = await runtime.ask(question, ["Разрешить", "Запретить"])
    except AskTimeout:
        return {
            "permission": "deny",
            "agent_message": "Telegram confirmation timed out. The command was blocked.",
        }
    permission = permission_from_answer(answer)
    if permission == "allow":
        return {"permission": "allow"}
    return {
        "permission": "deny",
        "agent_message": "User denied the command via Telegram.",
    }


async def _handle_notify_stop(runtime: BridgeRuntime, payload: dict[str, Any]) -> dict[str, Any]:
    status = str(payload.get("status") or "completed")
    await runtime.notify(f"Агент закончил выполнение задачи.\nstatus: {status}")
    return {"ok": True}


async def _handle_ask(runtime: BridgeRuntime, payload: dict[str, Any]) -> dict[str, Any]:
    question = str(payload.get("question") or "").strip()
    raw_options = payload.get("options") or []
    options = [str(item).strip() for item in raw_options if str(item).strip()]
    try:
        answer = await runtime.ask(question, options or None)
    except AskTimeout:
        return {
            "answer": (
                "NO_REPLY: the user did not answer in Telegram before timeout. "
                "Do not assume a choice. Ask again or continue with a safe default."
            )
        }
    return {"answer": answer}


async def _handle_notify(runtime: BridgeRuntime, payload: dict[str, Any]) -> dict[str, Any]:
    message = str(payload.get("message") or "").strip()
    await runtime.notify(message)
    return {"ok": True, "result": "sent"}


async def handle_connection(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    settings: Settings,
    runtime: BridgeRuntime,
) -> None:
    try:
        method, path, headers, body = await asyncio.wait_for(_read_request(reader), timeout=30)
        path_only = path.split("?", 1)[0]
        if method == "GET" and path_only == "/health":
            writer.write(_http_response("200 OK", {"ok": True}))
            await writer.drain()
            return
        if not _authorized(headers, settings.bridge_api_token):
            writer.write(_http_response("401 Unauthorized", {"error": "unauthorized"}))
            await writer.drain()
            return
        payload: dict[str, Any] = {}
        if body:
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON object expected.")
        if method == "POST" and path_only == "/v1/shell-confirm":
            result = await _handle_shell_confirm(runtime, payload)
            writer.write(_http_response("200 OK", result))
        elif method == "POST" and path_only == "/v1/notify-stop":
            result = await _handle_notify_stop(runtime, payload)
            writer.write(_http_response("200 OK", result))
        elif method == "POST" and path_only == "/v1/ask":
            result = await _handle_ask(runtime, payload)
            writer.write(_http_response("200 OK", result))
        elif method == "POST" and path_only == "/v1/notify":
            result = await _handle_notify(runtime, payload)
            writer.write(_http_response("200 OK", result))
        else:
            writer.write(_http_response("404 Not Found", {"error": "not found"}))
        await writer.drain()
    except Exception:
        log.exception("HTTP request failed")
        try:
            writer.write(_http_response("400 Bad Request", {"error": "bad request"}))
            await writer.drain()
        except Exception:
            pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def start_http_server(settings: Settings, runtime: BridgeRuntime) -> asyncio.AbstractServer:
    async def _on_connect(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await handle_connection(reader, writer, settings, runtime)

    server = await asyncio.start_server(
        _on_connect,
        host=settings.bridge_host,
        port=settings.bridge_port,
    )
    log.info("Hook HTTP listening on %s:%s", settings.bridge_host, settings.bridge_port)
    return server


async def stop_http_server(server: asyncio.AbstractServer | None) -> None:
    if server is None:
        return
    server.close()
    await server.wait_closed()
