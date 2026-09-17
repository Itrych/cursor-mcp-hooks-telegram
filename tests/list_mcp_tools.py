from __future__ import annotations

import asyncio
import json
import urllib.request
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
PY = ROOT / ".venv" / "Scripts" / "python.exe"


async def main() -> None:
    params = StdioServerParameters(
        command=str(PY),
        args=["-m", "telegram_bridge"],
        cwd=str(ROOT),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = sorted(item.name for item in tools.tools)
            print("tools", names)
            if names != ["ask_user_telegram", "notify_user_telegram"]:
                raise SystemExit(f"unexpected tools: {names}")
            with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            print("health", payload)
            if payload.get("ok") is not True:
                raise SystemExit("health check failed")
    print("mcp-ok")


if __name__ == "__main__":
    asyncio.run(main())
