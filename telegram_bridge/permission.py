from __future__ import annotations

_ALLOW = {
    "разрешить",
    "allow",
    "yes",
    "y",
    "да",
    "ок",
    "ok",
}

_DENY = {
    "запретить",
    "deny",
    "no",
    "n",
    "нет",
}


def permission_from_answer(answer: str) -> str:
    """Map a Telegram reply to Cursor hook permission. Unknown text is deny."""
    key = (answer or "").strip().lower()
    if key in _ALLOW:
        return "allow"
    if key in _DENY:
        return "deny"
    return "deny"
