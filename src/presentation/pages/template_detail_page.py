
import asyncio
import flet as ft
import logging
from typing import List, Optional
from application.services import DiscoveryService, UserProfileService
from domain.discovery.entities import Template
from domain.shared import EntityNotFoundException
from infrastructure.api import DctwApiClient
from infrastructure.di import get_container
from infrastructure.image import ImageServer
from presentation.components import (
    CommentsSection,
    VoteButton,
    build_social_links_section,
    build_user_row,
)
from presentation.tag_mappings import TEMPLATE_TAGS
from presentation.url_helper import open_url

logger = logging.getLogger(__name__)


class TemplateDetailPage:
    """Template detail page"""

    def __init__(self, page: ft.Page, template_id: str, on_tag_click=None):
        self._content_container = None
        self.page = page
        self.template_id = template_id
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
        self._template: Optional[Template] = None
        self._author_container: Optional[ft.Container] = None

    def _get_tag_info(self, tag_name: str) -> tuple[str, str]:
        """Get tag display name and icon"""
        return TEMPLATE_TAGS.get(tag_name, (tag_name, ft.Icons.TAG))

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

        self.page.run_task(self._load_template_data)

        return self._content_container

    async def _load_template_data(self):
        """Load template data asynchronously"""
        try:
            template_id_int = int(self.template_id)
            self._template = await self.discovery_service.get_template_by_id(template_id_int)
            self._render_template_detail()
            self.page.run_task(self._load_template_author)

        except EntityNotFoundException:
            self._show_error(f"找不到此模板 (ID: {self.template_id})")
        except ValueError:
            self._show_error(f"無效的模板 ID: {self.template_id}")
        except Exception as e:
            self._show_error(f"載入失敗: {str(e)}")

    def _render_template_detail(self):
        """Render template detail UI"""
        if not self._template:
            return

        template = self._template

        self._author_container = ft.Container()

        detail_view = ft.Column(
            [
                ft.Container(height=40),
                # Name
                ft.Row(
                    [
                        ft.Text(
                            template.name,
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # Author (avatar + name), like the official page
                self._author_container,
                # Description
                ft.Container(
                    content=ft.Text(
                        template.description,
                        size=16,
                        weight=ft.FontWeight.NORMAL,
                        text_align=ft.TextAlign.CENTER,
                        no_wrap=False,
                    ),
                    alignment=ft.Alignment(0, 0),
                    padding=ft.padding.symmetric(horizontal=20),
                ),
                # Action buttons
                ft.Container(
                    content=ft.Row(
                        [
                            ft.ElevatedButton(
                                icon=ft.Icons.ADD,
                                content=ft.Text("使用模板"),
                                disabled=not template.links.share_url,
                                on_click=lambda e: open_url(
                                    self.page, template.links.share_url
                                ),
                            ),
                            VoteButton(
                                page=self.page,
                                api_client=self.api_client,
                                item_type="templates",
                                item_id=template.id,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    alignment=ft.Alignment(0, 0),
                    padding=ft.padding.symmetric(vertical=20),
                ),
                # Tags
                self._create_tags_section(template),
                # Social links (same platforms as the official page)
                self._create_social_links_section(template),
                # Introduction (Markdown)
                ft.Container(
                    content=ft.Markdown(
                        template.introduce,
                        fit_content=False,
                        on_tap_link=lambda e: open_url(self.page, e.data),
                    ),
                    padding=ft.padding.all(20),
                ),
                # Reviews (same data as the website's 使用者評論 tab)
                self._create_comments_section(template),
                # DCTW page link
                ft.Row(
                    [
                        ft.ElevatedButton(
                            content=ft.Text("DCTW 模板頁面"),
                            icon=ft.Icons.OPEN_IN_NEW,
                            on_click=lambda e: open_url(
                                self.page, f"https://dctw.xyz/templates/{template.id}"
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

    def _create_social_links_section(self, template: Template) -> ft.Control:
        """Create the social links block shown on the official page."""
        section = build_social_links_section(
            self.page, template.social_links, self._cache_image
        )
        return section if section is not None else ft.Container(height=0)

    def _create_comments_section(self, template: Template) -> ft.Control:
        """Create the review list of the official page."""
        return CommentsSection(
            page=self.page,
            comments=template.comments,
            load_profiles=self._load_reviewer_profiles,
            cache_image=self._cache_image,
        ).build()

    async def _load_reviewer_profiles(self, user_ids: List[str]):
        """Resolve the reviewers through the official template page action."""
        return await self.user_profile_service.get_profiles(
            user_ids, f"/templates/{self.template_id}/"
        )

    async def _load_template_author(self) -> None:
        """Resolve the author ids and show the author row of the website."""
        template = self._template
        if template is None or not template.author_ids:
            return

        try:
            profiles = await self.user_profile_service.get_profiles(
                template.author_ids, f"/templates/{self.template_id}/"
            )
        except Exception as error:
            logger.warning(
                f"Failed to load the author of template {template.id}: {error}"
            )
            return

        if not profiles or self._author_container is None:
            return

        try:
            self._author_container.content = build_user_row(
                "作者", profiles, self._cache_image
            )
            self.page.update()
        except Exception:
            logger.debug("Template page closed before the author arrived")

    def _create_tags_section(self, template: Template) -> ft.Control:
        """Create tags section"""
        tag_buttons = []
        for tag in template.tags:
            display_name, icon = self._get_tag_info(tag.name)
            tag_buttons.append(
                ft.ElevatedButton(
                    content=ft.Text(display_name),
                    icon=icon,
                    tooltip="顯示相關模板",
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
        """Show the template list filtered by the tag that was tapped."""
        if self._on_tag_click is None:
            return
        try:
            self._on_tag_click(tag_name)
        except Exception:
            logger.exception("Failed to open the related templates")

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
