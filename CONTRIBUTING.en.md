# Contributing

[Русская версия](CONTRIBUTING.md)

This repository is private. Changes are made by the owner. This file records how work should be done so the GitHub history stays readable.

## Language

- End-user documents are entirely Russian or entirely English. Do not mix both in one file.
- The landing page is [README.md](README.md) (Russian). The English text is [README.en.md](README.en.md).
- Code comments are English.
- GitHub release notes are Russian.

## What belongs in git

The repository includes `telegram_bridge` sources, hooks, tests, public markdown files, and `.env.example`.

Do not commit:

- `.env`, `.venv`
- internal notes in `_docs` and `_other`
- secrets, tokens, or chat ids

## Environment

Python 3.11+, the `python` command. Dependency: `mcp>=1.28,<2`.

```text
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe tests\run_hook_cases.py
```

Live Telegram calls need a filled `.env`. Never copy the token into chat or git.

## Commits

One commit should carry one finished idea. The message explains why the change exists, not a file list. The commit author is the repository owner, without a Cursor co-author.

After a behaviour change, update [CHANGELOG.en.md](CHANGELOG.en.md) and [CHANGELOG.md](CHANGELOG.md) when needed.

## Releases

Tags use `vX.Y.Z`. Release text is Russian: what landed, what broke, how to upgrade. Details live in [CHANGELOG.md](CHANGELOG.md).
