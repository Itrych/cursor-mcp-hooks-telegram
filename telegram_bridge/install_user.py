"""Install telegram-bridge into the user-level Cursor config (~/.cursor)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from telegram_bridge.config import REPO_ROOT

USER_CURSOR = Path.home() / ".cursor"
MCP_PATH = USER_CURSOR / "mcp.json"
HOOKS_PATH = USER_CURSOR / "hooks.json"
RULES_DIR = USER_CURSOR / "rules"
RULE_PATH = RULES_DIR / "telegram-hitl.mdc"

HOOK_MARKER = "tg_shell_gate.py"
STOP_MARKER = "tg_notify_stop.py"
SERVER_NAME = "telegram-bridge"

USER_RULE = """---
description: When to use Telegram MCP tools for human-in-the-loop
alwaysApply: true
---

# Telegram human-in-the-loop

MCP server `telegram-bridge` is available in every workspace:

- `ask_user_telegram(question, options?)` — wait for a Telegram button or text reply
- `notify_user_telegram(message)` — status only, do not wait

Use `ask_user_telegram` when you need a human choice (architecture A vs B, destructive confirm, unclear requirement). Do not guess. Do not call Telegram via curl/shell.

Use `notify_user_telegram` for important progress that the operator should see on the phone.

Do not duplicate shell Allow/Deny through MCP. Dangerous shell is gated by the `beforeShellExecution` hook.

If `ask_user_telegram` returns `NO_REPLY`, do not invent an answer. Continue only with a safe default or stop and say that the operator did not reply.
"""


def _python() -> Path:
    return REPO_ROOT / ".venv" / "Scripts" / "python.exe"


def _hook_script(name: str) -> Path:
    return REPO_ROOT / ".cursor" / "hooks" / name


def _mcp_server_block() -> dict:
    root = str(REPO_ROOT)
    python = str(_python())
    return {
        "command": python,
        "args": ["-m", "telegram_bridge"],
        "env": {
            "PYTHONPATH": root,
            "PYTHONUTF8": "1",
            "TELEGRAM_BRIDGE_ROOT": root,
        },
        "envFile": str(REPO_ROOT / ".env"),
    }


def _hook_command(script_name: str) -> str:
    return f"{_python()} -u {_hook_script(script_name)}"


def _load_json(path: Path, fallback: dict) -> dict:
    if not path.is_file():
        return fallback
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object.")
    return data


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def install_mcp() -> None:
    data = _load_json(MCP_PATH, {"mcpServers": {}})
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError(f"{MCP_PATH} mcpServers must be an object.")
    servers[SERVER_NAME] = _mcp_server_block()
    _write_json(MCP_PATH, data)


def _upsert_hook(entries: list, marker: str, command: str, extra: dict) -> list:
    kept = []
    replaced = False
    for item in entries:
        if isinstance(item, dict) and marker in str(item.get("command", "")):
            kept.append({**item, "command": command, **extra})
            replaced = True
        else:
            kept.append(item)
    if not replaced:
        kept.append({"command": command, **extra})
    return kept


def install_hooks() -> None:
    data = _load_json(HOOKS_PATH, {"version": 1, "hooks": {}})
    data["version"] = 1
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"{HOOKS_PATH} hooks must be an object.")
    shell = list(hooks.get("beforeShellExecution") or [])
    stop = list(hooks.get("stop") or [])
    hooks["beforeShellExecution"] = _upsert_hook(
        shell,
        HOOK_MARKER,
        _hook_command("tg_shell_gate.py"),
        {"timeout": 930, "failClosed": True},
    )
    hooks["stop"] = _upsert_hook(
        stop,
        STOP_MARKER,
        _hook_command("tg_notify_stop.py"),
        {"timeout": 30},
    )
    _write_json(HOOKS_PATH, data)


def install_rule() -> None:
    RULES_DIR.mkdir(parents=True, exist_ok=True)
    RULE_PATH.write_text(USER_RULE, encoding="utf-8")


def main() -> int:
    if not _python().is_file():
        print(f"Missing venv python: {_python()}", file=sys.stderr)
        return 1
    install_mcp()
    install_hooks()
    install_rule()
    print(f"Installed user MCP: {MCP_PATH}")
    print(f"Installed user hooks: {HOOKS_PATH}")
    print(f"Installed user rule: {RULE_PATH}")
    print("Reload Cursor windows (or toggle MCP telegram-bridge) so other projects pick this up.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
