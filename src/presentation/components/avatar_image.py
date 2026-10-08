"""Avatar rendering helper.

The official website draws each icon directly inside a circle, so icons that
come without a background (transparent PNGs) blend with the card behind them.
This helper does the same: no picture is stacked behind the icon, a missing or
broken image falls back to the DCTW placeholder icon.
"""

import logging
from typing import Optional

import flet as ft

from infrastructure.config.constants import DEFAULT_AVATAR_URL

logger = logging.getLogger(__name__)

# Placeholder used by the website for items without a usable icon.
PLACEHOLDER_AVATAR_URL = "https://dctw.xyz/default-icon.png"


def build_avatar(
    src: Optional[str],
    radius: int = 25,
    bgcolor=ft.Colors.TRANSPARENT,
) -> ft.CircleAvatar:
    """Return a circular avatar that renders like the official website."""
    fallback = PLACEHOLDER_AVATAR_URL or DEFAULT_AVATAR_URL
    url = (src or "").strip() or fallback

    avatar = ft.CircleAvatar(
        foreground_image_src=url,
        bgcolor=bgcolor,
        radius=radius,
    )

    def handle_image_error(_e) -> None:
        if avatar.foreground_image_src == fallback:
            return
        avatar.foreground_image_src = fallback
        try:
            avatar.update()
        except Exception:
            logger.debug("Avatar is not mounted yet")

    avatar.on_image_error = handle_image_error
    return avatar