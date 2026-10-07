"""Vote button for detail pages.

Calls the DCTW vote API and shows the result as a toast. When no API key
is stored yet (or the stored key was revoked) the button opens the
Discord login dialog and casts the vote right after the login.
"""

import logging
from typing import Callable, Optional, Union

import flet as ft

from application.services import DiscoveryService, PreferenceService
from infrastructure.api import ApiKeyMissingError, DctwApiClient, InvalidApiKeyError
from infrastructure.di import get_container

from .discord_login_dialog import DiscordLoginDialog
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
        self._login_open = False

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
        except ApiKeyMissingError:
            self._prompt_login("需要登入 DCTW 才能投票，請使用 Discord 登入。")
        except InvalidApiKeyError:
            self._prompt_login("API Key 已失效，請重新使用 Discord 登入。")
        except Exception as error:
            logger.warning(
                "Vote failed for %s %s: %s", self._item_type, self._item_id, error
            )
            self._show_message(f"投票失敗：{error}")
        else:
            message = str(result.get("message") or "").strip()
            if result.get("ok"):
                if self._on_success is not None:
                    try:
                        self._on_success()
                    except Exception:
                        logger.exception("Vote success callback failed")
                message = message or "已成功投票！"
            self._show_message(message or "投票失敗，請稍後再試。")
        finally:
            self._voting = False
            self.disabled = False
            self._refresh_page()

    # ---------------------------------------------------------------- login

    def _prompt_login(self, reason: str) -> None:
        """Ask the user to sign in with Discord, then vote again."""
        if self._login_open:
            return

        self._login_open = True
        Toast(self._page).show("請先使用 Discord 登入，登入後會自動投票。", duration=3.0)

        try:
            container = get_container()
            dialog = DiscordLoginDialog(
                page=self._page,
                preference_service=container.resolve(PreferenceService),
                discovery_service=container.resolve(DiscoveryService),
                api_client=self._api_client,
                on_saved=self._retry_vote,
                on_close=self._on_login_closed,
                reason=reason,
            )
        except Exception:
            logger.exception("Failed to open the Discord login dialog")
            self._login_open = False
            return

        dialog.show()

    def _retry_vote(self) -> None:
        self._page.run_task(self._vote)

    def _on_login_closed(self) -> None:
        self._login_open = False

    # -------------------------------------------------------------- helpers

    def _show_message(self, message: str) -> None:
        Toast(self._page).show(message, duration=VOTE_RESULT_DURATION)

    def _refresh_page(self) -> None:
        try:
            self._page.update()
        except Exception:
            logger.debug("Page closed before the vote button could be refreshed")
