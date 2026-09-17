from __future__ import annotations

import asyncio
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
            result = await session.call_tool(
                "notify_user_telegram",
                {"message": "MCP-инструмент notify_user_telegram работает."},
            )
            print(result.content)
    print("notify-tool-ok")


if __name__ == "__main__":
    asyncio.run(main())
