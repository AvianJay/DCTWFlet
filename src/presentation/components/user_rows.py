"""Discord user blocks shared by the detail pages.

Bot and template authors are shown as a compact "作者 <avatars> <names>" row
right under the title, exactly like the official page. Server admins get a
card list with the job they were given on DCTW.
"""

from typing import Callable, List, Sequence

import flet as ft

from domain.discovery.entities import ServerAdmin, UserProfile
from presentation.components.avatar_image import build_avatar


def build_user_row(
    label: str,
    profiles: Sequence[UserProfile],
    cache_image: Callable[[str], str],
    max_avatars: int = 3,
    max_name_length: int = 24,
) -> ft.Control:
    """Build the small avatar + name row shown under a detail page title."""
    if not profiles:
        return ft.Container(height=0)

    avatars = [
        build_avatar(
            cache_image(profile.avatar_url) if profile.avatar_url else "",
            radius=12,
        )
        for profile in profiles[:max_avatars]
    ]
    names = "、".join(profile.name for profile in profiles if profile.name)
    if not names:
        return ft.Container(height=0)

    if len(names) > max_name_length:
        names = names[: max_name_length - 1] + "\u2026"

    controls: List[ft.Control] = [
        ft.Text(label, size=12, color=ft.Colors.OUTLINE)
    ]
    controls.extend(avatars)
    controls.append(
        ft.Text(
            names,
            size=13,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.OUTLINE,
        )
    )

    return ft.Container(
        content=ft.Row(
            controls,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        ),
        alignment=ft.Alignment(0, 0),
        padding=ft.padding.symmetric(horizontal=20),
    )


def build_admin_section(
    admins: Sequence[ServerAdmin],
    profiles: Sequence[UserProfile],
    cache_image: Callable[[str], str],
    title: str = "管理人員",
) -> ft.Control:
    """Build the admin list of the official server page."""
    if not admins:
        return ft.Container(height=0)

    by_id = {profile.id: profile for profile in profiles}
    cards: List[ft.Control] = []
    for admin in admins:
        profile = by_id.get(admin.id)
        name = (profile.name if profile and profile.name else "") or "未知"
        avatar_url = (
            cache_image(profile.avatar_url)
            if profile and profile.avatar_url
            else ""
        )

        details: List[ft.Control] = [
            ft.Text(name, size=14, weight=ft.FontWeight.BOLD)
        ]
        if admin.job:
            details.append(ft.Text(admin.job, size=12, color=ft.Colors.OUTLINE))

        cards.append(
            ft.Card(
                content=ft.Container(
                    content=ft.Row(
                        [
                            build_avatar(avatar_url, radius=18),
                            ft.Column(details, spacing=2, expand=True),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=12,
                )
            )
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Column(cards, spacing=10),
            ],
            spacing=10,
        ),
        padding=ft.padding.symmetric(horizontal=20, vertical=8),
    )

