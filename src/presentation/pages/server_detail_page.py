
import asyncio
import flet as ft
import logging
from typing import List, Optional
from application.services import (
    DiscoveryService,
    PreferenceService,
    UserProfileService,
)
from domain.discovery.entities import Server
from domain.discovery.value_objects import Comment
from domain.shared import EntityNotFoundException
from infrastructure.api import DctwApiClient
from infrastructure.di import get_container
from infrastructure.image import ImageServer
from presentation.components import (
    CommentPoster,
    CommentsSection,
    VoteButton,
    build_avatar,
    build_admin_section,
    build_intro_markdown,
    build_partner_badge,
    build_social_links_section,
)
from presentation.tag_mappings import SERVER_TAGS
from presentation.url_helper import open_url

logger = logging.getLogger(__name__)


class ServerDetailPage:
    """Server detail page"""

    def __init__(self, page: ft.Page, server_id: str, on_tag_click=None):
        self._content_container = None
        self.page = page
        self.server_id = server_id
        self._on_tag_click = on_tag_click
        self.container = get_container()
        self.discovery_service: DiscoveryService = self.container.resolve(
            DiscoveryService
        )
        self.user_profile_service: UserProfileService = self.container.resolve(
            UserProfileService
        )
        self.image_server: ImageServer = self.container.resolve(ImageServer)
        self.api_client: DctwApiClient = self.container.resolve(DctwApiClient)
        self._server: Optional[Server] = None
        self._admin_container: Optional[ft.Container] = None
        self._comments_container: Optional[ft.Container] = None
        self._comments_section: Optional[CommentsSection] = None
        self.comment_poster = CommentPoster(
            page=page,
            item_type="servers",
            item_id=server_id,
            api_client=self.api_client,
            preference_service=self.container.resolve(PreferenceService),
            on_comments=self._on_comments_changed,
        )

    def _get_tag_info(self, tag_name: str) -> tuple[str, str]:
        """Get tag display name and icon"""
        return SERVER_TAGS.get(tag_name, (tag_name, ft.Icons.TAG))

    def _cache_image(self, url: str) -> str:
        """Cache image and return local URL"""
        if not url:
            return ""
        image_id = self.image_server.register_image(url)
        return self.image_server.get_image_url(image_id)

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
            self.page.run_task(self._load_server_details)

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

        self._admin_container = ft.Container()

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
                # Social links (same platforms as the official page)
                self._create_social_links_section(server),
                # Members / online members / votes
                self._create_statistics_section(server),
                # Discord features (discoverable / community / private)
                self._create_features_section(server),
                # Introduction (Markdown)
                ft.Container(
                    content=build_intro_markdown(
                        self.page, server.introduce, convert_emojis=True
                    ),
                    padding=ft.padding.all(20),
                ),
                # Administrators (same data as the website's 管理人員 tab)
                self._admin_container,
                # Reviews (same data as the website's 使用者評論 tab)
                self._create_comments_placeholder(server),
                # DCTW page link
                ft.Row(
                    [
                        ft.ElevatedButton(
                            content=ft.Text("DCTW 伺服器頁面"),
                            icon=ft.Icons.OPEN_IN_NEW,
                            on_click=lambda e: open_url(
                                self.page, f"https://dctw.xyz/servers/{server.id}"
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

    def _create_social_links_section(self, server: Server) -> ft.Control:
        """Create the social links block shown on the official page."""
        section = build_social_links_section(
            self.page, server.social_links, self._cache_image
        )
        return section if section is not None else ft.Container(height=0)

    def _create_statistics_section(self, server: Server) -> ft.Control:
        """Create the member counters shown on the official page."""
        counters = [
            (ft.Icons.GROUP, server.statistics.members, "成員數量", None),
            (ft.Icons.CIRCLE, server.online_members, "在線人數", ft.Colors.GREEN),
            (ft.Icons.HOW_TO_VOTE, server.statistics.votes, "投票數", None),
        ]

        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Icon(icon, size=28, color=color),
                            ft.Text(
                                f"{value:,}",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=color,
                            ),
                            ft.Text(label, size=13, color=ft.Colors.GREY),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                    for icon, value, label, color in counters
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=36,
            ),
            padding=ft.padding.all(12),
        )

    def _create_features_section(self, server: Server) -> ft.Control:
        """Create the Discord feature badges of the official page."""
        if not server.features:
            return ft.Container(height=0)

        badge = self._create_feature_type_badge(server.features)
        rows: List[ft.Control] = [badge]

        if len(server.features) > 1:
            rows.append(
                ft.ExpansionTile(
                    title=ft.Text("功能列表", size=15, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(
                        f"{len(server.features)} 項功能", size=12, color=ft.Colors.GREY
                    ),
                    tile_padding=ft.padding.symmetric(horizontal=4),
                    controls=[
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Container(
                                        content=ft.Text(feature, size=11),
                                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                        border_radius=8,
                                        padding=ft.padding.symmetric(
                                            horizontal=8, vertical=4
                                        ),
                                    )
                                    for feature in server.features
                                ],
                                wrap=True,
                                spacing=6,
                                run_spacing=6,
                            ),
                            padding=ft.padding.only(left=8, right=8, bottom=8),
                        )
                    ],
                )
            )

        return ft.Container(
            content=ft.Column(rows, spacing=6),
            alignment=ft.Alignment(0, 0),
            padding=ft.padding.symmetric(horizontal=20, vertical=4),
        )

    @staticmethod
    def _create_feature_type_badge(features: List[str]) -> ft.Control:
        """Label the server exactly like the website does."""
        if "DISCOVERABLE" in features:
            text, icon, color = "探索伺服器", ft.Icons.EXPLORE, ft.Colors.AMBER
        elif "COMMUNITY" in features:
            text, icon, color = "社群伺服器", ft.Icons.GROUPS, ft.Colors.DEEP_PURPLE
        else:
            text, icon, color = "私人伺服器", ft.Icons.LOCK, ft.Colors.GREY

        return ft.Row(
            [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(icon, size=14, color=ft.Colors.WHITE),
                            ft.Text(
                                text,
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                            ),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=color,
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )

    def _create_comments_placeholder(self, server: Server) -> ft.Control:
        """Review list and review form, like the official page shows them."""
        self.comment_poster.sync_user()
        self._comments_section = CommentsSection(
            page=self.page,
            comments=server.comments,
            load_profiles=self._load_reviewer_profiles,
            cache_image=self._cache_image,
            loading=not server.comments,
            on_submit=self.comment_poster.submit,
            on_delete=self.comment_poster.delete,
            user_id=self.comment_poster.user_id,
            user_name=self.comment_poster.user_name,
        )
        self._comments_container = ft.Container(content=self._comments_section.build())
        return self._comments_container

    def _on_comments_changed(
        self, comments: List[Comment], user_id: str, user_name: str
    ) -> None:
        """Show the reviews the website returned after a review action."""
        if self._comments_section is None:
            return

        try:
            self._comments_section.set_comments(comments, user_id, user_name)
            self.page.update()
        except Exception:
            logger.debug("Server detail page closed before the reviews arrived")

    async def _load_reviewer_profiles(self, user_ids: List[str]):
        """Resolve the reviewers through the official server page action."""
        return await self.user_profile_service.get_profiles(
            user_ids, f"/servers/{self.server_id}/"
        )

    async def _load_server_details(self) -> None:
        """Show the admin list and the reviews of the official page."""
        server = self._server
        if server is None:
            return

        try:
            details = await self.discovery_service.get_server_details(server.id)
        except Exception as error:
            logger.warning(f"Failed to load the details of server {server.id}: {error}")
            details = None

        admins = details.admins if details else []
        comments = details.comments if details else list(server.comments)

        try:
            if self._admin_container is not None and admins:
                profiles = await self.user_profile_service.get_profiles(
                    [admin.id for admin in admins], f"/servers/{self.server_id}/"
                )
                self._admin_container.content = build_admin_section(
                    admins, profiles, self._cache_image
                )

            if self._comments_section is not None and details is not None:
                self._comments_section.set_comments(comments)

            self.page.update()
        except Exception:
            logger.debug("Server page closed before the details arrived")

    def _create_header_section(self, server: Server) -> ft.Control:
        """Create header section with banner and icon"""
        banner_url = self._cache_image(server.banner.value) if server.banner else ""
        icon_url = self._cache_image(server.icon.value)

        if banner_url:
            banner_content = ft.Image(
                src=banner_url,
                fit=ft.BoxFit.COVER,
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
                    content=build_avatar(icon_url, radius=64),
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
            [build_partner_badge("此伺服器為 DCTW 合作夥伴。")],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _create_tags_section(self, server: Server) -> ft.Control:
        """Create tags section"""
        tag_buttons = []
        for tag in server.tags:
            display_name, icon = self._get_tag_info(tag.name)
            tag_buttons.append(
                ft.ElevatedButton(
                    content=ft.Text(display_name),
                    icon=icon,
                    tooltip="顯示相關伺服器",
                    on_click=lambda e, name=tag.name: self._open_related(name),
                )
            )

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

    def _open_related(self, tag_name: str) -> None:
        """Show the server list filtered by the tag that was tapped."""
        if self._on_tag_click is None:
            return
        try:
            self._on_tag_click(tag_name)
        except Exception:
            logger.exception("Failed to open the related servers")

    def _create_action_buttons(self, server: Server) -> ft.Control:
        """Create action buttons"""
        return ft.Container(
            content=ft.Row(
                [
                    ft.ElevatedButton(
                        icon=ft.Icons.ADD,
                        content=ft.Text("加入伺服器"),
                        on_click=lambda e: open_url(self.page, server.links.invite.value),
                    ),
                    VoteButton(
                        page=self.page,
                        api_client=self.api_client,
                        item_type="servers",
                        item_id=server.id,
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
                        on_click=lambda e: self.page.run_task(self.page.push_route, "/"),
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
