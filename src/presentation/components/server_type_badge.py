"""The server type pill shown on the server cards.

Mirrors the badge rendered by the official website: DISCOVERABLE servers get a
yellow "探索伺服器" pill with a star, COMMUNITY servers a violet
"社群伺服器" pill with a globe and everything else a grey
"私人伺服器" pill with a people icon.
"""

from typing import List, Optional

import flet as ft

# Marker used by the lists to recognise a pill that is already on screen.
SERVER_TYPE_BADGE_TAG = "dctw-server-type-badge"

# Tailwind colours used by the website (yellow-500 / violet-500); the private
# pill sits between the gray-400 (light) and gray-600 (dark) of the site so it
# stays readable on both app themes.
DISCOVERABLE_COLOR = "#EAB308"
COMMUNITY_COLOR = "#8B5CF6"
PRIVATE_COLOR = "#6B7280"


def build_server_type_badge(features: Optional[List[str]] = None) -> ft.Control:
    """Build the server type pill (探索 / 社群 / 私人伺服器)."""
    values = {str(feature).strip().upper() for feature in features or []}
    if "DISCOVERABLE" in values:
        label, icon, bgcolor = (
            "探索伺服器",
            ft.Icons.STAR_BORDER,
            DISCOVERABLE_COLOR,
        )
    elif "COMMUNITY" in values:
        label, icon, bgcolor = (
            "社群伺服器",
            ft.Icons.PUBLIC,
            COMMUNITY_COLOR,
        )
    else:
        label, icon, bgcolor = (
            "私人伺服器",
            ft.Icons.GROUP,
            PRIVATE_COLOR,
        )

    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(icon, size=12, color=ft.Colors.WHITE),
                ft.Text(
                    label,
                    size=10,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                ),
            ],
            spacing=4,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=bgcolor,
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=6, vertical=2),
        tooltip=label,
        data=SERVER_TYPE_BADGE_TAG,
    )
