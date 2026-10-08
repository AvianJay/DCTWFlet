"""Markdown introduction block shared by the three detail pages.

The website renders every introduction with a GitHub flavoured pipeline, so
single line breaks stay visible, tables keep their cells and ``~~text~~`` is
struck through. Flet's markdown control does the same once it is told to use
the GitHub extension set and a style sheet that mirrors the website metrics
(``text-sm``/``text-lg`` body copy, ``mb-2`` paragraphs, ``list-disc pl-6``
lists, a hairline ``hr`` and blue links).
"""

import re

import flet as ft

from presentation.url_helper import open_url

#: Discord custom emoji tags, e.g. ``<:name:123456>``.
ANIMATED_EMOJI_PATTERN = re.compile(r"<a:\w*:(\d+)>")
STATIC_EMOJI_PATTERN = re.compile(r"<:\w*:(\d+)>")

#: The website paints body copy with Tailwind's ``text-sm`` (14px/20px), so the
#: same metrics are used on the phone layout.
BODY_SIZE = 14
BODY_HEIGHT = 1.43  # 20px line height for 14px text

INTRO_STYLE_SHEET = ft.MarkdownStyleSheet(
    block_spacing=0,
    p_text_style=ft.TextStyle(size=BODY_SIZE, height=BODY_HEIGHT),
    p_padding=ft.Padding.only(bottom=8),
    h1_text_style=ft.TextStyle(size=24, weight=ft.FontWeight.BOLD, height=1.33),
    h1_padding=ft.Padding.only(bottom=16),
    h2_text_style=ft.TextStyle(size=20, weight=ft.FontWeight.BOLD, height=1.4),
    h2_padding=ft.Padding.only(top=16, bottom=8),
    h3_text_style=ft.TextStyle(size=18, weight=ft.FontWeight.W_600, height=1.55),
    h3_padding=ft.Padding.only(top=12, bottom=4),
    h4_text_style=ft.TextStyle(size=BODY_SIZE, height=BODY_HEIGHT),
    h4_padding=ft.Padding.all(0),
    h5_text_style=ft.TextStyle(size=BODY_SIZE, height=BODY_HEIGHT),
    h5_padding=ft.Padding.all(0),
    h6_text_style=ft.TextStyle(size=BODY_SIZE, height=BODY_HEIGHT),
    h6_padding=ft.Padding.all(0),
    a_text_style=ft.TextStyle(color=ft.Colors.BLUE_500),
    em_text_style=ft.TextStyle(italic=True),
    strong_text_style=ft.TextStyle(weight=ft.FontWeight.BOLD),
    blockquote_text_style=ft.TextStyle(
        italic=True,
        color=ft.Colors.ON_SURFACE_VARIANT,
        size=BODY_SIZE,
        height=BODY_HEIGHT,
    ),
    blockquote_decoration=ft.BoxDecoration(
        border=ft.Border(left=ft.BorderSide(4, ft.Colors.OUTLINE_VARIANT))
    ),
    blockquote_padding=ft.Padding.only(left=16, top=4, bottom=4),
    list_indent=16,
    list_bullet_text_style=ft.TextStyle(size=BODY_SIZE, height=BODY_HEIGHT),
    code_text_style=ft.TextStyle(font_family="monospace", size=13),
    codeblock_padding=ft.Padding.all(12),
    table_head_text_style=ft.TextStyle(size=BODY_SIZE, weight=ft.FontWeight.BOLD),
    table_head_text_align=ft.TextAlign.LEFT,
    table_body_text_style=ft.TextStyle(size=BODY_SIZE),
    table_cells_padding=ft.Padding.symmetric(vertical=2, horizontal=6),
    horizontal_rule_decoration=ft.BoxDecoration(
        border=ft.Border(top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT))
    ),
)


def convert_discord_emojis(text: str) -> str:
    """Turn Discord custom emoji tags into images the markdown control shows."""
    if not text:
        return ""

    text = ANIMATED_EMOJI_PATTERN.sub(
        r"![emoji](https://cdn.discordapp.com/emojis/\1.gif?size=32&quality=lossless)",
        text,
    )
    return STATIC_EMOJI_PATTERN.sub(
        r"![emoji](https://cdn.discordapp.com/emojis/\1.png?size=32&quality=lossless)",
        text,
    )


def build_intro_markdown(
    page: ft.Page, text: str, *, convert_emojis: bool = False
) -> ft.Control:
    """Build the introduction block the same way the website renders it."""
    value = convert_discord_emojis(text) if convert_emojis else (text or "")
    return ft.Markdown(
        value,
        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
        soft_line_break=True,
        fit_content=False,
        md_style_sheet=INTRO_STYLE_SHEET,
        on_tap_link=lambda event: open_url(page, event.data),
    )
