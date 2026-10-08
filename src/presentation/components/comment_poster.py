"""Wire the review form of a detail page to the website session.

The official website only accepts reviews from a signed in Discord session,
so the form of a detail page opens :class:`DctwCommentDialog`, which runs
the review action inside a WebView that carries that session. Afterwards
the review list is reloaded from the website action and the detail page is
told about the new list and the account that wrote it.
"""

import logging
from typing import Callable, List, Optional

from application.services import PreferenceService
from domain.discovery.value_objects import Comment
from infrastructure.api import DctwApiClient
from infrastructure.repositories.api_helpers import parse_comments

from .dctw_comment_dialog import CommentResult, DctwCommentDialog
from .toast import Toast

logger = logging.getLogger(__name__)

SUBMIT_FAILED = "留言失敗，請稍後再試一次。"
SUBMIT_DONE = "留言已送出！"
DELETE_DONE = "留言已刪除！"


class CommentPoster:
    """Send, update and remove the review of the signed in DCTW user."""

    def __init__(
        self,
        page,
        item_type: str,
        item_id,
        api_client: DctwApiClient,
        preference_service: PreferenceService,
        on_comments: Optional[
            Callable[[List[Comment], str, str], None]
        ] = None,
    ) -> None:
        self._page = page
        self._item_type = str(item_type)
        self._item_id = str(item_id)
        self._api_client = api_client
        self._preferences = preference_service
        self._on_comments = on_comments
        self._user_id = ""
        self._user_name = ""
        self._busy = False

    # ----------------------------------------------------------------- user

    @property
    def user_id(self) -> str:
        """Discord id of the account that signed in, empty when unknown."""
        return self._user_id

    @property
    def user_name(self) -> str:
        """Display name of that account."""
        return self._user_name

    def sync_user(self) -> None:
        """Read the signed in account from the stored preferences."""
        try:
            preferences = self._preferences.get_current_preferences()
        except Exception:
            preferences = None

        if preferences is None:
            return

        self._user_id = str(getattr(preferences, "dctw_user_id", "") or "")
        self._user_name = str(getattr(preferences, "dctw_user_name", "") or "")

    # --------------------------------------------------------------- review

    def submit(self, stars: int, content: str) -> None:
        """Send the review of the form (insert or update)."""
        self._open("submit", stars, content)

    def delete(self) -> None:
        """Remove the own review."""
        self._open("delete", 0, "")

    def _open(self, mode: str, stars: int, content: str) -> None:
        if self._busy:
            return

        actions = self._api_client.comment_actions(self._item_type)
        if not actions:
            Toast(self._page).show(SUBMIT_FAILED)
            return

        try:
            dialog = DctwCommentDialog(
                page=self._page,
                item_path=f"/{self._item_type}/{self._item_id}/",
                actions=actions,
                mode=mode,
                item_id=self._item_id,
                stars=stars,
                content=content,
                on_done=lambda result, mode=mode: self._finished(mode, result),
            )
        except Exception:
            logger.exception("Failed to open the review dialog")
            Toast(self._page).show(SUBMIT_FAILED)
            return

        self._busy = True
        dialog.show()

    def _finished(self, mode: str, result: CommentResult) -> None:
        self._busy = False

        if not result.ok:
            Toast(self._page).show(result.message or SUBMIT_FAILED)
            return

        if result.user_id:
            self._user_id = result.user_id
            self._user_name = result.user_name or self._user_name
            self._page.run_task(self._store_user)

        Toast(self._page).show(
            result.message or (DELETE_DONE if mode == "delete" else SUBMIT_DONE)
        )
        self._page.run_task(self._reload)

    async def _store_user(self) -> None:
        try:
            await self._preferences.update_dctw_user(self._user_id, self._user_name)
        except Exception:
            logger.debug("Failed to store the signed in DCTW user")

    async def _reload(self) -> None:
        try:
            raw = await self._api_client.get_comments(self._item_type, self._item_id)
        except Exception as error:
            logger.warning(f"Failed to reload the reviews: {error}")
            return

        if self._on_comments is None:
            return

        try:
            self._on_comments(parse_comments(raw), self._user_id, self._user_name)
        except Exception:
            logger.debug("Detail page closed before the reviews arrived")
