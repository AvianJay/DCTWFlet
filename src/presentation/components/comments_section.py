"""Comments ("使用者評論") section shared by the detail pages.

The API embeds the reviews in the item itself, so the detail pages hand the
parsed list to this component, which resolves the reviewer names and avatars
through the same website action the official page uses.
"""

import logging
from typing import Awaitable, Callable, Dict, List, Sequence

import flet as ft

from domain.discovery.entities import UserProfile
from domain.discovery.value_objects import Comment
from presentation.components.avatar_image import build_avatar

logger = logging.getLogger(__name__)

STAR_COLOR = ft.Colors.AMBER


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
    """Reusable review list of the bot, server and template detail pages."""

    def __init__(
        self,
        page: ft.Page,
        comments: Sequence[Comment],
        load_profiles: Callable[
            [List[str]], Awaitable[List[UserProfile]]
        ],
        cache_image: Callable[[str], str],
        title: str = "使用者評論",
        loading: bool = False,
    ) -> None:
        self.page = page
        self._comments = list(comments or [])
        self._load_profiles = load_profiles
        self._cache_image = cache_image
        self._title = title
        self._loading = loading
        self._body = ft.Column(spacing=10)

    def build(self) -> ft.Control:
        """Build the section; the reviewer names load in the background."""
        if self._comments or self._loading:
            self._begin_loading()
        else:
            self._body.controls = [
                ft.Text("目前沒有評論", size=14, color=ft.Colors.OUTLINE)
            ]

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(self._title, size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    self._build_summary(),
                    self._body,
                ],
                spacing=10,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=8),
        )

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

        try:
            self._body.controls = [
                self._build_card(comment, profiles.get(comment.user_id))
                for comment in self._comments
            ]
            self._body.update()
        except Exception:
            logger.debug("Comment section closed before the profiles arrived")

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
        name = (profile.name if profile and profile.name else "") or "訪客"
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

