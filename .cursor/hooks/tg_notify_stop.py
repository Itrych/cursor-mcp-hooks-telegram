from __future__ import annotations

import json
import os
import sys
from pathlib import Path

def _bridge_root() -> Path:
    env = os.environ.get("TELEGRAM_BRIDGE_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def _read_input() -> dict:
    raw_bytes = sys.stdin.buffer.read()
    raw = raw_bytes.decode("utf-8-sig", errors="replace").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    payload = _read_input()
    status = str(payload.get("status") or "completed")
    root = _bridge_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from telegram_bridge.config import load_settings
        from telegram_bridge.hook_client import bridge_request

        settings = load_settings()
        bridge_request(
            settings,
            "POST",
            "/v1/notify-stop",
            {"status": status},
            timeout_sec=20,
        )
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
