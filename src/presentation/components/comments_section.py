"""Comments ("使用者評論") section shared by the detail pages.

The API embeds the reviews in the item itself, so the detail pages hand the
parsed list to this component, which resolves the reviewer names and avatars
through the same website action the official page uses. Signed in users can
also write, update and remove their own review: the form mirrors the one on
the official detail page and the review itself is sent by the caller
through the website session (see :class:`DctwCommentDialog`).
"""

import logging
from typing import Awaitable, Callable, Dict, List, Optional, Sequence

import flet as ft

from domain.discovery.entities import UserProfile
from domain.discovery.value_objects import Comment
from presentation.components.avatar_image import build_avatar

logger = logging.getLogger(__name__)

STAR_COLOR = ft.Colors.AMBER
MAX_CONTENT_LENGTH = 50
RATING_HINT = "留下你的評論，底下星星是可以點選的！"
CONTENT_HINT = "最多 50 個字"
ANONYMOUS_NAME = "訪客"
SUBMIT_LABEL = "送出留言"
UPDATE_LABEL = "編輯留言"
DELETE_LABEL = "刪除留言"
EMPTY_MESSAGE = "目前沒有評論"


def build_stars(stars: int, size: int = 16) -> ft.Control:
    """Return the five star icons of a rating, like the website shows them."""
    icons: List[ft.Control] = []
    for index in range(1, 6):
        filled = index <= stars
        icons.append(
            ft.Icon(
                ft.Icons.STAR if filled else ft.Icons.STAR_BORDER,
                size=size,
                color=STAR_COLOR if filled else ft.Colors.OUTLINE,
            )
        )
    return ft.Row(icons, spacing=1)


class CommentsSection:
    """Reusable review list and review form of the detail pages."""

    def __init__(
        self,
        page: ft.Page,
        comments: Sequence[Comment],
        load_profiles: Callable[[List[str]], Awaitable[List[UserProfile]]],
        cache_image: Callable[[str], str],
        title: str = "使用者評論",
        loading: bool = False,
        on_submit: Optional[Callable[[int, str], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
        user_id: str = "",
        user_name: str = "",
    ) -> None:
        self.page = page
        self._comments = list(comments or [])
        self._load_profiles = load_profiles
        self._cache_image = cache_image
        self._title = title
        self._loading = loading
        self._on_submit = on_submit
        self._on_delete = on_delete
        self._user_id = str(user_id or "")
        self._user_name = str(user_name or "")
        self._profiles: Dict[str, UserProfile] = {}

        self._stars = 5
        self._star_icons: List[ft.Icon] = []
        self._content_field = ft.TextField(
            hint_text=CONTENT_HINT,
            multiline=True,
            min_lines=2,
            max_lines=4,
            max_length=MAX_CONTENT_LENGTH,
            text_size=14,
            border_radius=8,
            dense=True,
        )
        self._submit_button = ft.FilledButton(
            SUBMIT_LABEL,
            icon=ft.Icons.SEND,
            on_click=self._submit_clicked,
            expand=True,
        )
        self._delete_button = ft.OutlinedButton(
            DELETE_LABEL,
            icon=ft.Icons.DELETE_OUTLINE,
            on_click=self._delete_clicked,
            expand=True,
            visible=False,
            style=ft.ButtonStyle(color=ft.Colors.ERROR),
        )
        self._composer_name = ft.Text(
            ANONYMOUS_NAME,
            size=14,
            weight=ft.FontWeight.BOLD,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self._composer_avatar = ft.Container(
            content=ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=34, color=ft.Colors.OUTLINE),
            width=40,
            height=40,
            alignment=ft.Alignment(0, 0),
        )

        self._body = ft.Column(spacing=10)
        self._summary_host = ft.Container()
        self._composer_host = ft.Container()

    # --------------------------------------------------------------- build

    def build(self) -> ft.Control:
        """Build the section; the reviewer names load in the background."""
        self._render_summary()
        self._render_composer()

        if self._comments or self._loading:
            self._begin_loading()
        else:
            self._body.controls = [
                ft.Text(EMPTY_MESSAGE, size=14, color=ft.Colors.OUTLINE)
            ]

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(self._title, size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    self._summary_host,
                    self._composer_host,
                    self._body,
                ],
                spacing=10,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=8),
        )

    def set_comments(
        self,
        comments: Sequence[Comment],
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> None:
        """Replace the reviews, e.g. after one was added or removed."""
        self._comments = list(comments or [])
        self._loading = False
        if user_id is not None:
            self._user_id = str(user_id or "")
        if user_name is not None:
            self._user_name = str(user_name or "")

        self._render_summary()
        self._render_composer()
        self._begin_loading()

    # -------------------------------------------------------------- content

    def _begin_loading(self) -> None:
        """Show the placeholder while the reviews are being resolved."""
        self._body.controls = [
            ft.Row(
                [
                    ft.ProgressRing(width=16, height=16, stroke_width=2),
                    ft.Text("載入評論...", size=13, color=ft.Colors.OUTLINE),
                ],
                spacing=8,
                alignment=ft.MainAxisAlignment.CENTER,
            )
        ]
        self.page.run_task(self._resolve_profiles)

    async def _resolve_profiles(self) -> None:
        profiles: Dict[str, UserProfile] = {}
        try:
            resolved = await self._load_profiles(
                [comment.user_id for comment in self._comments if comment.user_id]
            )
            profiles = {profile.id: profile for profile in resolved}
        except Exception as error:
            logger.warning(f"Failed to load the reviewer profiles: {error}")

        self._profiles = profiles

        try:
            self._body.controls = [
                self._build_card(comment, profiles.get(comment.user_id))
                for comment in self._comments
            ]
            if not self._comments:
                self._body.controls = [
                    ft.Text(EMPTY_MESSAGE, size=14, color=ft.Colors.OUTLINE)
                ]
            self._update_composer_avatar()
            self._body.update()
            self._composer_host.update()
        except Exception:
            logger.debug("Comment section closed before the profiles arrived")

    # ------------------------------------------------------------- composer

    def _render_composer(self) -> None:
        """Build the review form of the signed in user."""
        if self._on_submit is None:
            self._composer_host.visible = False
            return

        self._composer_host.visible = True
        mine = self._own_comment()

        if mine is not None:
            self._stars = max(1, min(5, int(mine.stars or 0)))
            self._content_field.value = mine.content or ""

        self._star_icons = []
        stars: List[ft.Control] = []
        for index in range(1, 6):
            filled = index <= self._stars
            icon = ft.Icon(
                ft.Icons.STAR if filled else ft.Icons.STAR_BORDER,
                size=26,
                color=STAR_COLOR if filled else ft.Colors.OUTLINE,
            )
            self._star_icons.append(icon)
            stars.append(
                ft.Container(
                    content=icon,
                    padding=ft.padding.all(2),
                    border_radius=6,
                    ink=True,
                    on_click=lambda _e, value=index: self._set_stars(value),
                )
            )

        self._composer_name.value = self._user_name or ANONYMOUS_NAME
        self._submit_button.content = ft.Text(
            UPDATE_LABEL if mine is not None else SUBMIT_LABEL
        )
        self._delete_button.visible = True

        self._composer_host.content = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                self._composer_avatar,
                                ft.Column(
                                    [
                                        self._composer_name,
                                        ft.Text(
                                            RATING_HINT,
                                            size=12,
                                            color=ft.Colors.OUTLINE,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                            ],
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(stars, spacing=2),
                        self._content_field,
                        ft.Row(
                            [self._submit_button, self._delete_button],
                            spacing=8,
                        ),
                    ],
                    spacing=10,
                ),
                padding=12,
            )
        )
        self._update_composer_avatar()

    def _update_composer_avatar(self) -> None:
        profile = self._profiles.get(self._user_id) if self._user_id else None
        if not profile or not profile.avatar_url:
            return

        try:
            self._composer_avatar.content = build_avatar(
                self._cache_image(profile.avatar_url), radius=20
            )
        except Exception:
            logger.debug("Failed to build the composer avatar")

    def _own_comment(self) -> Optional[Comment]:
        if not self._user_id:
            return None

        for comment in self._comments:
            if str(comment.user_id) == self._user_id:
                return comment
        return None

    def _set_stars(self, value: int) -> None:
        self._stars = max(1, min(5, int(value)))
        for index, icon in enumerate(self._star_icons, start=1):
            icon.name = ft.Icons.STAR if index <= self._stars else ft.Icons.STAR_BORDER
            icon.color = (
                STAR_COLOR if index <= self._stars else ft.Colors.OUTLINE
            )
        self._refresh()

    def _submit_clicked(self, _e) -> None:
        if self._on_submit is None:
            return

        content = (self._content_field.value or "").strip()
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]
        self._on_submit(self._stars, content)

    def _delete_clicked(self, _e) -> None:
        if self._on_delete is not None:
            self._on_delete()

    # --------------------------------------------------------------- render

    def _render_summary(self) -> None:
        self._summary_host.content = self._build_summary()

    def _build_summary(self) -> ft.Control:
        rated = [comment for comment in self._comments if comment.stars > 0]
        average = sum(comment.stars for comment in rated) / len(rated) if rated else 0

        rating_column: List[ft.Control] = [
            ft.Text("平均評分", size=13, color=ft.Colors.OUTLINE)
        ]
        if rated:
            rating_column.append(
                ft.Row(
                    [
                        ft.Text(f"{average:.1f}", size=22, weight=ft.FontWeight.BOLD),
                        build_stars(round(average), size=18),
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        else:
            rating_column.append(ft.Text("未有評分", size=14, color=ft.Colors.OUTLINE))

        return ft.Row(
            [
                ft.Column(rating_column, spacing=2),
                ft.Text(
                    f"{len(self._comments)} 則評論",
                    size=13,
                    color=ft.Colors.OUTLINE,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_card(self, comment: Comment, profile) -> ft.Control:
        name = (profile.name if profile and profile.name else "") or ANONYMOUS_NAME
        avatar_url = (
            self._cache_image(profile.avatar_url)
            if profile and profile.avatar_url
            else ""
        )

        meta = comment.local_created_at.strftime("%Y-%m-%d %H:%M")
        if comment.edited:
            meta += " (已編輯)"

        details: List[ft.Control] = [
            ft.Row(
                [
                    ft.Text(
                        name,
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        expand=True,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Text(meta, size=11, color=ft.Colors.OUTLINE),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            build_stars(comment.stars, size=14),
        ]
        if comment.content:
            details.append(ft.Text(comment.content, size=14))

        return ft.Card(
            content=ft.Container(
                content=ft.Row(
                    [
                        build_avatar(avatar_url, radius=18),
                        ft.Column(details, spacing=4, expand=True),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=12,
            )
        )

    def _refresh(self) -> None:
        try:
            self.page.update()
        except Exception:
            logger.debug("Comment section closed before it could be refreshed")
