"""DCTW API key helpers

The API key is copied from the DCTW dashboard (after logging in on
https://dctw.xyz) and pasted into the app from the clipboard.
"""

import asyncio
import logging
from typing import Callable, Optional, Tuple

import flet as ft

from application.services import DiscoveryService, PreferenceService
from infrastructure.api import DctwApiClient

logger = logging.getLogger(__name__)


async def apply_api_key(
    value: Optional[str],
    preference_service: PreferenceService,
    discovery_service: DiscoveryService,
    api_client: DctwApiClient,
) -> Tuple[bool, str]:
    """Validate an API key and store it.

    Returns:
        A tuple of (success, message).
    """
    key = (value or "").strip()
    if not key:
        return False, "剪貼簿中沒有可用的 API Key，請先在 DCTW 後台複製 API KEY。"

    try:
        is_valid = await api_client.validate_api_key(key)
    except Exception as ex:
        logger.exception("API key validation failed")
        return False, f"驗證失敗（{ex}），請確認網路連線後再試。"

    if not is_valid:
        return False, "此 API Key 無效或已失效，請重新複製正確的 API KEY。"

    try:
        await preference_service.update_api_key(key)
        await discovery_service.clear_all_caches()
    except Exception as ex:
        logger.exception("Failed to store API key")
        return False, f"儲存 API Key 失敗：{ex}"

    return True, "已成功儲存 API Key，正在重新載入資料…"


async def apply_api_key_from_clipboard(
    preference_service: PreferenceService,
    discovery_service: DiscoveryService,
    api_client: DctwApiClient,
) -> Tuple[bool, str]:
    """Read the clipboard and apply the API key found in it."""
    try:
        clipboard_value = await ft.Clipboard().get()
    except Exception:
        logger.exception("Failed to read clipboard")
        return False, "無法讀取剪貼簿，請改用手動輸入 API Key。"

    return await apply_api_key(
        clipboard_value, preference_service, discovery_service, api_client
    )


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
                "從剪貼簿貼上",
                icon=ft.Icons.CONTENT_PASTE,
                on_click=self._on_paste,
            )
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
                    ft.Text("1. 在 DCTW 官網（dctw.xyz）使用 Discord 登入", size=13),
                    ft.Text("2. 進入後台，在個人檔案旁點擊「複製 API KEY」", size=13),
                    ft.Text("3. 回到本應用程式，點擊下方「從剪貼簿貼上」", size=13),
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
