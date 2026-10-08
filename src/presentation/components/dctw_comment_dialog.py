"""Leave or remove a review with the official DCTW login session.

The review endpoints of dctw.xyz are Next.js server actions that only
accept the Discord login session of the website, an API key is rejected
(verified against the live site). Reviews are therefore sent from inside a
WebView that carries that session: the page of the item is opened, the same
action the website calls is executed there and the answer is reported back
through the JavaScript console. When nobody is signed in the WebView shows
the Discord login first and the review is sent right after it.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Callable, Dict, Optional
from urllib.parse import quote

import flet as ft

from infrastructure.config.constants import DCTW_WEBSITE_URL
from presentation.url_helper import open_url

try:  # The WebView control ships as an optional Flet extension.
    from flet_webview import WebView
except Exception:  # pragma: no cover - extension not installed
    WebView = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# The website signs users in with its own Discord application.
DISCORD_CLIENT_ID = "1410309371174326364"
DISCORD_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
DCTW_LOGIN_REDIRECT = f"{DCTW_WEBSITE_URL}/login"

# Server action the website uses to read the signed in user.
SESSION_USER_ACTION = "00c157a1e18b5f15bf55205390aff7e0e58bc4c6bf"

COMMENT_MARKER = "DCTWFletComment:"
SUBMIT_TIMEOUT = 45.0
CLOSE_DELAY = 0.6

WEBVIEW_PLATFORMS = (
    ft.PagePlatform.ANDROID,
    ft.PagePlatform.IOS,
    ft.PagePlatform.MACOS,
)

LOGIN_REQUIRED_MESSAGE = "留言需要登入 DCTW，請在下方使用 Discord 登入。"
TIMEOUT_MESSAGE = "留言送出逾時，請確認網路連線後再試一次。"
NO_WEBVIEW_MESSAGE = (
    "此裝置不支援在應用程式內留言，請使用手機版 App，或在瀏覽器開啟 DCTW 留言。"
)
NO_COMMENT_MESSAGE = "您還沒有留言，無法刪除。"

# The website shows the review form of a detail page and sends the same
# Next.js server actions from the browser. The script below repeats that
# call inside the page so the site session (cookie) is used.
SCRIPT_TEMPLATE = r"""
(function () {
  if (window.__dctwfletReview) { return "busy"; }
  window.__dctwfletReview = true;

  var report = function (value) {
    try { console.log("__MARKER__" + JSON.stringify(value)); } catch (error) {}
  };
  var parseRows = function (text) {
    var found = [];
    String(text || "").split("\n").forEach(function (line) {
      var index = line.indexOf(":");
      if (index < 0) { return; }
      try { found.push(JSON.parse(line.slice(index + 1))); } catch (error) {}
    });
    return found;
  };
  var pickObject = function (list, key) {
    for (var index = list.length - 1; index >= 0; index -= 1) {
      var item = list[index];
      if (item && typeof item === "object" && !Array.isArray(item) &&
          Object.prototype.hasOwnProperty.call(item, key)) {
        return item;
      }
    }
    return null;
  };
  var pickList = function (list) {
    for (var index = list.length - 1; index >= 0; index -= 1) {
      if (Array.isArray(list[index])) { return list[index]; }
    }
    return [];
  };
  var call = function (action, payload) {
    return fetch(window.location.pathname, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Next-Action": action,
        "Content-Type": "text/plain;charset=UTF-8",
        "Accept": "text/x-component"
      },
      body: JSON.stringify(payload)
    }).then(function (response) { return response.text(); });
  };
  var toAnswer = function (reply) {
    var row = pickObject(parseRows(reply), "ok");
    if (!row) { return { ok: true, message: "" }; }
    return { ok: row.ok !== false, message: String(row.message || "") };
  };
  var ownReview = function (user) {
    return call("__LIST_ACTION__", [__ITEM_ID__]).then(function (reply) {
      var list = pickList(parseRows(reply)) || [];
      for (var index = 0; index < list.length; index += 1) {
        if (list[index] && String(list[index].userId) === String(user.id)) {
          return list[index];
        }
      }
      return null;
    });
  };
  var describe = function (user) {
    return { id: String(user.id), name: String(user.global_name || user.username || "") };
  };
  var fail = function (error) {
    report({ status: "error", message: String((error && error.message) || error) });
  };

  call("__SESSION_ACTION__", []).then(function (reply) {
    var user = pickObject(parseRows(reply), "id");
    if (!user || !user.id) { report({ status: "login" }); return; }
    return ownReview(user).then(function (existing) {
      __ACTION__
      if (__MODE__ === "delete" && !existing) {
        report({ status: "error", message: __NO_COMMENT__, user: describe(user) });
        return;
      }
      return call(target, payload).then(function (answer) {
        var result = toAnswer(answer);
        report({
          status: result.ok ? "ok" : "error",
          message: result.message,
          user: describe(user)
        });
      });
    });
  }).catch(fail);

  return "started";
})()
"""


@dataclass
class CommentResult:
    """Outcome of a review action."""

    ok: bool = False
    message: str = ""
    user_id: str = ""
    user_name: str = ""


def build_comment_script(
    mode: str,
    actions: Dict[str, str],
    item_id: str,
    stars: int = 0,
    content: str = "",
) -> str:
    """Return the JavaScript that runs the website action in the WebView.

    ``mode`` is either ``submit`` (insert or update the own review) or
    ``delete`` (remove the own review).
    """
    item = json.dumps(str(item_id))

    if mode == "delete":
        body = (
            "var target = %s;"
            " var payload = [%s, String(user.id)];"
            % (json.dumps(str(actions.get("delete", ""))), item)
        )
    else:
        body = (
            "var target = existing ? %s : %s;"
            " var payload = [%s, %d, %s];"
            % (
                json.dumps(str(actions.get("edit", ""))),
                json.dumps(str(actions.get("insert", ""))),
                item,
                int(stars),
                json.dumps(str(content or "")),
            )
        )

    script = SCRIPT_TEMPLATE.replace("__MARKER__", COMMENT_MARKER)
    script = script.replace("__SESSION_ACTION__", SESSION_USER_ACTION)
    script = script.replace("__LIST_ACTION__", str(actions.get("list", "")))
    script = script.replace("__ITEM_ID__", item)
    script = script.replace("__MODE__", json.dumps(mode))
    script = script.replace("__NO_COMMENT__", json.dumps(NO_COMMENT_MESSAGE))
    return script.replace("__ACTION__", body)


def build_login_url(state: str) -> str:
    """Build the Discord OAuth2 URL the official website uses to log in."""
    return (
        f"{DISCORD_AUTHORIZE_URL}?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={quote(DCTW_LOGIN_REDIRECT, safe='')}"
        "&response_type=code&scope=identify%20guilds&prompt=consent"
        f"&state={quote(state, safe='')}"
    )


def _host_of(url: str) -> str:
    """Return the host of a URL, lower case, without the scheme."""
    match = re.match(r"^[a-zA-Z]+://([^/?#]+)", url or "")
    return match.group(1).lower() if match else ""


class DctwCommentDialog:
    """Run one review action inside a WebView that carries the session.

    ``mode`` is ``submit`` (insert or update the own review) or ``delete``
    (remove the own review). The outcome is reported through ``on_done``.
    """

    def __init__(
        self,
        page: ft.Page,
        item_path: str,
        actions: Dict[str, str],
        mode: str = "submit",
        item_id: str = "",
        stars: int = 0,
        content: str = "",
        on_done: Optional[Callable[[CommentResult], None]] = None,
    ) -> None:
        self._page = page
        self._item_path = item_path if item_path.startswith("/") else f"/{item_path}"
        self._actions = dict(actions or {})
        self._mode = mode
        self._item_id = str(item_id)
        self._stars = stars
        self._content = content
        self._on_done = on_done

        self._dialog: Optional[ft.AlertDialog] = None
        self._webview = None
        self._script = ""
        self._injected = False
        self._finished = False
        self._closed = False
        self._login_started = False

        self._status = ft.Text("正在送出留言…", size=13)
        self._progress = ft.ProgressRing(
            width=16, height=16, stroke_width=2, visible=True
        )
        self._browser_button = ft.TextButton(
            "改用瀏覽器", on_click=self._on_open_browser
        )
        self._retry_button = ft.TextButton(
            "重試", on_click=self._on_retry, visible=False
        )
        self._close_button = ft.TextButton("關閉", on_click=lambda _: self._close())

    # --------------------------------------------------------------- public

    @property
    def page_url(self) -> str:
        """URL of the detail page the review belongs to."""
        return f"{DCTW_WEBSITE_URL}{self._item_path}"

    def show(self) -> None:
        """Open the dialog and run the review action."""
        if not self._supports_webview():
            self._show_unsupported()
            return

        self._script = build_comment_script(
            self._mode, self._actions, self._item_id, self._stars, self._content
        )
        self._webview = WebView(
            url=self.page_url,
            expand=True,
            on_url_change=self._on_url_change,
            on_page_ended=self._on_page_ended,
            on_console_message=self._on_console_message,
        )

        self._dialog = ft.AlertDialog(
            modal=True,
            inset_padding=ft.padding.symmetric(horizontal=8, vertical=8),
            content_padding=ft.padding.symmetric(horizontal=8, vertical=8),
            title=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.DELETE_OUTLINE
                        if self._mode == "delete"
                        else ft.Icons.RATE_REVIEW,
                        size=22,
                    ),
                    ft.Text(
                        "刪除留言" if self._mode == "delete" else "送出留言",
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                spacing=8,
            ),
            content=self._build_content(),
            actions=[self._browser_button, self._retry_button, self._close_button],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.show_dialog(self._dialog)
        self._page.run_task(self._watch_timeout)

    # ------------------------------------------------------------------ ui

    def _build_content(self) -> ft.Control:
        return ft.Column(
            [
                ft.Text(
                    "留言會以你的 DCTW 登入身分送出，尚未登入時請先完成 Discord 登入。",
                    size=12,
                    color=ft.Colors.OUTLINE,
                ),
                ft.Container(
                    content=self._webview,
                    height=380,
                    border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=12,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                ),
                ft.Row(
                    [self._progress, self._status],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=8,
            tight=True,
        )

    def _show_unsupported(self) -> None:
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [ft.Icon(ft.Icons.RATE_REVIEW, size=22), ft.Text("送出留言")],
                spacing=8,
            ),
            content=ft.Text(NO_WEBVIEW_MESSAGE, size=13),
            actions=[
                ft.TextButton("開啟 DCTW", on_click=self._on_open_browser),
                self._close_button,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.show_dialog(self._dialog)

    def _supports_webview(self) -> bool:
        if WebView is None:
            return False
        try:
            if self._page.web:
                return False
            return self._page.platform in WEBVIEW_PLATFORMS
        except Exception:
            return False

    # -------------------------------------------------------------- webview

    def _on_url_change(self, e) -> None:
        url = str(getattr(e, "data", "") or "")
        host = _host_of(url)
        self._injected = False

        if self._finished or self._closed:
            return

        if host.endswith("discord.com"):
            self._set_status("請在 Discord 完成登入…")
        elif "code=" in url:
            self._set_status("正在完成登入…")

    def _on_page_ended(self, e) -> None:
        url = str(getattr(e, "data", "") or "")
        if self._finished or self._closed:
            return
        if not _host_of(url).endswith("dctw.xyz"):
            return
        if "/login" in url:
            return
        self._page.run_task(self._inject)

    async def _inject(self) -> None:
        if self._webview is None or self._injected or self._finished or self._closed:
            return

        self._injected = True
        try:
            await self._webview.run_javascript(self._script)
        except Exception:
            logger.exception("Failed to run the review script")
            self._injected = False
            self._set_status("無法送出留言，請再試一次。", busy=False)

    def _on_console_message(self, e) -> None:
        message = str(getattr(e, "message", "") or getattr(e, "data", "") or "")
        index = message.find(COMMENT_MARKER)
        if index < 0:
            return

        try:
            data = json.loads(message[index + len(COMMENT_MARKER):].strip())
        except ValueError:
            return

        if isinstance(data, dict):
            self._handle(data)

    # --------------------------------------------------------------- result

    def _handle(self, data: dict) -> None:
        if self._finished or self._closed:
            return

        status = str(data.get("status") or "")
        user = data.get("user") or {}
        user_id = str(user.get("id") or "")
        user_name = str(user.get("name") or "")

        if status == "login":
            self._set_status(LOGIN_REQUIRED_MESSAGE)
            if not self._login_started:
                self._show_login()
            return

        if status == "ok":
            self._finish(
                CommentResult(
                    ok=True,
                    message=str(data.get("message") or ""),
                    user_id=user_id,
                    user_name=user_name,
                )
            )
            return

        message = str(data.get("message") or "") or "留言送出失敗，請稍後再試一次。"
        if "登入" in message and "留言" not in message:
            self._set_status(LOGIN_REQUIRED_MESSAGE)
            if not self._login_started:
                self._show_login()
            return

        self._set_status(message, busy=False)
        self._retry_button.visible = True
        self._refresh()

    def _show_login(self) -> None:
        if self._webview is None:
            return

        self._login_started = True
        self._injected = False
        try:
            self._webview.url = build_login_url(self.page_url)
            self._webview.update()
        except Exception:
            logger.exception("Failed to open the DCTW login page")

    def _finish(self, result: CommentResult) -> None:
        if self._finished:
            return

        self._finished = True
        self._page.run_task(self._close_with_result, result)

    async def _close_with_result(self, result: CommentResult) -> None:
        self._set_status(result.message or "留言已送出！", busy=False)
        await asyncio.sleep(CLOSE_DELAY)
        self._close()

        if self._on_done is not None:
            try:
                self._on_done(result)
            except Exception:
                logger.exception("Comment result callback failed")

    async def _watch_timeout(self) -> None:
        await asyncio.sleep(SUBMIT_TIMEOUT)
        if self._finished or self._closed or self._login_started:
            return

        self._set_status(TIMEOUT_MESSAGE, busy=False)
        self._retry_button.visible = True
        self._refresh()

    # --------------------------------------------------------------- events

    def _on_retry(self, _e) -> None:
        if self._webview is None:
            return

        self._retry_button.visible = False
        self._login_started = False
        self._set_status("正在重新送出留言…")
        try:
            self._page.run_task(self._webview.reload)
        except Exception:
            logger.exception("Failed to reload the review page")

    def _on_open_browser(self, _e) -> None:
        open_url(self._page, self.page_url)

    def _set_status(self, message: str, busy: bool = True) -> None:
        if self._closed:
            return

        self._status.value = message
        self._progress.visible = busy
        self._refresh()

    def _refresh(self) -> None:
        try:
            self._page.update()
        except Exception:
            logger.debug("Page closed before the comment dialog could refresh")

    def _close(self) -> None:
        if self._closed:
            return

        self._closed = True
        try:
            self._page.pop_dialog()
        except Exception:
            logger.exception("Failed to close the comment dialog")
