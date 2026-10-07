"""In-app Discord login for dctw.xyz.

The official website signs users in with Discord OAuth2 and then shows
their personal API key in the dashboard. This dialog runs the same OAuth
flow inside a WebView, watches the dashboard for the key and stores it,
so users can vote (and load data) right after logging in.

Platforms without WebView support (Windows, Linux and plain web builds)
fall back to opening the login page in the system browser and reading
the key from the clipboard.
"""

import asyncio
import logging
import re
from typing import Callable, Optional
from urllib.parse import quote

import flet as ft

from application.services import DiscoveryService, PreferenceService
from infrastructure.api import DctwApiClient
from infrastructure.config.constants import DCTW_WEBSITE_URL
from presentation.url_helper import open_url

from .api_key_helpers import apply_api_key
from .toast import Toast

try:  # The WebView control ships as an optional Flet extension.
    from flet_webview import WebView
except Exception:  # pragma: no cover - extension not installed
    WebView = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

DISCORD_CLIENT_ID = "1410309371174326364"
DISCORD_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
DCTW_LOGIN_REDIRECT = f"{DCTW_WEBSITE_URL}/login"
DCTW_DASHBOARD_URL = f"{DCTW_WEBSITE_URL}/dashboard/overview"

# Marker the injected JavaScript uses to send the key back to Python.
KEY_MARKER = "DCTWFletApiKey:"
API_KEY_PATTERN = re.compile(r"dctw_[A-Za-z0-9_\-]{8,}")

WEBVIEW_PLATFORMS = (
    ft.PagePlatform.ANDROID,
    ft.PagePlatform.IOS,
    ft.PagePlatform.MACOS,
)

# JavaScript injected into the logged-in dashboard. It scans the page, the
# responses the site loads and anything the site copies to the clipboard,
# then reports the API key through the console (captured by Flet).
CAPTURE_SCRIPT = r"""
(function () {
  if (window.__dctwfletCapture) { return "already"; }
  window.__dctwfletCapture = true;

  var report = function (value) {
    try { console.log("DCTWFletApiKey:" + String(value || "")); } catch (e) {}
  };
  var scan = function (text) {
    var match = String(text || "").match(/dctw_[A-Za-z0-9_\-]{8,}/);
    if (match) { report(match[0]); return true; }
    return false;
  };

  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      var writeText = navigator.clipboard.writeText.bind(navigator.clipboard);
      navigator.clipboard.writeText = function (text) {
        scan(text);
        return writeText(text);
      };
    }
  } catch (e) {}

  try {
    var execCommand = document.execCommand ? document.execCommand.bind(document) : null;
    if (execCommand) {
      document.execCommand = function (command) {
        if (String(command).toLowerCase() === "copy") {
          try { scan(String(window.getSelection())); } catch (e) {}
        }
        return execCommand.apply(null, arguments);
      };
    }
  } catch (e) {}

  try {
    var fetchOriginal = window.fetch;
    if (fetchOriginal) {
      window.fetch = function () {
        var request = fetchOriginal.apply(this, arguments);
        try {
          request.then(function (response) {
            try {
              response.clone().text().then(function (body) { scan(body); }).catch(function () {});
            } catch (e) {}
          }).catch(function () {});
        } catch (e) {}
        return request;
      };
    }
  } catch (e) {}

  scan(document.body ? document.body.innerText : "");

  var attempts = 0;
  var timer = setInterval(function () {
    attempts += 1;
    if (!scan(document.body ? document.body.innerText : "") && attempts === 2) {
      try {
        var nodes = document.querySelectorAll("button, a, [role=button]");
        for (var i = 0; i < nodes.length; i++) {
          var label = String(nodes[i].textContent || "");
          var isCopy = label.indexOf("複製") !== -1 || /copy/i.test(label);
          if (isCopy && /api/i.test(label)) {
            nodes[i].click();
            break;
          }
        }
      } catch (e) {}
    }
    if (attempts >= 20) { clearInterval(timer); }
  }, 1000);

  return "started";
})()
"""


def build_login_url(state: str = DCTW_DASHBOARD_URL) -> str:
    """Build the Discord OAuth2 URL the official website uses to log in."""
    return (
        f"{DISCORD_AUTHORIZE_URL}?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={quote(DCTW_LOGIN_REDIRECT, safe='')}"
        "&response_type=code&scope=identify%20guilds&prompt=consent"
        f"&state={quote(state, safe='')}"
    )


def extract_api_key(text: Optional[str]) -> Optional[str]:
    """Return the first DCTW API key contained in ``text``."""
    match = API_KEY_PATTERN.search(str(text or ""))
    return match.group(0) if match else None


def _host_of(url: str) -> str:
    match = re.match(r"^[a-zA-Z]+://([^/?#]+)", url or "")
    return match.group(1).lower() if match else ""


class DiscordLoginDialog:
    """Sign in with Discord and store the DCTW API key automatically."""

    def __init__(
        self,
        page: ft.Page,
        preference_service: PreferenceService,
        discovery_service: DiscoveryService,
        api_client: DctwApiClient,
        on_saved: Optional[Callable[[], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        reason: Optional[str] = None,
    ):
        self._page = page
        self._preferences = preference_service
        self._discovery = discovery_service
        self._api_client = api_client
        self._on_saved = on_saved
        self._on_close = on_close

        self._dialog: Optional[ft.AlertDialog] = None
        self._webview = None
        self._status = ft.Text(
            reason or "請在下方使用 Discord 登入 DCTW，登入後會自動填入 API Key。",
            size=13,
        )
        self._progress = ft.ProgressRing(
            width=18, height=18, stroke_width=2, visible=False
        )
        self._manual_button = ft.TextButton(
            "我已複製 API Key",
            icon=ft.Icons.CONTENT_PASTE,
            on_click=self._on_manual_paste,
            visible=False,
        )

        self._capturing = False
        self._applying = False
        self._saved = False
        self._closed = False

    # ------------------------------------------------------------------ UI

    def show(self) -> None:
        """Show the login dialog."""
        if self._supports_webview():
            content = self._build_webview_content()
            actions = [
                self._manual_button,
                ft.TextButton("取消", on_click=lambda _: self._close()),
            ]
        else:
            content = self._build_browser_content()
            actions = [
                ft.OutlinedButton(
                    "開啟瀏覽器登入",
                    icon=ft.Icons.OPEN_IN_NEW,
                    on_click=self._on_open_browser,
                ),
                ft.FilledButton(
                    "從剪貼簿貼上",
                    icon=ft.Icons.CONTENT_PASTE,
                    on_click=self._on_manual_paste,
                ),
                ft.TextButton("取消", on_click=lambda _: self._close()),
            ]

        self._dialog = ft.AlertDialog(
            modal=True,
            inset_padding=ft.padding.symmetric(horizontal=8, vertical=8),
            content_padding=ft.padding.symmetric(horizontal=8, vertical=8),
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.LOGIN, size=22),
                    ft.Text("使用 Discord 登入", weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=content,
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.show_dialog(self._dialog)

    def _build_webview_content(self) -> ft.Control:
        self._webview = WebView(
            url=build_login_url(),
            expand=True,
            on_url_change=self._on_url_change,
            on_page_ended=self._on_page_ended,
            on_console_message=self._on_console_message,
        )

        return ft.Container(
            width=280,
            height=440,
            content=ft.Column(
                [
                    ft.Text("登入完成後會自動取得 API Key，不需要手動複製。", size=13),
                    ft.Container(
                        content=self._webview,
                        expand=True,
                        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                        border_radius=12,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                    ft.Row(
                        [self._progress, self._status],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.TextButton(
                        "改用瀏覽器登入",
                        on_click=self._on_open_browser,
                    ),
                ],
                spacing=6,
                expand=True,
            ),
        )

    def _build_browser_content(self) -> ft.Control:
        return ft.Column(
            [
                ft.Text("此裝置不支援內嵌登入，請改用瀏覽器：", size=14),
                ft.Text("1. 點擊「開啟瀏覽器登入」並完成 Discord 登入", size=13),
                ft.Text("2. 在 DCTW 後台點擊「複製 API KEY」", size=13),
                ft.Text("3. 回到應用程式，點擊「從剪貼簿貼上」", size=13),
                ft.Divider(height=12),
                ft.Row(
                    [self._progress, self._status],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            tight=True,
            spacing=8,
        )

    def _supports_webview(self) -> bool:
        if WebView is None:
            return False
        try:
            if self._page.web:
                return False
            return self._page.platform in WEBVIEW_PLATFORMS
        except Exception:
            return False

    def _close(self) -> None:
        if self._closed:
            return

        self._closed = True
        try:
            self._page.pop_dialog()
        except Exception:
            logger.exception("Failed to close the Discord login dialog")

        if self._on_close is not None:
            try:
                self._on_close()
            except Exception:
                logger.exception("Discord login close callback failed")

    # -------------------------------------------------------------- login

    def _on_url_change(self, e) -> None:
        self._handle_url(str(getattr(e, "data", "") or ""))

    def _on_page_ended(self, e) -> None:
        url = str(getattr(e, "data", "") or "")
        self._handle_url(url)
        if (
            self._capturing
            and not self._saved
            and _host_of(url).endswith("dctw.xyz")
        ):
            self._page.run_task(self._inject_capture)

    def _handle_url(self, url: str) -> None:
        if not url or self._saved:
            return

        host = _host_of(url)
        if host.endswith("discord.com"):
            self._set_status("請在 Discord 完成登入…", busy=True)
            return

        if not host.endswith("dctw.xyz"):
            return

        if "error=" in url or "error_description=" in url:
            self._set_status("登入沒有完成（可能已取消），請再試一次。", busy=False)
            return

        if "code=" in url:
            self._set_status("正在完成登入…", busy=True)
            return

        self._start_capture()

    def _start_capture(self) -> None:
        if self._capturing or self._saved:
            return

        self._capturing = True
        self._set_status("登入成功，正在取得 API Key…", busy=True)
        self._page.run_task(self._capture_flow)

    async def _capture_flow(self) -> None:
        """Open the dashboard and try to read the API key from the page."""
        try:
            current = None
            if self._webview is not None:
                try:
                    current = await self._webview.get_current_url()
                except Exception:
                    current = None

            if not current or "/dashboard" not in current:
                try:
                    self._webview.url = DCTW_DASHBOARD_URL
                    self._webview.update()
                except Exception:
                    logger.exception("Failed to open the DCTW dashboard")
                await asyncio.sleep(2.5)

            await self._inject_capture()

            self._manual_button.visible = True
            self._refresh()

            if self._page.platform == ft.PagePlatform.ANDROID:
                for _ in range(4):
                    await asyncio.sleep(1.0)
                    if self._saved or self._closed:
                        return
                    key = await self._read_clipboard_key()
                    if key:
                        await self._apply_key(key)
                        return
        except Exception:
            logger.exception("Failed to capture the API key from the dashboard")

    async def _inject_capture(self) -> None:
        if self._webview is None or self._saved or self._closed:
            return
        try:
            await self._webview.run_javascript(CAPTURE_SCRIPT)
        except Exception:
            logger.exception("Failed to run the API key capture script")

    def _on_console_message(self, e) -> None:
        message = str(getattr(e, "message", "") or "")
        if KEY_MARKER not in message:
            return

        key = extract_api_key(message)
        if key:
            self._page.run_task(self._apply_key, key)

    # -------------------------------------------------------------- apply

    def _on_manual_paste(self, _e) -> None:
        self._page.run_task(self._manual_apply)

    async def _manual_apply(self) -> None:
        self._set_status("正在從剪貼簿讀取 API Key…", busy=True)
        key = await self._read_clipboard_key()
        if not key:
            self._set_status(
                "剪貼簿中沒有 API Key，請先在 DCTW 後台點擊「複製 API KEY」。",
                busy=False,
            )
            return

        await self._apply_key(key)

    async def _read_clipboard_key(self) -> Optional[str]:
        try:
            value = await ft.Clipboard().get()
        except Exception:
            logger.exception("Failed to read the clipboard")
            return None

        return extract_api_key(value)

    async def _apply_key(self, key: str) -> None:
        if self._saved or self._applying:
            return

        self._applying = True
        self._set_status("已取得 API Key，正在驗證…", busy=True)
        try:
            ok, message = await apply_api_key(
                key, self._preferences, self._discovery, self._api_client
            )
        finally:
            self._applying = False

        if not ok:
            self._set_status(message, busy=False)
            return

        self._saved = True
        self._set_status(message, busy=False)

        await asyncio.sleep(0.6)
        self._close()
        Toast(self._page).show("已使用 Discord 登入並自動填入 API Key")

        if self._on_saved is not None:
            try:
                self._on_saved()
            except Exception:
                logger.exception("Discord login saved callback failed")

    # ------------------------------------------------------------ events

    def _on_open_browser(self, _e) -> None:
        open_url(self._page, build_login_url())
        self._manual_button.visible = True
        self._set_status(
            "請在瀏覽器完成登入並複製 API Key，再回來點擊「我已複製 API Key」。",
            busy=False,
        )

    def _set_status(self, message: str, busy: bool = False) -> None:
        if self._closed:
            return

        self._status.value = message
        self._progress.visible = busy
        self._refresh()

    def _refresh(self) -> None:
        try:
            self._page.update()
        except Exception:
            logger.debug("Page closed before the login dialog could be refreshed")
