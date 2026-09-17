from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from telegram_bridge.config import load_settings
from telegram_bridge.exceptions import AskTimeout, BridgeError
from telegram_bridge.runtime import BridgeRuntime


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m telegram_bridge",
        description="Telegram HITL bridge. No args starts the MCP stdio server.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    notify = sub.add_parser("notify", help="Send a status message and exit.")
    notify.add_argument("message")

    ask = sub.add_parser("ask", help="Ask a question and wait for a Telegram reply.")
    ask.add_argument("question")
    ask.add_argument(
        "--options",
        nargs="*",
        default=[],
        help="Inline button labels. Omit to wait for free text only.",
    )
    ask.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Override ASK_TIMEOUT_SEC for this question.",
    )
    sub.add_parser("serve", help="Run the MCP stdio server (default).")
    sub.add_parser(
        "install-user",
        help="Install MCP, hooks, and the HITL rule into ~/.cursor for all projects.",
    )
    return parser


async def _run_notify(message: str) -> int:
    runtime = BridgeRuntime(load_settings())
    await runtime.notify(message)
    print("sent")
    return 0


async def _run_ask(question: str, options: list[str], timeout: int | None) -> int:
    runtime = BridgeRuntime(load_settings())
    await runtime.start()
    try:
        answer = await runtime.ask(question, options, timeout_sec=timeout)
        print(answer)
        return 0
    except AskTimeout as exc:
        print(str(exc), file=sys.stderr)
        return 2
    finally:
        await runtime.stop()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1] in {"serve", "mcp"}):
        from telegram_bridge.mcp_server import run_mcp

        run_mcp()
        return

    args = _build_parser().parse_args()
    try:
        if args.command == "serve":
            from telegram_bridge.mcp_server import run_mcp

            run_mcp()
            return
        if args.command == "install-user":
            from telegram_bridge.install_user import main as install_main

            raise SystemExit(install_main())
        if args.command == "notify":
            raise SystemExit(asyncio.run(_run_notify(args.message)))
        raise SystemExit(asyncio.run(_run_ask(args.question, args.options, args.timeout)))
    except BridgeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
