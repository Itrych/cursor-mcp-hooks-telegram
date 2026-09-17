# Security policy

[Русская версия](SECURITY.md)

## Supported versions

Security fixes are accepted for current `main` and for the latest `v*` tag.

## What counts as a vulnerability

Please report cases where an attacker can:

- read the bot token or `BRIDGE_API_TOKEN` from logs, tool output, or the repository;
- send a message or press a button from a Telegram account that is not the allowed chat;
- expose the HTTP bridge beyond loopback;
- bypass the hook Allow/Deny gate for a dangerous command.

Ordinary command-filter false positives and human-reply timeouts are not vulnerabilities; file them as regular repository issues.

## How to report

Do not open a public issue with a PoC or secrets.

1. In GitHub: Security → Advisories (private report) for this repository.
2. If that tab is unavailable, contact the repository owner through GitHub without putting tokens in the message.

Include the affected version or commit, steps without real secrets, and expected versus actual behaviour.

## Response

The owner will acknowledge the report and close it after a fix, or after explaining why it is not a vulnerability. Fixes are recorded in [CHANGELOG.en.md](CHANGELOG.en.md).
