"""Browser automation service built on Playwright.

Manages browser lifecycle, page creation, screenshots, and cleanup.
Anti-fingerprinting: launches with real Chrome, sets locale/timezone/
geolocation to match proxy region, and applies stealth patches.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = Path("data/screenshots")

STEALTH_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-sync",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-hang-monitor",
    "--disable-ipc-flooding-protection",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost",
    "--enable-features=NetworkService,NetworkServiceInProcess",
    "--password-store=basic",
    "--use-mock-keychain",
    "--metrics-recording-only",
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
        self.user_agent = user_agent
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
        self._using_system_chrome = False
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
            self._using_system_chrome = True
            logger.info("Browser started with system Chrome (headless=%s, proxy=%s)",
                        self._config.headless, bool(self._config.proxy))
        except Exception:
            logger.warning("System Chrome not found, trying Edge")
            try:
                self._browser = await self._playwright.chromium.launch(
                    channel="msedge", **launch_opts
                )
                self._using_system_chrome = True
                logger.info("Browser started with Edge (headless=%s)", self._config.headless)
            except Exception:
                launch_opts["args"].append("--no-sandbox")
                self._browser = await self._playwright.chromium.launch(**launch_opts)
                self._using_system_chrome = False
                logger.warning("Using bundled Chromium — sites may detect automation")

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
            "screen": {
                "width": self._config.viewport_width,
                "height": self._config.viewport_height,
            },
            "device_scale_factor": 1,
            "is_mobile": False,
            "has_touch": False,
            "extra_http_headers": {
                "Accept-Language": f"{self._config.locale},en;q=0.9",
            },
        }

        # Only override UA when NOT using system Chrome — real Chrome's own UA
        # matches its internals; a fake one creates detectable mismatches
        if self._config.user_agent and not self._using_system_chrome:
            context_opts["user_agent"] = self._config.user_agent

        context = await self._browser.new_context(**context_opts)
        context.set_default_timeout(self._config.timeout_ms)

        lang = self._config.locale
        lang_base = lang.split("-")[0]
        await context.add_init_script(f"""
            // webdriver: real Chrome returns false, not undefined
            Object.defineProperty(navigator, 'webdriver', {{get: () => false}});

            Object.defineProperty(navigator, 'languages', {{get: () => ['{lang}', '{lang_base}']}});
            Object.defineProperty(navigator, 'platform', {{get: () => 'Win32'}});
            Object.defineProperty(navigator, 'hardwareConcurrency', {{get: () => 8}});
            Object.defineProperty(navigator, 'deviceMemory', {{get: () => 8}});
            Object.defineProperty(navigator, 'maxTouchPoints', {{get: () => 0}});
            Object.defineProperty(navigator, 'vendor', {{get: () => 'Google Inc.'}});

            // navigator.connection (missing in headless = detection vector)
            if (!navigator.connection) {{
                Object.defineProperty(navigator, 'connection', {{get: () => ({{
                    effectiveType: '4g',
                    rtt: 50,
                    downlink: 10,
                    saveData: false,
                    onchange: null,
                    addEventListener: function(){{}},
                    removeEventListener: function(){{}},
                    dispatchEvent: function(){{return true}}
                }})}});
            }}

            // window.chrome — must exist and look real
            if (!window.chrome) {{
                window.chrome = {{}};
            }}
            window.chrome.runtime = window.chrome.runtime || {{
                id: undefined,
                connect: function(){{}},
                sendMessage: function(){{}},
                onMessage: {{addListener: function(){{}}, removeListener: function(){{}}}},
                onConnect: {{addListener: function(){{}}, removeListener: function(){{}}}}
            }};
            window.chrome.loadTimes = window.chrome.loadTimes || function(){{return {{}}}};
            window.chrome.csi = window.chrome.csi || function(){{return {{}}}};
            window.chrome.app = window.chrome.app || {{
                isInstalled: false,
                InstallState: {{"DISABLED":"disabled","INSTALLED":"installed","NOT_INSTALLED":"not_installed"}},
                RunningState: {{"CANNOT_RUN":"cannot_run","READY_TO_RUN":"ready_to_run","RUNNING":"running"}}
            }};

            // Permissions API — match real Chrome behavior
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({{state: Notification.permission}}) :
                originalQuery(parameters)
            );

            // Plugins — only spoof if empty (real Chrome already has them)
            if (navigator.plugins.length === 0) {{
                Object.defineProperty(navigator, 'plugins', {{get: () => {{
                    const plugins = [
                        {{name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format', length: 1, item: function(i){{return this}}, namedItem: function(n){{return this}}}},
                        {{name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '', length: 1, item: function(i){{return this}}, namedItem: function(n){{return this}}}},
                        {{name: 'Native Client', filename: 'internal-nacl-plugin', description: '', length: 1, item: function(i){{return this}}, namedItem: function(n){{return this}}}}
                    ];
                    plugins.length = 3;
                    plugins.item = function(i){{return plugins[i]}};
                    plugins.namedItem = function(n){{return plugins.find(p => p.name === n)}};
                    plugins.refresh = function(){{}};
                    return plugins;
                }}}});

                Object.defineProperty(navigator, 'mimeTypes', {{get: () => {{
                    const mimes = [
                        {{type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: navigator.plugins[0]}},
                        {{type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: navigator.plugins[1]}}
                    ];
                    mimes.length = 2;
                    mimes.item = function(i){{return mimes[i]}};
                    mimes.namedItem = function(n){{return mimes.find(m => m.type === n)}};
                    return mimes;
                }}}});
            }}

            // WebGL vendor/renderer — only spoof if on bundled Chromium
            if (!{str(self._using_system_chrome).lower()}) {{
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(param) {{
                    if (param === 37445) return 'Google Inc. (NVIDIA)';
                    if (param === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)';
                    return getParameter.call(this, param);
                }};
                if (typeof WebGL2RenderingContext !== 'undefined') {{
                    const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
                    WebGL2RenderingContext.prototype.getParameter = function(param) {{
                        if (param === 37445) return 'Google Inc. (NVIDIA)';
                        if (param === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)';
                        return getParameter2.call(this, param);
                    }};
                }}
            }}

            // Prevent iframe contentWindow detection
            const originalAttachShadow = Element.prototype.attachShadow;
            Element.prototype.attachShadow = function(init) {{
                return originalAttachShadow.call(this, init);
            }};

            // Media devices — headless often has none
            if (navigator.mediaDevices && !navigator.mediaDevices.enumerateDevices.__original) {{
                const origEnum = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
                navigator.mediaDevices.enumerateDevices = async function() {{
                    const devices = await origEnum();
                    if (devices.length === 0) {{
                        return [
                            {{deviceId: 'default', kind: 'audioinput', label: '', groupId: 'default'}},
                            {{deviceId: 'default', kind: 'videoinput', label: '', groupId: 'default'}},
                            {{deviceId: 'default', kind: 'audiooutput', label: '', groupId: 'default'}}
                        ];
                    }}
                    return devices;
                }};
                navigator.mediaDevices.enumerateDevices.__original = true;
            }}

            // Battery API — headless may not have it
            if (!navigator.getBattery) {{
                navigator.getBattery = async function() {{
                    return {{
                        charging: true, chargingTime: 0, dischargingTime: Infinity, level: 1,
                        addEventListener: function(){{}}, removeEventListener: function(){{}},
                        dispatchEvent: function(){{return true}}, onchargingchange: null,
                        onchargingtimechange: null, ondischargingtimechange: null, onlevelchange: null
                    }};
                }};
            }}
        """)

        page = await context.new_page()

        try:
            from playwright_stealth import Stealth
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
            logger.debug("Stealth plugin applied")
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
            "system_chrome": self._using_system_chrome,
        }
