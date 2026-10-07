"""DCTW API key dialog.

The API key is copied from the DCTW dashboard (after logging in on
https://dctw.xyz) and pasted into the app from the clipboard. It is only
needed for voting; browsing bots, servers and templates works without it.
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
        on_close: Optional[Callable[[], None]] = None,
    ):
        self.page = page
        self._preferences = preference_service
        self._discovery = discovery_service
        self._api_client = api_client
        self._on_saved = on_saved
        self._on_close = on_close

        self._dialog: Optional[ft.AlertDialog] = None
        self._status = ft.Text("請先在 DCTW 後台複製 API KEY，再點擊下方按鈕。", size=13)
        self._progress = ft.ProgressRing(
            width=18, height=18, stroke_width=2, visible=False
        )

    # ------------------------------------------------------------------ UI

    def show(self, dismissible: bool = True) -> None:
        """Show the API key dialog."""
        actions = [
            ft.FilledButton(
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
                    ft.Text("瀏覽資料不需要登入；投票時才需要 DCTW API Key。", size=14),
                    ft.Text("1. 到 DCTW 官網登入後，在後台複製 API KEY。", size=13),
                    ft.Text(
                        "2. 回到應用程式點擊「從剪貼簿貼上」，會自動驗證並儲存。",
                        size=13,
                    ),
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

        if self._on_close is not None:
            try:
                self._on_close()
            except Exception:
                logger.exception("API key dialog close callback failed")

    # -------------------------------------------------------------- events

    def _on_paste(self, _e) -> None:
        self.page.run_task(self._paste_from_clipboard)

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
