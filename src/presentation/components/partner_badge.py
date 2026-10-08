"""The "DCTW 合作夥伴" pill shown for partnered items.

Mirrors the badge rendered by the official website: the DCTW icon and the
label on a light pill, instead of a coloured icon.
"""

import flet as ft

# Marker used by the lists to recognise a pill that is already on screen.
PARTNER_BADGE_TAG = "dctw-partner-badge"


def build_partner_badge(tooltip: str = "DCTW 合作夥伴") -> ft.Control:
    """Build the white partner pill used on the cards and detail pages."""
    return ft.Container(
        content=ft.Row(
            [
                ft.Image(
                    src="icon.png",
                    width=14,
                    height=14,
                    fit=ft.BoxFit.CONTAIN,
                ),
                ft.Text(
                    "DCTW 合作夥伴",
                    size=10,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.SURFACE,
                ),
            ],
            spacing=5,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.ON_SURFACE,
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=7, vertical=2),
        tooltip=tooltip,
        data=PARTNER_BADGE_TAG,
    )
