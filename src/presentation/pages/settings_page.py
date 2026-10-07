"""Settings page

Manage user preferences
"""

import flet as ft
import asyncio

from application.services import PreferenceService
from domain.preferences.value_objects import Theme, UpdateCheck
from infrastructure.api import DctwApiClient
from infrastructure.di import get_container

from application.services import DiscoveryService
from presentation.components import ApiKeyDialog, Toast


class SettingsPage:
    """Settings page"""

    def __init__(self, page: ft.Page, on_data_changed=None):
        self.page = page
        self._on_data_changed = on_data_changed
        self.container = get_container()
        self.pref_service: PreferenceService = self.container.resolve(PreferenceService)
        self.discovery_service: DiscoveryService = self.container.resolve(
            DiscoveryService
        )
        self.api_client: DctwApiClient = self.container.resolve(DctwApiClient)
        self.toast = Toast(self.page)

        # UI組件
        self.theme_dropdown = ft.Dropdown(
            label="主題",
            options=[
                ft.dropdown.Option("system", "跟隨系統"),
                ft.dropdown.Option("light", "淺色"),
                ft.dropdown.Option("dark", "深色"),
            ],
            on_select=lambda e: self.page.run_task(self._on_theme_changed, e),
        )

        self.nsfw_switch = ft.Switch(
            label="顯示NSFW內容",
            on_change=lambda e: self.page.run_task(self._on_nsfw_changed, e),
        )

        self.api_key_field = ft.TextField(
            label="API金鑰",
            password=True,
            can_reveal_password=True,
        )

        self.api_key_status = ft.Text(
            "尚未設定 API Key",
            size=13,
            color=ft.Colors.ORANGE,
        )

        self.update_check_dropdown = ft.Dropdown(
            label="更新檢查",
            options=[
                ft.dropdown.Option("popup", "彈窗提示"),
                ft.dropdown.Option("notify", "通知欄提示"),
                ft.dropdown.Option("none", "不檢查"),
            ],
            on_select=lambda e: self.page.run_task(self._on_update_check_changed, e),
        )

    def build(self) -> ft.Control:
        """Build page UI"""
        # Load current settings
        self.page.run_task(self._load_preferences)

        return ft.Column(
            [
                # Title bar (same style as the bot/server/template list headers)
                ft.AppBar(
                    title=ft.Text("應用程式設定"),
                    center_title=False,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
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
                            self.api_key_status,
                            ft.FilledButton(
                                "從剪貼簿貼上 API Key",
                                icon=ft.Icons.CONTENT_PASTE,
                                on_click=lambda _: self._open_api_key_dialog(),
                            ),
                            ft.Text(
                                "瀏覽機器人、伺服器與模板不需要 API Key，投票時才需要。"
                                "請先到 DCTW 官網登入並在後台複製 API KEY，再點擊上方按鈕貼上。",
                                size=12,
                                color=ft.Colors.GREY,
                            ),
                            self.api_key_field,
                            ft.Row(
                                [
                                    ft.OutlinedButton(
                                        "驗證並儲存",
                                        icon=ft.Icons.SAVE,
                                        on_click=lambda _: self.page.run_task(
                                            self._save_api_key
                                        ),
                                    ),
                                    ft.TextButton(
                                        "清除 API Key",
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        on_click=lambda _: self.page.run_task(
                                            self._clear_api_key
                                        ),
                                    ),
                                ],
                                spacing=10,
                                wrap=True,
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
            self._update_api_key_status(prefs.api_key)

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

    def _update_api_key_status(self, api_key) -> None:
        """Update the API key status label"""
        if api_key and api_key.is_set:
            self.api_key_status.value = f"已設定 API Key：{api_key}"
            self.api_key_status.color = ft.Colors.GREEN
        else:
            self.api_key_status.value = "尚未設定 API Key（投票時需要）"
            self.api_key_status.color = ft.Colors.ORANGE

    def _open_api_key_dialog(self):
        """Open the dialog that fills in the API key from the clipboard"""
        dialog = ApiKeyDialog(
            page=self.page,
            preference_service=self.pref_service,
            discovery_service=self.discovery_service,
            api_client=self.api_client,
            on_saved=self._on_api_key_saved,
        )
        dialog.show()

    def _on_api_key_saved(self):
        """Called after the API key dialog stores a new key"""
        self.page.run_task(self._after_api_key_saved)

    async def _after_api_key_saved(self):
        await self._load_preferences()
        self._notify_data_changed()
        self._show_success("API Key 已儲存，資料將重新載入")

    async def _save_api_key(self):
        """Validate and save the manually entered API key"""
        try:
            api_key = (self.api_key_field.value or "").strip()
            if not api_key:
                self._show_error("請輸入 API Key")
                return

            is_valid = await self.api_client.validate_api_key(api_key)
            if not is_valid:
                self._show_error("API Key 無效，請確認後再試")
                return

            await self.pref_service.update_api_key(api_key)
            await self.discovery_service.clear_all_caches()
            await self._load_preferences()
            self._notify_data_changed()

            self._show_success("API Key 已儲存，資料將重新載入")

        except Exception as e:
            print(f"Error saving API key: {e}")
            self._show_error(f"儲存 API Key 失敗: {str(e)}")

    async def _clear_api_key(self):
        """Remove the stored API key"""
        try:
            await self.pref_service.update_api_key("")
            await self.discovery_service.clear_all_caches()
            await self._load_preferences()
            self._notify_data_changed()

            self._show_success("API Key 已清除")

        except Exception as e:
            print(f"Error clearing API key: {e}")
            self._show_error(f"清除 API Key 失敗: {str(e)}")

    async def _clear_cache(self):
        """Clear cache"""
        try:
            await self.discovery_service.clear_all_caches()

            self._show_success("緩存已清除")

        except Exception as e:
            print(f"Error clearing cache: {e}")
            self._show_error(f"Clear cache失敗: {str(e)}")

    def _show_success(self, message: str):
        """Show a small message at the bottom of the page"""
        self.toast.show(message)

    def _notify_data_changed(self) -> None:
        """Tell the shell that the cached data tabs have to be rebuilt."""
        if self._on_data_changed is None:
            return
        try:
            self._on_data_changed()
        except Exception as ex:
            print(f"Error reloading data tabs: {ex}")

    def _show_error(self, message: str):
        """Show error message"""
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message),
                bgcolor=ft.Colors.ERROR,
            )
        )
