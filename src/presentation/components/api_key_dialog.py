"""DCTW API key helpers.

The API key can be fetched automatically with the in-app Discord login or
copied from the DCTW dashboard (after logging in on https://dctw.xyz) and
pasted into the app from the clipboard.
"""

import asyncio
import logging
from typing import Callable, Optional

import flet as ft

from application.services import DiscoveryService, PreferenceService
from infrastructure.api import DctwApiClient

from .api_key_helpers import apply_api_key, apply_api_key_from_clipboard

logger = logging.getLogger(__name__)


class ApiKeyDialog:
    """Dialog that stores the API key copied from the DCTW dashboard."""

    def __init__(
        self,
        page: ft.Page,
        preference_service: PreferenceService,
        discovery_service: DiscoveryService,
        api_client: DctwApiClient,
        on_saved: Optional[Callable[[], None]] = None,
    ):
        self.page = page
        self._preferences = preference_service
        self._discovery = discovery_service
        self._api_client = api_client
        self._on_saved = on_saved

        self._dialog: Optional[ft.AlertDialog] = None
        self._status = ft.Text("請先複製 API KEY，再點擊下方按鈕。", size=13)
        self._progress = ft.ProgressRing(
            width=18, height=18, stroke_width=2, visible=False
        )

    # ------------------------------------------------------------------ UI

    def show(self, dismissible: bool = True) -> None:
        """Show the API key dialog."""
        actions = [
            ft.FilledButton(
                "使用 Discord 登入",
                icon=ft.Icons.LOGIN,
                on_click=self._on_login,
            ),
            ft.OutlinedButton(
                "從剪貼簿貼上",
                icon=ft.Icons.CONTENT_PASTE,
                on_click=self._on_paste,
            ),
        ]
        if dismissible:
            actions.append(ft.TextButton("稍後", on_click=lambda _: self._close()))

        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.KEY, size=22),
                    ft.Text("設定 DCTW API Key", weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Column(
                [
                    ft.Text(
                        "DCTW API 需要 API Key 才能取得資料，取得方式：",
                        size=14,
                    ),
                    ft.Text("1. 點擊下方「使用 Discord 登入」在應用程式內完成登入", size=13),
                    ft.Text("2. API Key 會自動填入，不需要手動複製", size=13),
                    ft.Text("3. 也可以到 DCTW 後台複製 API KEY 後再貼上", size=13),
                    ft.Divider(height=12),
                    ft.Row(
                        [self._progress, self._status],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                tight=True,
                spacing=8,
            ),
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(self._dialog)

    def _close(self) -> None:
        try:
            self.page.pop_dialog()
        except Exception:
            logger.exception("Failed to close API key dialog")

    # -------------------------------------------------------------- events

    def _on_paste(self, _e) -> None:
        self.page.run_task(self._paste_from_clipboard)

    def _on_login(self, _e) -> None:
        """Open the in-app Discord login and store the key automatically."""
        from .discord_login_dialog import DiscordLoginDialog

        self._close()
        dialog = DiscordLoginDialog(
            page=self.page,
            preference_service=self._preferences,
            discovery_service=self._discovery,
            api_client=self._api_client,
            on_saved=self._on_saved,
        )
        dialog.show()

    async def _paste_from_clipboard(self) -> None:
        self._set_status("正在從剪貼簿讀取並驗證 API Key…", busy=True)

        ok, message = await apply_api_key_from_clipboard(
            self._preferences, self._discovery, self._api_client
        )

        self._set_status(message, busy=False)
        if not ok:
            return

        await asyncio.sleep(0.8)
        self._close()

        if self._on_saved:
            try:
                self._on_saved()
            except Exception:
                logger.exception("API key saved callback failed")

    def _set_status(self, message: str, busy: bool = False) -> None:
        self._status.value = message
        self._progress.visible = busy
        try:
            self.page.update()
        except Exception:
            pass
