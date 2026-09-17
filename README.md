# cursor-mcp-hooks-telegram

Мост между агентом Cursor и Telegram: содержательные вопросы человеку через MCP и автоматическое подтверждение опасных команд через хуки Cursor.

[English version](README.en.md)

## Зачем это нужно

Агент в Cursor умеет работать, пока вы не сидите за компьютером. Этот проект даёт два канала связи с телефоном:

| Канал | Кто инициирует | Назначение |
| --- | --- | --- |
| MCP `ask_user_telegram` | агент | выбор архитектуры, уточнение требования, подтверждение |
| MCP `notify_user_telegram` | агент | статус без ожидания ответа |
| Hook `beforeShellExecution` | Cursor | Allow / Deny для опасной shell-команды |
| Hook `stop` | Cursor | уведомление, что задача агента завершена |

Правила Cursor только подсказывают вызвать MCP. Запрет опасного shell обеспечивает хук.

## Как это устроено

```text
Cursor Agent
  |  MCP stdio: ask_user / notify_user
  v
telegram-bridge (один процесс Python)
  |-- Telegram Bot API (getUpdates + sendMessage)
  |-- HTTP 127.0.0.1  <--- хуки Cursor (короткие процессы)
  v
Telegram → кнопки или текст
```

Один процесс владеет `getUpdates`. Хуки не ходят в Telegram напрямую: они спрашивают локальный HTTP-мост. Если порт моста уже занят, второй MCP-процесс работает клиентом первого и не запускает повторный polling.

## Требования

- Windows, Python 3.11+ (`python`, не `python3`)
- Cursor с поддержкой MCP и project/user hooks
- Telegram-бот и числовой `chat_id` личного чата

## Установка

Клонируйте репозиторий, создайте виртуальное окружение и поставьте зависимость:

```text
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Скопируйте `.env.example` в `.env` и заполните:

| Переменная | Назначение |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | токен бота от BotFather |
| `TELEGRAM_CHAT_ID` | числовой id чата, куда слать сообщения |
| `BRIDGE_HOST` | только loopback, по умолчанию `127.0.0.1` |
| `BRIDGE_PORT` | порт HTTP для хуков, по умолчанию `8765` |
| `BRIDGE_API_TOKEN` | случайная строка для локального HTTP |
| `ASK_TIMEOUT_SEC` | ожидание ответа человека, по умолчанию `900` |

Файл `.env` в git не входит.

Создайте бота через [BotFather](https://t.me/BotFather), откройте его и нажмите Start. `chat_id` можно взять из `getUpdates` после `/start` или у [@userinfobot](https://t.me/userinfobot).

Проверка доставки без Cursor:

```text
.venv\Scripts\python.exe -m telegram_bridge notify "проверка"
.venv\Scripts\python.exe -m telegram_bridge ask "Выбери вариант" --options A B
```

Подключение ко всем проектам Cursor на этой машине:

```text
.venv\Scripts\python.exe -m telegram_bridge install-user
```

Команда обновляет пользовательские файлы:

- `%USERPROFILE%\.cursor\mcp.json`
- `%USERPROFILE%\.cursor\hooks.json`
- `%USERPROFILE%\.cursor\rules\telegram-hitl.mdc`

Затем Reload Window. В Settings → MCP сервер `telegram-bridge` должен быть включён. В Settings → Hooks видны user-level хуки.

Не кладите копию MCP-сервера ещё и в `.cursor/mcp.json` проекта: Cursor поднимет два процесса и они столкнутся на порту `8765`. Шаблон для справки: `.cursor/mcp.json.example`.

## Инструменты MCP

### `ask_user_telegram(question, options?)`

Задаёт вопрос в Telegram. `options` становятся inline-кнопками. Человек может ответить кнопкой или текстом. Пока вопрос висит, MCP-вызов ждёт. Если ответа нет до таймаута, агент получает строку `NO_REPLY` и не должен выдумывать выбор.

### `notify_user_telegram(message)`

Отправляет статус и сразу возвращает `sent`.

Правило `.cursor/rules/telegram-hitl.mdc` подсказывает агенту, когда звать эти инструменты. Это не принуждение: при необходимости напишите явно «спроси в Telegram».

## Хуки

Скрипты лежат в `.cursor/hooks/`. После `install-user` Cursor вызывает их по абсолютному пути из профиля пользователя.

- `beforeShellExecution` пропускает обычные команды. Опасные (удаление деревьев файлов, `git push --force`, `irm \| iex`, format диска и подобные) уходят в Telegram как Разрешить / Запретить. Если мост не запущен, такая команда блокируется.
- `stop` шлёт «Агент закончил выполнение задачи» и не возвращает `followup_message`, чтобы Cursor не перезапускал агента сам.

Список опасных шаблонов: `telegram_bridge/danger.py`.

## CLI

```text
python -m telegram_bridge                 # MCP stdio (так стартует Cursor)
python -m telegram_bridge notify TEXT
python -m telegram_bridge ask "Вопрос" --options A B
python -m telegram_bridge install-user
```

Не запускайте CLI `ask` параллельно с MCP Cursor: у Telegram только один потребитель `getUpdates`.

## Безопасность

- Токен бота и `chat_id` только в локальном `.env`.
- Бот отвечает лишь указанному чату.
- Локальный HTTP слушает loopback и проверяет `BRIDGE_API_TOKEN`.
- Хуки читают JSON хука как UTF-8 bytes; в stdout отдают ASCII JSON.

Сообщить об уязвимости: [SECURITY.md](SECURITY.md).

## Документация

- [Участие в разработке](CONTRIBUTING.md)
- [Политика безопасности](SECURITY.md)
- [История изменений](CHANGELOG.md)
- [Лицензия MIT](LICENSE)

## Лицензия

Проект распространяется на условиях [MIT License](LICENSE).
