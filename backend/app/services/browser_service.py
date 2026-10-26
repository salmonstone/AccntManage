"""Browser automation service built on Playwright.

Manages browser lifecycle, page creation, screenshots, and cleanup.
Used by workflow steps that require browser interaction.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = Path("data/screenshots")


class BrowserConfig:
    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = 30_000,
        proxy: dict[str, str] | None = None,
        user_agent: str | None = None,
        viewport_width: int = 1280,
        viewport_height: int = 720,
    ) -> None:
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.proxy = proxy
        self.user_agent = user_agent
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height


class BrowserService:
    def __init__(self, config: BrowserConfig | None = None) -> None:
        self._config = config or BrowserConfig()
        self._playwright = None
        self._browser = None
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        launch_opts: dict[str, Any] = {
            "headless": self._config.headless,
        }
        if self._config.proxy:
            launch_opts["proxy"] = self._config.proxy

        self._browser = await self._playwright.chromium.launch(**launch_opts)
        logger.info("Browser started (headless=%s)", self._config.headless)

    async def new_page(self) -> Any:
        if not self._browser:
            await self.start()

        context_opts: dict[str, Any] = {
            "viewport": {
                "width": self._config.viewport_width,
                "height": self._config.viewport_height,
            },
        }
        if self._config.user_agent:
            context_opts["user_agent"] = self._config.user_agent

        context = await self._browser.new_context(**context_opts)
        context.set_default_timeout(self._config.timeout_ms)
        page = await context.new_page()
        return page

    async def take_screenshot(self, page: Any, label: str = "screenshot") -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
        filename = f"{safe_label}_{ts}.png"
        path = SCREENSHOTS_DIR / filename
        await page.screenshot(path=str(path))
        logger.debug("Screenshot saved: %s", filename)
        return str(path)

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Browser stopped")

    @property
    def is_running(self) -> bool:
        return self._browser is not None

    def get_diagnostics(self) -> dict[str, Any]:
        return {
            "running": self.is_running,
            "headless": self._config.headless,
            "timeout_ms": self._config.timeout_ms,
            "has_proxy": self._config.proxy is not None,
        }
