from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

def _bridge_root() -> Path:
    env = os.environ.get("TELEGRAM_BRIDGE_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def _debug(message: str) -> None:
    if os.environ.get("TG_HOOK_DEBUG") != "1":
        return
    try:
        Path(__file__).resolve().parent.joinpath("last-hook.log").write_text(
            message, encoding="utf-8"
        )
    except Exception:
        pass


def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=True))
    sys.stdout.flush()


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
    command = str(payload.get("command") or "")
    cwd = str(payload.get("cwd") or "")
    _debug(f"command={command!r}\ncwd={cwd!r}")

    root = _bridge_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from telegram_bridge.danger import is_dangerous_command
    from telegram_bridge.config import load_settings
    from telegram_bridge.hook_client import BridgeUnavailable, bridge_request

    if not is_dangerous_command(command):
        _emit({"permission": "allow"})
        return 0

    settings = load_settings()
    timeout = settings.ask_timeout_sec + 30
    try:
        result = bridge_request(
            settings,
            "POST",
            "/v1/shell-confirm",
            {"command": command, "cwd": cwd},
            timeout_sec=timeout,
        )
    except BridgeUnavailable:
        _emit(
            {
                "permission": "deny",
                "agent_message": "Telegram bridge is not running. Dangerous command blocked.",
                "user_message": "Мост Telegram не запущен — опасная команда заблокирована.",
            }
        )
        return 0

    permission = result.get("permission", "deny")
    if permission == "allow":
        _emit({"permission": "allow"})
        return 0
    out = {
        "permission": "deny",
        "agent_message": result.get(
            "agent_message",
            "User denied the command via Telegram.",
        ),
    }
    if result.get("user_message"):
        out["user_message"] = result["user_message"]
    _emit(out)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        _debug(traceback.format_exc())
        _emit(
            {
                "permission": "deny",
                "agent_message": "Shell gate crashed. Command blocked.",
            }
        )
        raise SystemExit(0)
