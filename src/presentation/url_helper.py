"""Helpers for opening external links from control event handlers."""

import logging
from typing import Any, Optional

import flet as ft

logger = logging.getLogger(__name__)

_launchers: dict[int, ft.UrlLauncher] = {}


def open_url(page: ft.Page, url: Optional[Any]) -> None:
    """Open ``url`` in the system browser.

    ``Page.launch_url`` is a coroutine, so calling it directly from a click
    handler never runs it. This helper schedules the call on the page event
    loop and keeps a reusable :class:`flet.UrlLauncher` service around.
    """
    target = _as_text(url)
    if not target:
        return

    page.run_task(_launch, _launcher_for(page), target)


def _as_text(url: Optional[Any]) -> str:
    """Normalize a URL that may be a plain string or a value object."""
    if url is None:
        return ""

    value = getattr(url, "value", url)
    return str(value).strip() if value else ""


def _launcher_for(page: ft.Page) -> ft.UrlLauncher:
    launcher = _launchers.get(id(page))
    if launcher is not None:
        return launcher

    launcher = ft.UrlLauncher()
    try:
        launcher.page
    except RuntimeError:
        # Not auto-registered (created outside a Flet callback): attach it.
        try:
            page.services.append(launcher)
        except Exception:
            logger.exception("Failed to attach UrlLauncher to the page")

    _launchers[id(page)] = launcher
    return launcher


async def _launch(launcher: ft.UrlLauncher, url: str) -> None:
    try:
        await launcher.launch_url(url)
    except Exception:
        logger.exception("Failed to open URL: %s", url)
