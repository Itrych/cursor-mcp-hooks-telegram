# Changelog

[Русская версия](CHANGELOG.md)

This file follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [SemVer](https://semver.org/).

## [0.1.0] — 2026-09-17

Initial release.

### Added

- stdio MCP server `telegram-bridge` with `ask_user_telegram` and `notify_user_telegram`.
- Telegram Bot API long polling, inline buttons, and free-text replies.
- Loopback HTTP for hooks: shell confirmation, `stop` notification, ask/notify proxy.
- `beforeShellExecution` hook (dangerous commands only) and `stop` hook.
- Cursor user-profile install: `python -m telegram_bridge install-user`.
- Client mode when the HTTP port is already taken by another bridge process.
- Tests that do not need a live Telegram session: dangerous-command filter and hook stdin.

### Security

- Replies are limited to the allowed `chat_id`.
- Secrets stay in `.env`; `.env.example` is the template.
- The bridge HTTP server listens on `127.0.0.1` and checks `BRIDGE_API_TOKEN`.
