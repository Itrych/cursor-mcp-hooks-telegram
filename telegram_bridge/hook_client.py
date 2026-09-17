from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from telegram_bridge.config import Settings
from telegram_bridge.exceptions import BridgeError


class BridgeUnavailable(BridgeError):
    """Local HTTP bridge is not running."""


def bridge_request(
    settings: Settings,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout_sec: int = 30,
) -> dict[str, Any]:
    url = f"http://{settings.bridge_host}:{settings.bridge_port}{path}"
    body = None
    headers = {
        "X-Bridge-Token": settings.bridge_api_token,
        "Accept": "application/json",
    }
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise BridgeUnavailable(f"bridge HTTP error: {exc.reason}") from exc
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise BridgeError("bridge returned a non-object JSON payload.")
    return data
