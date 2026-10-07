"""Multi-select tag filter dialog.

The list pages show a funnel icon in the top-right corner. Tapping it opens
this dialog, which lists every official tag as a checkbox so the user can
pick several tags at once on a phone. The selection is applied only after
pressing 確認.
"""

import logging
from typing import Callable, Dict, Iterable, Mapping, Optional, Sequence, Set, Tuple

import flet as ft

logger = logging.getLogger(__name__)

TagInfo = Tuple[str, object]  # (label, icon)


class TagFilterDialog:
    """Reusable multi-select tag picker shown inside an AlertDialog."""

    def __init__(
        self,
        page: ft.Page,
        title: str,
        tags: Mapping[str, TagInfo],
        order: Sequence[str],
        selected: Iterable[str],
        on_apply: Callable[[Set[str]], None],
    ) -> None:
        self.page = page
        self._title = title
        self._tags = tags
        self._order = [name for name in order if name in tags]
        self._selected: Set[str] = {name for name in selected if name in tags}
        self._on_apply = on_apply
        self._boxes: Dict[str, ft.Checkbox] = {}
        self._count = ft.Text(size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self._dialog: Optional[ft.AlertDialog] = None

    # ------------------------------------------------------------------ UI

    def show(self) -> None:
        """Open the dialog with the current selection pre-checked."""
        self._refresh_count()
        self._dialog = ft.AlertDialog(
            modal=True,
            scrollable=True,
            title=ft.Text(self._title, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [self._count]
                + [self._build_row(name) for name in self._order],
                tight=True,
                spacing=0,
                width=320,
            ),
            actions=[
                ft.TextButton("清除", on_click=self._clear),
                ft.TextButton("取消", on_click=lambda _: self._close()),
                ft.FilledButton("確認", on_click=self._confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(self._dialog)

    def _build_row(self, name: str) -> ft.Control:
        label, icon = self._tags[name]
        box = ft.Checkbox(
            value=name in self._selected,
            visual_density=ft.VisualDensity.COMPACT,
            on_change=lambda e, tag=name: self._on_box_change(
                tag, bool(e.control.value)
            ),
        )
        self._boxes[name] = box
        return ft.Container(
            content=ft.Row(
                [
                    box,
                    ft.Icon(icon, size=18, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(label, size=14),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=6, vertical=0),
            border_radius=10,
            ink=True,
            on_click=lambda _, tag=name: self._toggle(tag),
        )

    # -------------------------------------------------------------- events

    def _on_box_change(self, name: str, checked: bool) -> None:
        if checked:
            self._selected.add(name)
        else:
            self._selected.discard(name)
        self._refresh_count()

    def _toggle(self, name: str) -> None:
        """Row tap: flip the checkbox and keep the selection in sync."""
        box = self._boxes[name]
        box.value = not bool(box.value)
        if box.value:
            self._selected.add(name)
        else:
            self._selected.discard(name)
        box.update()
        self._refresh_count()

    def _clear(self, _e=None) -> None:
        self._selected.clear()
        for box in self._boxes.values():
            box.value = False
            box.update()
        self._refresh_count()

    def _confirm(self, _e=None) -> None:
        selection = set(self._selected)
        self._close()
        try:
            self._on_apply(selection)
        except Exception:
            logger.exception("Applying the tag filter failed")

    def _close(self) -> None:
        try:
            self.page.pop_dialog()
        except Exception:
            logger.exception("Failed to close the tag filter dialog")

    def _refresh_count(self) -> None:
        count = len(self._selected)
        self._count.value = f"已選 {count} 個標籤" if count else "尚未選擇標籤"
        if self._dialog is None:
            return
        try:
            self._count.update()
        except Exception:
            logger.debug("Tag counter is not mounted yet")
