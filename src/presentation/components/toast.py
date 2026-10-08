"""Small transient message box shown at the bottom of the page."""

import asyncio
import logging
from typing import Optional

import flet as ft

logger = logging.getLogger(__name__)

DEFAULT_DURATION = 2.5
DEFAULT_BOTTOM_MARGIN = 96


class Toast:
    """Shows a small message box at the bottom of the page for a few seconds."""

    def __init__(
        self,
        page: ft.Page,
        duration: float = DEFAULT_DURATION,
        bottom: int = DEFAULT_BOTTOM_MARGIN,
    ):
        self.page = page
        self.duration = duration
        self.bottom = bottom
        # Every display owns its controls and the task that shows them, so a
        # task that is replaced by a newer message can only remove the box it
        # created itself.
        self._task = None
        self._host: Optional[ft.Container] = None

    def show(self, message: str, duration: Optional[float] = None) -> None:
        """Display a message and hide it again after a few seconds."""
        self._cancel_previous()
        self._task = self.page.run_task(
            self._show, message, duration or self.duration
        )

    def _cancel_previous(self) -> None:
        """Stop the message that is currently on screen (if any)."""
        task = self._task
        self._task = None
        if task is None or task.done():
            return

        try:
            task.cancel()
        except Exception:
            logger.exception("Failed to cancel the previous toast message")

    async def _show(self, message: str, duration: float) -> None:
        box = ft.Container(
            content=ft.Text(
                message,
                size=13,
                color=ft.Colors.ON_SURFACE,
                text_align=ft.TextAlign.CENTER,
            ),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            padding=ft.padding.symmetric(horizontal=16, vertical=9),
            border_radius=20,
            shadow=ft.BoxShadow(
                blur_radius=10,
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
            ),
            opacity=0,
            animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )

        host = ft.Container(
            content=box,
            left=0,
            right=0,
            bottom=self.bottom,
            alignment=ft.Alignment(0, 0),
            ignore_interactions=True,
        )
        self._host = host

        try:
            self.page.overlay.append(host)
            self.page.update()

            await asyncio.sleep(0.05)
            box.opacity = 1
            self.page.update()

            await asyncio.sleep(duration)

            box.opacity = 0
            self.page.update()
            await asyncio.sleep(0.25)
        except Exception:
            logger.exception("Failed to show toast message")
        finally:
            self._remove(host)

    def _remove(self, host: Optional[ft.Container]) -> None:
        """Remove one message box; a newer display keeps its own box."""
        if host is None:
            return

        try:
            if host in self.page.overlay:
                self.page.overlay.remove(host)
        except Exception:
            logger.exception("Failed to remove toast message")

        if self._host is host:
            self._host = None

        try:
            self.page.update()
        except Exception:
            pass
