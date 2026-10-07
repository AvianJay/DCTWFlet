"""Social links section shared by the bot and server detail pages.

The official website renders one rounded icon button per platform
(Line, Facebook, Instagram, Twitch, Threads, X) and falls back to a
generic link icon for platforms without a dedicated picture.
"""

from typing import Callable, Dict, Optional

import flet as ft

from presentation.url_helper import open_url

SOCIAL_ICON_URLS: Dict[str, str] = {
    "Line": "https://cdn-icons-png.flaticon.com/128/2504/2504922.png",
    "Facebook": "https://cdn-icons-png.flaticon.com/128/2504/2504903.png",
    "Instagram": "https://cdn-icons-png.flaticon.com/128/2111/2111463.png",
    "Twitch": "https://cdn-icons-png.flaticon.com/128/2504/2504946.png",
    "Threads": "https://cdn-icons-png.flaticon.com/128/12105/12105338.png",
    "X": "https://cdn-icons-png.flaticon.com/128/5969/5969020.png",
}

FALLBACK_SOCIAL_ICON_URL = (
    "https://cdn-icons-png.flaticon.com/128/1011/1011322.png"
)


def build_social_links_section(
    page: ft.Page,
    social_links: Optional[Dict[str, str]],
    cache_image: Callable[[str], str],
    title: str = "社群連結",
) -> Optional[ft.Control]:
    """Build the social links block shown on the official detail pages.

    Returns ``None`` when the item has no usable link so callers can skip
    the whole section.
    """
    links = {
        platform: url
        for platform, url in (social_links or {}).items()
        if isinstance(url, str) and url.startswith(("http://", "https://"))
    }
    if not links:
        return None

    buttons = []
    for platform, url in links.items():
        icon_url = cache_image(
            SOCIAL_ICON_URLS.get(platform, FALLBACK_SOCIAL_ICON_URL)
        )
        buttons.append(
            ft.Container(
                content=ft.Image(
                    src=icon_url,
                    width=22,
                    height=22,
                    fit=ft.BoxFit.CONTAIN,
                    error_content=ft.Icon(ft.Icons.LINK, size=22),
                ),
                width=44,
                height=44,
                bgcolor=ft.Colors.SECONDARY_CONTAINER,
                border_radius=12,
                alignment=ft.Alignment(0, 0),
                ink=True,
                tooltip=platform,
                on_click=lambda e, target=url: open_url(page, target),
            )
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
                ft.Row(
                    buttons,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12,
                    run_spacing=12,
                    wrap=True,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
        alignment=ft.Alignment(0, 0),
        padding=ft.padding.symmetric(horizontal=20, vertical=8),
    )
