"""Tag labels and icons.

The names, translations and order mirror the official website tag lists so
the in-app filters behave exactly like dctw.xyz.
"""

import flet as ft

BOT_TAGS = {
    "music": ("音樂", ft.Icons.MUSIC_NOTE),
    "fun": ("娛樂", ft.Icons.EMOJI_EMOTIONS),
    "management": ("管理", ft.Icons.SETTINGS),
    "utility": ("工具", ft.Icons.BUILD),
    "minigames": ("小遊戲", ft.Icons.SPORTS_ESPORTS),
    "customizable": ("可自訂", ft.Icons.PALETTE),
    "automation": ("自動化", ft.Icons.AUTO_FIX_HIGH),
    "roleplay": ("角色扮演", ft.Icons.THEATER_COMEDY),
    "nsfw": ("NSFW", ft.Icons.DO_NOT_DISTURB),
}

SERVER_TAGS = {
    "gaming": ("遊戲", ft.Icons.SPORTS_ESPORTS),
    "community": ("社群", ft.Icons.GROUPS),
    "anime": ("動漫", ft.Icons.ANIMATION),
    "art": ("藝術", ft.Icons.BRUSH),
    "programing": ("程式", ft.Icons.CODE),
    "programming": ("程式", ft.Icons.CODE),  # API 兩種拼法都出現過
    "hangout": ("交流", ft.Icons.FORUM),
    "acting": ("對戲", ft.Icons.MIC),
    "politics": ("政治", ft.Icons.GAVEL),
    "roleplay": ("角色扮演", ft.Icons.PEOPLE),
    "nsfw": ("NSFW", ft.Icons.DO_NOT_DISTURB),
}

TEMPLATE_TAGS = {
    "gaming": ("遊戲社群模板", ft.Icons.SPORTS_ESPORTS),
    "support": ("支援社群模板", ft.Icons.SUPPORT_AGENT),
    "fun": ("趣味社群模板", ft.Icons.EMOJI_EMOTIONS),
    "large": ("大型社群模板", ft.Icons.GROUPS),
    "community": ("一般社群模板", ft.Icons.GROUP),
    "anime": ("動漫社群模板", ft.Icons.ANIMATION),
    "art": ("藝術社群模板", ft.Icons.BRUSH),
    "nsfw": ("NSFW", ft.Icons.DO_NOT_DISTURB),
}

# Chips shown in the tag filter, in the same order as the website sidebar.
BOT_TAG_FILTERS = (
    "music",
    "fun",
    "management",
    "utility",
    "minigames",
    "customizable",
    "automation",
    "roleplay",
    "nsfw",
)

SERVER_TAG_FILTERS = (
    "gaming",
    "community",
    "anime",
    "art",
    "programing",
    "hangout",
    "acting",
    "politics",
    "roleplay",
    "nsfw",
)

TEMPLATE_TAG_FILTERS = (
    "gaming",
    "support",
    "fun",
    "large",
    "community",
    "anime",
    "art",
    "nsfw",
)
