"""Settings page

Manage user preferences
"""

import flet as ft
import asyncio

from application.services import PreferenceService
from domain.preferences.value_objects import Theme, UpdateCheck
from infrastructure.di import get_container

from application.services import DiscoveryService


class SettingsPage:
    """Settings page"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.container = get_container()
        self.pref_service: PreferenceService = self.container.resolve(PreferenceService)

        # UI組件
        self.theme_dropdown = ft.Dropdown(
            label="主題",
            options=[
                ft.dropdown.Option("system", "跟隨系統"),
                ft.dropdown.Option("light", "淺色"),
                ft.dropdown.Option("dark", "深色"),
            ],
            on_change=lambda e: self.page.run_task(self._on_theme_changed, e),
        )

        self.nsfw_switch = ft.Switch(
            label="顯示NSFW內容",
            on_change=lambda e: self.page.run_task(self._on_nsfw_changed, e),
        )

        self.api_key_field = ft.TextField(
            label="API密鑰",
            password=True,
            can_reveal_password=True,
        )

        self.update_check_dropdown = ft.Dropdown(
            label="更新檢查",
            options=[
                ft.dropdown.Option("popup", "彈窗提示"),
                ft.dropdown.Option("notify", "通知欄提示"),
                ft.dropdown.Option("none", "不檢查"),
            ],
            on_change=lambda e: self.page.run_task(self._on_update_check_changed, e),
        )

    def build(self) -> ft.Control:
        """Build page UI"""
        # Load current settings
        self.page.run_task(self._load_preferences)

        return ft.Column(
            [
                # Title bar
                ft.Container(
                    content=ft.Text("設置", size=24, weight=ft.FontWeight.BOLD),
                    bgcolor=ft.Colors.SURFACE,
                    padding=15,
                ),
                # Settings items
                ft.Container(
                    content=ft.Column(
                        [
                            # Appearance settings
                            ft.Text("外觀", size=18, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            self.theme_dropdown,
                            ft.Container(height=20),
                            # Content settings
                            ft.Text("內容", size=18, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            self.nsfw_switch,
                            ft.Container(height=20),
                            # API設置
                            ft.Text("API設置", size=18, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            self.api_key_field,
                            ft.OutlinedButton(
                                "Save API key",
                                icon=ft.Icons.SAVE,
                                on_click=lambda _: self.page.run_task(
                                    self._save_api_key
                                ),
                            ),
                            ft.Container(height=20),
                            # Update settings
                            ft.Text("更新", size=18, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            self.update_check_dropdown,
                            ft.Container(height=20),
                            # Cache management
                            ft.Text("緩存", size=18, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            ft.OutlinedButton(
                                "清除所有緩存",
                                icon=ft.Icons.DELETE_SWEEP,
                                on_click=lambda _: self.page.run_task(
                                    self._clear_cache
                                ),
                            ),
                        ],
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    padding=ft.padding.only(left=20, right=20, top=20, bottom=10),
                    expand=True,
                ),
            ],
            expand=True,
        )

    async def _load_preferences(self):
        """Load current settings"""
        try:
            prefs = await self.pref_service.load_preferences()

            # Update UI
            self.theme_dropdown.value = prefs.theme.value
            self.nsfw_switch.value = prefs.nsfw_filter.is_enabled
            self.api_key_field.value = prefs.api_key.value or ""
            self.update_check_dropdown.value = prefs.update_check.value

            self.page.update()

        except Exception as e:
            print(f"Error loading preferences: {e}")
            self._show_error(f"載入設置失敗: {str(e)}")

    async def _on_theme_changed(self, e):
        """Theme changed event"""
        try:
            theme = Theme.from_string(e.control.value)
            await self.pref_service.change_theme(theme)

            # Apply theme immediately
            self.page.theme_mode = theme.value
            self.page.update()

            self._show_success("主題已更改")

        except Exception as ex:
            print(f"Error changing theme: {ex}")
            self._show_error(f"更改主題失敗: {str(ex)}")

    async def _on_nsfw_changed(self, e):
        """NSFW filter change event handler"""
        try:
            enabled = e.control.value
            await self.pref_service.set_nsfw(enabled)

            status = "已啟用" if enabled else "已禁用"
            self._show_success(f"NSFW過濾{status}")

        except Exception as ex:
            print(f"Error toggling NSFW: {ex}")
            self._show_error(f"更改NSFW設置失敗: {str(ex)}")

    async def _on_update_check_changed(self, e):
        """Update check change event handler"""
        try:
            update_check = UpdateCheck.from_string(e.control.value)
            await self.pref_service.change_update_check(update_check)

            self._show_success("更新檢查設置已更改")

        except Exception as ex:
            print(f"Error changing update check: {ex}")
            self._show_error(f"更改更新設置失敗: {str(ex)}")

    async def _save_api_key(self):
        """Save API key"""
        try:
            api_key = self.api_key_field.value
            await self.pref_service.update_api_key(api_key)

            self._show_success("API密鑰已保存")

        except Exception as e:
            print(f"Error saving API key: {e}")
            self._show_error(f"Save API key失敗: {str(e)}")

    async def _clear_cache(self):
        """Clear cache"""
        try:

            discovery_service = self.container.resolve(DiscoveryService)
            await discovery_service.clear_all_caches()

            self._show_success("緩存已清除")

        except Exception as e:
            print(f"Error clearing cache: {e}")
            self._show_error(f"Clear cache失敗: {str(e)}")

    def _show_success(self, message: str):
        """Show success message"""
        snack = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.GREEN,
        )
        self.page.snack_bar = snack
        snack.open = True
        self.page.update()

    def _show_error(self, message: str):
        """Show error message"""
        snack = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.ERROR,
        )
        self.page.snack_bar = snack
        snack.open = True
        self.page.update()
