from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".cursor" / "hooks" / "tg_shell_gate.py"
PY = ROOT / ".venv" / "Scripts" / "python.exe"


def run_hook(payload: dict) -> dict:
    completed = subprocess.run(
        [str(PY), "-u", str(HOOK)],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        cwd=str(ROOT),
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.decode("utf-8", errors="replace"))
    return json.loads(completed.stdout.decode("utf-8"))


def main() -> None:
    safe = run_hook({"command": "echo hello", "cwd": str(ROOT)})
    assert safe.get("permission") == "allow", safe
    dangerous = run_hook({"command": "rm -rf C:\\temp", "cwd": str(ROOT)})
    assert dangerous.get("permission") == "deny", dangerous
    print("hook-ok")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    from tests.test_smoke import main as unit_main

    unit_main()
    main()
