from __future__ import annotations

import os
from pathlib import Path

from telegram_bridge.config import REPO_ROOT


def bridge_root() -> Path:
    env = os.environ.get("TELEGRAM_BRIDGE_ROOT")
    if env:
        return Path(env)
    return REPO_ROOT
