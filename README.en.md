# cursor-mcp-hooks-telegram

A bridge between the Cursor agent and Telegram: human-in-the-loop questions through MCP, and automatic confirmation of dangerous shell commands through Cursor hooks.

[Русская версия](README.md)

## Purpose

The Cursor agent can keep working while you are away from the keyboard. This project adds two phone channels:

| Channel | Initiated by | Purpose |
| --- | --- | --- |
| MCP `ask_user_telegram` | agent | architecture choice, requirement, confirmation |
| MCP `notify_user_telegram` | agent | status without waiting |
| Hook `beforeShellExecution` | Cursor | Allow / Deny for a dangerous shell command |
| Hook `stop` | Cursor | notification that the agent task finished |

Cursor rules only steer the agent toward MCP. The hook is what actually blocks a dangerous shell command.

## Architecture

```text
Cursor Agent
  |  MCP stdio: ask_user / notify_user
  v
telegram-bridge (one Python process)
  |-- Telegram Bot API (getUpdates + sendMessage)
  |-- HTTP 127.0.0.1  <--- Cursor hooks (short-lived processes)
  v
Telegram → buttons or text
```

A single process owns `getUpdates`. Hooks never call Telegram themselves; they query the local HTTP bridge. If the bridge port is already taken, a second MCP process becomes a client of the first one and does not start another polling loop.

## Requirements

- Windows, Python 3.11+ (`python`, not `python3`)
- Cursor with MCP and project/user hooks
- A Telegram bot and the numeric `chat_id` of your private chat

## Install

Clone the repository, create a virtual environment, and install the dependency:

```text
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in:

| Variable | Purpose |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | bot token from BotFather |
| `TELEGRAM_CHAT_ID` | numeric chat id for outbound messages |
| `BRIDGE_HOST` | loopback only, default `127.0.0.1` |
| `BRIDGE_PORT` | HTTP port for hooks, default `8765` |
| `BRIDGE_API_TOKEN` | random string for local HTTP auth |
| `ASK_TIMEOUT_SEC` | how long to wait for a human, default `900` |

`.env` is not tracked by git.

Create a bot with [BotFather](https://t.me/BotFather), open it, and press Start. You can read `chat_id` from `getUpdates` after `/start`, or from [@userinfobot](https://t.me/userinfobot).

Smoke test without Cursor:

```text
.venv\Scripts\python.exe -m telegram_bridge notify "probe"
.venv\Scripts\python.exe -m telegram_bridge ask "Pick one" --options A B
```

Attach the bridge to every Cursor project on this machine:

```text
.venv\Scripts\python.exe -m telegram_bridge install-user
```

That command updates:

- `%USERPROFILE%\.cursor\mcp.json`
- `%USERPROFILE%\.cursor\hooks.json`
- `%USERPROFILE%\.cursor\rules\telegram-hitl.mdc`

Then reload the window. In Settings → MCP enable `telegram-bridge`. In Settings → Hooks you should see the user-level hooks.

Do not also add the same MCP server to a project's `.cursor/mcp.json`: Cursor would start two processes and they would collide on port `8765`. A reference template lives at `.cursor/mcp.json.example`.

## Auto-review and the MCP allowlist

If the chat shows a Skip / Run card, the MCP call has not reached Telegram yet. Press Run.

To skip that prompt: Settings → Agents → Approvals & Execution → allowlist. The entry format is `server:tool` (the `mcp.json` server name and the tool name):

- `telegram-bridge:*` — both tools
- or separately: `telegram-bridge:ask_user_telegram` and `telegram-bridge:notify_user_telegram`

Do not enter `telegram-bridge` or `notify_user_telegram` alone: Cursor drops those strings.

Alternatively, create `%USERPROFILE%\.cursor\permissions.json`:

```json
{
  "mcpAllowlist": [
    "telegram-bridge:*"
  ]
}
```

This is the Cursor Desktop format, not the CLI `Mcp(...)` form. If the file sets `mcpAllowlist`, it fully replaces the IDE allowlist for MCP.

## MCP tools

### `ask_user_telegram(question, options?)`

Sends a question to Telegram. `options` become inline buttons. The operator may answer with a button or with free text. The MCP call blocks until a reply arrives. On timeout the agent receives `NO_REPLY` and must not invent a choice.

### `notify_user_telegram(message)`

Sends a status message and returns `sent`.

The rule `.cursor/rules/telegram-hitl.mdc` tells the agent when to call these tools. It is guidance, not enforcement. If you need a Telegram prompt, ask for it explicitly.

## Hooks

Scripts live in `.cursor/hooks/`. After `install-user`, Cursor invokes them by absolute path from the user profile.

- `beforeShellExecution` allows ordinary commands. Dangerous ones (recursive deletes, `git push --force`, `irm \| iex`, disk format, and similar) go to Telegram as Allow / Deny. If the bridge is down, those commands are denied.
- `stop` sends “the agent finished the task” and does not return `followup_message`, so Cursor will not auto-continue the agent.

Dangerous-command patterns: `telegram_bridge/danger.py`.

## CLI

```text
python -m telegram_bridge                 # MCP stdio (how Cursor launches it)
python -m telegram_bridge notify TEXT
python -m telegram_bridge ask "Question" --options A B
python -m telegram_bridge install-user
```

Do not run CLI `ask` in parallel with the Cursor MCP process: Telegram allows only one `getUpdates` consumer.

## Security

- Keep the bot token and `chat_id` in the local `.env` file only.
- The bot answers a single allowed chat.
- Local HTTP listens on loopback and checks `BRIDGE_API_TOKEN`.
- Hooks read stdin as UTF-8 bytes and write ASCII JSON to stdout.

To report a vulnerability, see [SECURITY.en.md](SECURITY.en.md).

## Documentation

- [Contributing](CONTRIBUTING.en.md)
- [Security policy](SECURITY.en.md)
- [Changelog](CHANGELOG.en.md)
- [MIT License](LICENSE)

## License

This project is released under the [MIT License](LICENSE).
