from __future__ import annotations

import re

# Match the full agent command string. Keep this conservative: a hit means
# Telegram must confirm. A miss still goes through Cursor's own GUI approval.
_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE | re.DOTALL)
    for pattern in (
        r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f\b",
        r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r\b",
        r"\bdel\s+/[sS]\b",
        r"\brmdir\s+/[sS]\b",
        r"\berd\s+/[sS]\b",
        r"\bRemove-Item\b.{0,240}-(Recurse|Force)\b",
        r"\bClear-Disk\b",
        r"\bInitialize-Disk\b",
        r"\bformat\s+[a-zA-Z]:",
        r"\bdiskpart\b",
        r"\bmkfs(\.\w+)?\b",
        r"\bdd\s+if=",
        r"\bcipher\s+/w",
        r"\bgit\s+push\b.{0,160}(\s--force\b|\s-f\b)",
        r"\bshutdown\b",
        r"\bStop-Computer\b",
        r"\bRestart-Computer\b",
        r"\bRemove-Computer\b",
        r"\bbcdedit\b",
        r"\breg\s+delete\b",
        r"\bnet\s+user\b",
        r"\bnet\s+localgroup\b",
        r"\bSet-ExecutionPolicy\b",
        r"\bInvoke-Expression\b",
        r"\biex\b",
        r"\bDownloadString\b",
        r"\b(irm|Invoke-RestMethod|Invoke-WebRequest)\b.{0,200}\|\s*(iex|Invoke-Expression)\b",
        r"\b(curl|wget)\b.{0,200}\|\s*(sh|bash|zsh|powershell|pwsh|python|py|cmd)\b",
        r"\bsc\s+(delete|config)\b",
        r"\bschtasks\s+/create\b",
        r"\btakeown\b",
        r"\bicacls\b.{0,200}\bEveryone\b",
        r"\bDrop\s+Database\b",
    )
)


def is_dangerous_command(command: str) -> bool:
    text = (command or "").strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in _PATTERNS)
