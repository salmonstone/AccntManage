"""Browser automation service built on Playwright.

Manages browser lifecycle, page creation, screenshots, and cleanup.
Anti-fingerprinting: launches with real Chrome args, sets locale/timezone/
geolocation to match proxy region, and applies stealth patches.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = Path("data/screenshots")

CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)

STEALTH_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--no-first-run",
    "--no-default-browser-check",
    "--start-maximized",
]


class BrowserConfig:
    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = 30_000,
        proxy: dict[str, str] | None = None,
        user_agent: str | None = None,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        locale: str = "en-US",
        timezone_id: str = "America/New_York",
        color_scheme: str = "dark",
    ) -> None:
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.proxy = proxy
        self.user_agent = user_agent or CHROME_USER_AGENT
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.locale = locale
        self.timezone_id = timezone_id
        self.color_scheme = color_scheme


class BrowserService:
    def __init__(self, config: BrowserConfig | None = None) -> None:
        self._config = config or BrowserConfig()
        self._playwright: Any = None
        self._browser: Any = None
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        launch_opts: dict[str, Any] = {
            "headless": self._config.headless,
            "args": STEALTH_LAUNCH_ARGS.copy(),
        }
        if self._config.proxy:
            launch_opts["proxy"] = self._config.proxy

        try:
            self._browser = await self._playwright.chromium.launch(
                channel="chrome", **launch_opts
            )
            logger.info("Browser started with system Chrome (headless=%s)", self._config.headless)
        except Exception:
            logger.info("System Chrome not found, falling back to bundled Chromium")
            self._browser = await self._playwright.chromium.launch(**launch_opts)
            logger.info("Browser started with Chromium (headless=%s)", self._config.headless)

    async def new_page(self) -> Any:
        if not self._browser:
            await self.start()

        context_opts: dict[str, Any] = {
            "viewport": {
                "width": self._config.viewport_width,
                "height": self._config.viewport_height,
            },
            "locale": self._config.locale,
            "timezone_id": self._config.timezone_id,
            "color_scheme": self._config.color_scheme,
        }

        context = await self._browser.new_context(**context_opts)
        context.set_default_timeout(self._config.timeout_ms)

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        page = await context.new_page()

        try:
            from playwright_stealth import Stealth
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
            logger.info("Stealth plugin applied to page")
        except ImportError:
            logger.debug("playwright-stealth not installed, using built-in stealth only")
        except Exception as e:
            logger.warning("Failed to apply stealth plugin: %s", e)

        return page

    async def take_screenshot(self, page: Any, label: str = "screenshot") -> str:
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
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
