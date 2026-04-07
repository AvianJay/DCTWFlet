
import asyncio
import flet as ft
import re
from typing import Optional
from application.services import DiscoveryService
from domain.discovery.entities import Server
from domain.shared import EntityNotFoundException
from infrastructure.di import get_container
from infrastructure.image import ImageServer
from presentation.tag_mappings import SERVER_TAGS


class ServerDetailPage:
    """Server detail page"""

    def __init__(self, page: ft.Page, server_id: str):
        self._content_container = None
        self.page = page
        self.server_id = server_id
        self.container = get_container()
        self.discovery_service: DiscoveryService = self.container.resolve(
            DiscoveryService
        )
        self.image_server: ImageServer = self.container.resolve(ImageServer)
        self._server: Optional[Server] = None

    def _get_tag_info(self, tag_name: str) -> tuple[str, str]:
        """Get tag display name and icon"""
        return SERVER_TAGS.get(tag_name, (tag_name, ft.Icons.TAG))

    def _cache_image(self, url: str) -> str:
        """Cache image and return local URL"""
        if not url:
            return ""
        image_id = self.image_server.register_image(url)
        return self.image_server.get_image_url(image_id)

    def _convert_discord_emojis(self, text: str) -> str:
        if not text:
            return ""

        # Replace animated emojis <a:name:id>
        text = re.sub(
            r"<a:\w*:(\d+)>",
            r"![emoji](https://cdn.discordapp.com/emojis/\1.gif?size=32&quality=lossless)",
            text,
        )

        # Replace static emojis <:name:id>
        text = re.sub(
            r"<:\w*:(\d+)>",
            r"![emoji](https://cdn.discordapp.com/emojis/\1.png?size=32&quality=lossless)",
            text,
        )
        return text

    def build(self) -> ft.Control:
        """Build page UI"""
        self._content_container = ft.Container(
            expand=True,
            alignment=ft.Alignment(0, 0),
        )

        self._content_container.content = ft.Column(
            [
                ft.ProgressRing(),
                ft.Text("載入中...", size=16, text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )

        self.page.run_task(self._load_server_data)

        return self._content_container

    async def _load_server_data(self):
        """Load server data asynchronously"""
        try:
            server_id_int = int(self.server_id)
            self._server = await self.discovery_service.get_server_by_id(server_id_int)
            self._render_server_detail()

        except EntityNotFoundException:
            self._show_error(f"找不到此伺服器 (ID: {self.server_id})")
        except ValueError:
            self._show_error(f"無效的伺服器 ID: {self.server_id}")
        except Exception as e:
            self._show_error(f"載入失敗: {str(e)}")

    def _render_server_detail(self):
        """Render server detail UI"""
        if not self._server:
            return

        server = self._server

        detail_view = ft.Column(
            [
                # Banner and Icon
                self._create_header_section(server),
                # Name
                ft.Row(
                    [
                        ft.Text(
                            server.name,
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # Badges (Partner)
                self._create_badges_section(server),
                # Description
                ft.Container(
                    content=ft.Text(
                        server.description,
                        size=16,
                        weight=ft.FontWeight.NORMAL,
                        text_align=ft.TextAlign.CENTER,
                        no_wrap=False,
                    ),
                    alignment=ft.Alignment(0, 0),
                    padding=ft.padding.symmetric(horizontal=20),
                ),
                # Tags
                self._create_tags_section(server),
                # Action buttons
                self._create_action_buttons(server),
                # Introduction (Markdown)
                ft.Container(
                    content=ft.Markdown(
                        self._convert_discord_emojis(server.introduce),
                        fit_content=False,
                        on_tap_link=lambda e: self.page.launch_url(e.data),
                    ),
                    padding=ft.padding.all(20),
                ),
                # DCTW page link
                ft.Row(
                    [
                        ft.ElevatedButton(
                            content=ft.Text("DCTW 伺服器頁面"),
                            icon=ft.Icons.OPEN_IN_NEW,
                            on_click=lambda e: self.page.launch_url(
                                f"https://dctw.xyz/servers/{server.id}"
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=20),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self._content_container.content = detail_view
        self.page.update()

    def _create_header_section(self, server: Server) -> ft.Control:
        """Create header section with banner and icon"""
        banner_url = self._cache_image(server.banner.value) if server.banner else ""
        icon_url = self._cache_image(server.icon.value)

        if banner_url:
            banner_content = ft.Image(
                src=banner_url,
                fit=ft.ImageFit.COVER,
                width=float("inf"),
                error_content=ft.Container(bgcolor=ft.Colors.SURFACE),
            )
        else:
            banner_content = ft.Container(bgcolor=ft.Colors.SURFACE)

        return ft.Stack(
            [
                ft.Container(
                    content=banner_content,
                    height=256,
                    expand=True,
                ),
                ft.Container(
                    content=ft.CircleAvatar(
                        foreground_image_src=icon_url,
                        radius=64,
                    ),
                    alignment=ft.Alignment(0, 1),
                    margin=ft.margin.only(top=128),
                ),
            ],
            height=256 + 64,
        )

    def _create_badges_section(self, server: Server) -> ft.Control:
        """Create badges section"""
        if not server.is_partnered:
            return ft.Container(height=0)

        return ft.Row(
            [
                ft.ElevatedButton(
                    content=ft.Text("DCTW 合作夥伴"),
                    color=ft.Colors.WHITE,
                    icon=ft.Icons.STAR,
                    icon_color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.GREEN,
                    on_click=lambda e: self.page.open(
                        ft.SnackBar(content=ft.Text("此伺服器為 DCTW 合作夥伴。"))
                    ),
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _create_tags_section(self, server: Server) -> ft.Control:
        """Create tags section"""
        tag_buttons = []
        for tag in server.tags:
            display_name, icon = self._get_tag_info(tag.name)
            tag_buttons.append(ft.ElevatedButton(content=ft.Text(display_name), icon=icon))

        if not tag_buttons:
            return ft.Container(height=0)

        return ft.Container(
            content=ft.Row(
                tag_buttons,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                wrap=True,
            ),
            alignment=ft.Alignment(0, 0),
            padding=ft.padding.symmetric(horizontal=20),
        )

    def _create_action_buttons(self, server: Server) -> ft.Control:
        """Create action buttons"""
        return ft.Container(
            content=ft.Row(
                [
                    ft.ElevatedButton(
                        icon=ft.Icons.ADD,
                        content=ft.Text("加入伺服器"),
                        on_click=lambda e: self.page.launch_url(server.links.invite.value),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                wrap=True,
            ),
            alignment=ft.Alignment(0, 0),
            padding=ft.padding.symmetric(horizontal=20),
        )

    def _show_error(self, message: str):
        """Show error message"""
        error_view = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.ERROR_OUTLINE, size=64, color=ft.Colors.ERROR),
                    ft.Text(message, size=18, text_align=ft.TextAlign.CENTER),
                    ft.ElevatedButton(
                        content=ft.Text("返回"),
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda e: asyncio.create_task(self.page.push_route("/")),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20,
            ),
            alignment=ft.Alignment(0, 0),
            expand=True,
            padding=ft.padding.all(40),
        )

        self._content_container.content = error_view
        self.page.update()
