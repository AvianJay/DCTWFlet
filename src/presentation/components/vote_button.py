"""Vote button for detail pages.

Calls the DCTW vote API and shows the result as a toast. Voting needs a
DCTW API key; when none is stored (or the key was revoked) the button
opens the API key dialog so the key can be pasted from the clipboard and
the vote is cast right after.
"""

import logging
from typing import Callable, Optional, Union

import flet as ft

from application.services import DiscoveryService, PreferenceService
from infrastructure.api import DctwApiClient
from infrastructure.di import get_container

from .api_key_dialog import ApiKeyDialog
from .toast import Toast

logger = logging.getLogger(__name__)

VOTE_RESULT_DURATION = 4.0


class VoteButton(ft.ElevatedButton):
    """Elevated button that casts a DCTW vote for one item."""

    def __init__(
        self,
        page: ft.Page,
        api_client: DctwApiClient,
        item_type: str,
        item_id: Union[int, str],
        on_success: Optional[Callable[[], None]] = None,
    ):
        super().__init__(
            content=ft.Text("投票"),
            icon=ft.Icons.HOW_TO_VOTE,
            on_click=self._on_click,
        )
        self._page = page
        self._api_client = api_client
        self._item_type = item_type
        self._item_id = item_id
        self._on_success = on_success
        self._voting = False
        self._key_dialog_open = False

    def _on_click(self, _e) -> None:
        self._page.run_task(self._vote)

    async def _vote(self) -> None:
        if self._voting:
            return

        self._voting = True
        self.disabled = True
        self._refresh_page()

        try:
            result = await self._api_client.vote(self._item_type, self._item_id)

            if result.get("needs_key"):
                self._prompt_api_key(str(result.get("message") or ""))
                return

            message = str(result.get("message") or "").strip()
            if result.get("ok"):
                if self._on_success is not None:
                    try:
                        self._on_success()
                    except Exception:
                        logger.exception("Vote success callback failed")
                message = message or "已成功投票！"
            self._show_message(message or "投票失敗，請稍後再試。")
        except Exception as error:
            logger.warning(
                "Vote failed for %s %s: %s", self._item_type, self._item_id, error
            )
            self._show_message(f"投票失敗：{error}")
        finally:
            self._voting = False
            self.disabled = False
            self._refresh_page()

    # ------------------------------------------------------------- api key

    def _prompt_api_key(self, reason: str) -> None:
        """Ask for the API key pasted from the clipboard, then vote again."""
        if self._key_dialog_open:
            return

        self._key_dialog_open = True
        Toast(self._page).show(
            reason or "投票需要 DCTW API Key，請從剪貼簿貼上 API Key。",
            duration=VOTE_RESULT_DURATION,
        )

        try:
            container = get_container()
            dialog = ApiKeyDialog(
                page=self._page,
                preference_service=container.resolve(PreferenceService),
                discovery_service=container.resolve(DiscoveryService),
                api_client=self._api_client,
                on_saved=self._retry_vote,
                on_close=self._on_key_dialog_closed,
            )
        except Exception:
            logger.exception("Failed to open the API key dialog")
            self._key_dialog_open = False
            return

        dialog.show()

    def _on_key_dialog_closed(self) -> None:
        self._key_dialog_open = False

    def _retry_vote(self) -> None:
        self._key_dialog_open = False
        self._page.run_task(self._vote)

    # -------------------------------------------------------------- helpers

    def _show_message(self, message: str) -> None:
        Toast(self._page).show(message, duration=VOTE_RESULT_DURATION)

    def _refresh_page(self) -> None:
        try:
            self._page.update()
        except Exception:
            logger.debug("Page closed before the vote button could be refreshed")
