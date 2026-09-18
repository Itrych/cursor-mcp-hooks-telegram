# История изменений

[English version](CHANGELOG.en.md)

Формат близок к [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/). Версии следуют [SemVer](https://semver.org/lang/ru/).

## [0.1.1] — 2026-09-18

### Изменено

- В README описан allowlist Auto-review для Desktop: `telegram-bridge:*`, а не имя сервера или инструмента по отдельности.

## [0.1.0] — 2026-09-17

Первый выпуск.

### Добавлено

- MCP-сервер stdio `telegram-bridge` с инструментами `ask_user_telegram` и `notify_user_telegram`.
- Long polling Telegram Bot API, inline-кнопки и ответ свободным текстом.
- Локальный HTTP на loopback для хуков: подтверждение shell, уведомление `stop`, прокси ask/notify.
- Хуки `beforeShellExecution` (только опасные команды) и `stop`.
- Установка в профиль Cursor: `python -m telegram_bridge install-user`.
- Режим клиента, если порт HTTP уже занят другим процессом моста.
- Набор тестов без живого Telegram: фильтр опасных команд и stdin хука.

### Безопасность

- Ответы только в разрешённый `chat_id`.
- Секреты только в `.env`, шаблон — `.env.example`.
- HTTP моста слушает `127.0.0.1` и проверяет `BRIDGE_API_TOKEN`.
