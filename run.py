"""Launch script that ensures ProactorEventLoop on Windows.

Uvicorn ignores asyncio.set_event_loop_policy() and creates its own loop,
which on Python 3.14/Windows lacks subprocess support (needed by Playwright).
This script creates a ProactorEventLoop explicitly and runs uvicorn inside it.
"""
import asyncio
import sys

import uvicorn


def main():
    config = uvicorn.Config(
        "backend.app.main:app",
        host="127.0.0.1",
        port=8765,
    )
    server = uvicorn.Server(config)

    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.serve())
    else:
        asyncio.run(server.serve())


if __name__ == "__main__":
    main()
