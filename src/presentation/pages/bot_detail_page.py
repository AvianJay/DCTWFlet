import flet as ft
import re
from typing import Optional
from application.services import DiscoveryService
from domain.discovery.entities import Bot
from domain.shared import EntityNotFoundException
from infrastructure.di import get_container
from infrastructure.image import ImageServer


class BotDetailPage:
    """Bot detail page"""

    def __init__(self, page: ft.Page, bot_id: str):
        self._content_container = None
        self.page = page
        self.bot_id = bot_id
        self.container = get_container()
        self.discovery_service: DiscoveryService = self.container.resolve(
            DiscoveryService
        )
        self.image_server: ImageServer = self.container.resolve(ImageServer)
        self._bot: Optional[Bot] = None

    def _get_tag_info(self, tag_name: str) -> tuple[str, str]:
        """Get tag display name and icon"""

        tag_map = {
            "music": ("音樂", ft.Icons.MUSIC_NOTE),
            "minigames": ("小遊戲", ft.Icons.GAMES),
            "fun": ("娛樂", ft.Icons.EMOJI_EMOTIONS),
            "utility": ("工具", ft.Icons.BUILD),
            "management": ("管理", ft.Icons.ADMIN_PANEL_SETTINGS),
            "customizable": ("可自訂", ft.Icons.TUNE),
            "automation": ("自動化", ft.Icons.AUTORENEW),
            "roleplay": ("角色扮演", ft.Icons.THEATER_COMEDY),
            "nsfw": ("NSFW", ft.Icons.EIGHTEEN_UP_RATING),
        }

        return tag_map.get(tag_name, (tag_name, ft.Icons.TAG))

    def _get_status_color(self, status: str) -> str:
        """Get status indicator color"""

        status_colors = {
            "online": ft.Colors.GREEN,
            "idle": ft.Colors.YELLOW,
            "dnd": ft.Colors.RED,
            "offline": ft.Colors.GREY,
        }

        return status_colors.get(status, ft.Colors.GREY)

    def _get_status_text(self, status: str) -> str:
        """Get status text"""

        status_texts = {
            "online": "在線",
            "idle": "閒置",
            "dnd": "請勿打擾",
            "offline": "離線",
        }

        return status_texts.get(status, "未知")

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

        # Create loading indicator first
        self._content_container = ft.Container(
            expand=True,
            alignment=ft.alignment.center,
        )

        # Create loading indicator
        self._content_container.content = ft.Column(
            [
                ft.ProgressRing(),
                ft.Text("載入中...", size=16, text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )

        # Load bot data asynchronously
        self.page.run_task(self._load_bot_data)

        return self._content_container

    async def _load_bot_data(self):
        """Load bot data asynchronously"""

        try:
            bot_id_int = int(self.bot_id)
            self._bot = await self.discovery_service.get_bot_by_id(bot_id_int)
            self._render_bot_detail()

        except EntityNotFoundException as e:
            self._show_error(f"找不到此機器人 (ID: {self.bot_id})")

        except ValueError:
            self._show_error(f"無效的機器人 ID: {self.bot_id}")

        except Exception as e:
            self._show_error(f"載入失敗: {str(e)}")

    def _render_bot_detail(self):
        """Render bot detail UI"""

        if not self._bot:
            return

        bot = self._bot

        # Create detail view

        detail_view = ft.Column(
            [
                # Banner and Avatar
                self._create_header_section(bot),
                # Name
                ft.Row(
                    [
                        ft.Text(
                            bot.name,
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # Badges (Verified, Partner)
                self._create_badges_section(bot),
                # Description
                ft.Container(
                    content=ft.Text(
                        bot.description,
                        size=16,
                        weight=ft.FontWeight.NORMAL,
                        text_align=ft.TextAlign.CENTER,
                        no_wrap=False,
                    ),
                    alignment=ft.alignment.center,
                    padding=ft.padding.symmetric(horizontal=20),
                ),
                # Tags
                self._create_tags_section(bot),
                # Action buttons (Invite, Support Server, Website)
                self._create_action_buttons(bot),
                # Introduction (Markdown)
                ft.Container(
                    content=ft.Markdown(
                        self._convert_discord_emojis(bot.introduce),
                        fit_content=False,
                        on_tap_link=lambda e: self.page.launch_url(e.data),
                    ),
                    padding=ft.padding.all(20),
                ),
                # Statistics
                self._create_statistics_section(bot),
                # DCTW page link
                ft.Row(
                    [
                        ft.ElevatedButton(
                            text="DCTW 機器人頁面",
                            icon=ft.Icons.OPEN_IN_NEW,
                            on_click=lambda e: self.page.launch_url(
                                f"https://dctw.xyz/bots/{bot.id}"
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                # Spacing at bottom
                ft.Container(height=20),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self._content_container.content = detail_view
        self.page.update()

    def _create_header_section(self, bot: Bot) -> ft.Control:
        """Create header section with banner and avatar"""
        banner_url = self._cache_image(bot.banner.value) if bot.banner else ""
        avatar_url = self._cache_image(bot.avatar.value)
        status_color = self._get_status_color(bot.status.value)

        status_text = self._get_status_text(bot.status.value)
        if banner_url:
            banner_content = ft.Image(
                src=banner_url,
                fit=ft.ImageFit.COVER,
                width=float("inf"),
                error_content=ft.Container(
                    bgcolor=ft.Colors.SURFACE,
                ),
            )
        else:
            banner_content = ft.Container(
                bgcolor=ft.Colors.SURFACE,
            )

        return ft.Stack(
            [
                # Banner
                ft.Container(
                    content=banner_content,
                    height=256,
                    expand=True,
                ),
                # Avatar with status indicator
                ft.Container(
                    content=ft.Stack(
                        [
                            ft.CircleAvatar(
                                foreground_image_src=avatar_url,
                                radius=64,
                            ),
                            ft.Container(
                                content=ft.Container(
                                    content=ft.CircleAvatar(
                                        bgcolor=status_color,
                                        radius=16,
                                    ),
                                    on_click=lambda e: self.page.open(
                                        ft.SnackBar(
                                            content=ft.Text(
                                                f"機器人狀態: {status_text}"
                                            )
                                        )
                                    ),
                                ),
                                alignment=ft.alignment.bottom_right,
                            ),
                        ],
                        width=128,
                        height=128,
                    ),
                    alignment=ft.alignment.bottom_center,
                    margin=ft.margin.only(top=128),
                ),
            ],
            height=256 + 64,
        )

    def _create_badges_section(self, bot: Bot) -> ft.Control:
        """Create badges section (verified, partner)"""

        badges = []

        if bot.verified:
            badges.append(
                ft.ElevatedButton(
                    text="Discord 已驗證",
                    color=ft.Colors.WHITE,
                    icon=ft.Icons.VERIFIED,
                    icon_color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.BLUE,
                    on_click=lambda e: self.page.open(
                        ft.SnackBar(content=ft.Text("此機器人經過 Discord 官方驗證。"))
                    ),
                )
            )

        if bot.is_partnered:
            badges.append(
                ft.ElevatedButton(
                    text="DCTW 合作夥伴",
                    color=ft.Colors.WHITE,
                    icon=ft.Icons.STAR,
                    icon_color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.GREEN,
                    on_click=lambda e: self.page.open(
                        ft.SnackBar(content=ft.Text("此機器人為 DCTW 合作夥伴。"))
                    ),
                )
            )

        if not badges:
            return ft.Container(height=0)

        return ft.Row(
            badges,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _create_tags_section(self, bot: Bot) -> ft.Control:
        """Create tags section"""

        tag_buttons = []

        for tag in bot.tags:
            display_name, icon = self._get_tag_info(tag.name)

            tag_buttons.append(ft.ElevatedButton(text=display_name, icon=icon))

        if not tag_buttons:
            return ft.Container(height=0)

        return ft.Container(
            content=ft.Row(
                tag_buttons,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                wrap=True,
            ),
            alignment=ft.alignment.center,
            padding=ft.padding.symmetric(horizontal=20),
        )

    def _create_action_buttons(self, bot: Bot) -> ft.Control:
        """Create action buttons (invite, support server, website)"""
        buttons = [
            ft.ElevatedButton(
                icon=ft.Icons.PERSON_ADD,
                text="邀請機器人",
                on_click=lambda e: self.page.launch_url(bot.links.invite.value),
            ),
        ]

        if bot.links.support_server:
            buttons.append(
                ft.ElevatedButton(
                    icon=ft.Icons.HELP_CENTER,
                    text="支援伺服器",
                    on_click=lambda e: self.page.launch_url(bot.links.support_server),
                )
            )

        if bot.links.website:
            buttons.append(
                ft.ElevatedButton(
                    icon=ft.Icons.LINK,
                    text="官方網站",
                    on_click=lambda e: self.page.launch_url(bot.links.website),
                )
            )

        return ft.Container(
            content=ft.Row(
                buttons,
                alignment=ft.MainAxisAlignment.CENTER,
                wrap=True,
            ),
            alignment=ft.alignment.center,
            padding=ft.padding.symmetric(horizontal=20),
        )

    def _create_statistics_section(self, bot: Bot) -> ft.Control:
        """Create statistics section"""

        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Icon(ft.Icons.STAR, size=32),
                            ft.Text(
                                str(bot.statistics.votes),
                                size=20,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text("投票數", size=14, color=ft.Colors.GREY),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Icon(ft.Icons.DNS, size=32),
                            ft.Text(
                                str(bot.statistics.servers),
                                size=20,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text("伺服器數", size=14, color=ft.Colors.GREY),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=40,
            ),
            padding=ft.padding.all(20),
        )

    def _show_error(self, message: str):
        """Show error message"""

        error_view = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.ERROR_OUTLINE, size=64, color=ft.Colors.ERROR),
                    ft.Text(message, size=18, text_align=ft.TextAlign.CENTER),
                    ft.ElevatedButton(
                        text="返回",
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda e: self.page.go("/"),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20,
            ),
            alignment=ft.alignment.center,
            expand=True,
            padding=ft.padding.all(40),
        )

        self._content_container.content = error_view
        self.page.update()
