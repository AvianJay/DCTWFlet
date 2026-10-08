"""Helpers for the data returned by the DCTW API."""

import json
from datetime import datetime, timezone
from typing import Optional

from domain.discovery.value_objects import Comment
from domain.discovery.value_objects.comment import DCTW_TIMEZONE

from ..config.constants import DCTW_API_BASE_URL, DEFAULT_AVATAR_URL

# Avatar used when the API does not provide a usable image.
FALLBACK_AVATAR_URL = DEFAULT_AVATAR_URL

# Relative paths the website uses as placeholders for items without an icon.
# The official site swaps them for its own placeholder icon, so the app shows
# exactly the same picture instead of the site logo.
PLACEHOLDER_AVATAR_URL = DCTW_API_BASE_URL.rstrip("/") + "/default-icon.png"

_PLACEHOLDER_PATHS = {
    "/icon.png",
    "/default-icon.png",
    "/guild-icon.png",
    "/favicon.ico",
}


def normalize_url(value: Optional[str], fallback: str = "") -> str:
    """Return an absolute URL that Flet is able to render.

    The API occasionally returns relative paths (for example ``/icon.png``),
    which are resolved against the DCTW website.
    """
    url = (value or "").strip()

    if not url:
        return fallback

    if url.startswith("//"):
        return "https:" + url

    if url.startswith("/"):
        if url.lower() in _PLACEHOLDER_PATHS:
            return PLACEHOLDER_AVATAR_URL
        return DCTW_API_BASE_URL.rstrip("/") + url

    if not url.startswith(("http://", "https://")):
        return fallback

    return url


def normalize_optional_url(value: Optional[str]) -> Optional[str]:
    """Return an absolute URL, or ``None`` when there is no usable one."""
    return normalize_url(value) or None


def parse_tag_list(value) -> list[str]:
    """Return the tags of an API item as a list of clean lowercase names.

    The DCTW API returns tags as a comma separated string, while the cached
    payloads store them as a list. Both shapes are accepted so cached data
    keeps working after the API format changes.
    """
    if not value:
        return []

    if isinstance(value, str):
        raw_tags = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        raw_tags = []
        for item in value:
            raw_tags.extend(str(item).split(","))
    else:
        return []

    tags: list[str] = []
    for raw_tag in raw_tags:
        tag = raw_tag.strip().lower()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def to_bool(value) -> bool:
    """Convert the API's mixed booleans ("0"/"1"/true/false) to a real bool."""
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def parse_author_ids(data: dict) -> list[str]:
    """Return the Discord ids of a bot's authors.

    The API stores them as a single id, a comma separated list or a JSON
    array string; the website merges ``author`` with ``devs``/``co_authors``.
    """
    ids = parse_id_list(data.get("author"))
    for value in (data.get("devs"), data.get("co_authors")):
        for user_id in parse_id_list(value):
            if user_id not in ids:
                ids.append(user_id)
    return ids


def parse_id_list(value) -> list[str]:
    """Return Discord ids from the single/CSV/JSON-array shapes of the API."""
    ids: list[str] = []

    def add(value) -> None:
        if value is None:
            return

        if isinstance(value, (list, tuple, set)):
            for item in value:
                add(item)
            return

        text = str(value).strip()
        if not text:
            return

        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except ValueError:
                parsed = None
            if isinstance(parsed, list):
                for item in parsed:
                    add(item)
                return

        for part in text.split(","):
            part = part.strip()
            if part and part not in ids:
                ids.append(part)

    add(value)
    return ids


def parse_features(value) -> list[str]:
    """Return the raw Discord guild features of a server.

    The API stores them as a comma separated string (``COMMUNITY,ANIMATED_ICON``)
    and the website only uses them to label the server (discoverable,
    community or private).
    """
    if not value:
        return []

    if isinstance(value, str):
        raw_values = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        raw_values = [str(item) for item in value]
    else:
        return []

    features: list[str] = []
    for raw_value in raw_values:
        feature = raw_value.strip().upper()
        if feature and feature not in features:
            features.append(feature)
    return features


def parse_admin_entries(value) -> list[dict[str, str]]:
    """Return the admins of a server as ``{"id": ..., "job": ...}`` entries.

    The API stores admins as a JSON string (or array) of objects like
    ``{"id": "123", "job": "管理員"}``. Just like the website, entries
    without an id are dropped.
    """
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            value = json.loads(text)
        except ValueError:
            return []

    if not isinstance(value, list):
        return []

    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in value:
        if isinstance(item, str):
            user_id, job = item.strip(), ""
        elif isinstance(item, dict):
            user_id = str(item.get("id") or "").strip()
            job = str(item.get("job") or item.get("role") or "").strip()
        else:
            continue

        if not user_id or user_id in seen:
            continue
        seen.add(user_id)
        entries.append({"id": user_id, "job": job})
    return entries


def parse_comments(value) -> list[Comment]:
    """Return the reviews of an API item as :class:`Comment` objects.

    Reviews are embedded in the item itself (``comments``); the separate
    ``/comments/`` endpoints answer 404, so the single item endpoint is the
    source of truth used by the website as well.
    """
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            value = json.loads(text)
        except ValueError:
            return []

    if not isinstance(value, list):
        return []

    comments: list[Comment] = []
    for item in value:
        if not isinstance(item, dict):
            continue

        try:
            stars = int(item.get("stars") or 0)
        except (TypeError, ValueError):
            stars = 0

        comments.append(
            Comment(
                user_id=str(
                    item.get("userId") or item.get("user_id") or ""
                ).strip(),
                stars=max(0, min(5, stars)),
                content=str(item.get("content") or "").strip(),
                created_at=parse_datetime(item.get("created_at")),
                edited=to_bool(item.get("edited", False)),
            )
        )
    return comments


def serialize_comments(comments) -> list[dict]:
    """Serialize comments for the cache (round-trips through parse_comments)."""
    return [
        {
            "userId": comment.user_id,
            "stars": comment.stars,
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
            "edited": comment.edited,
        }
        for comment in comments
    ]


# Platforms shown on the official detail pages, in the same order.
SOCIAL_PLATFORMS = ("Line", "Facebook", "Instagram", "Twitch", "Threads", "X")


def parse_social_links(value) -> dict[str, str]:
    """Return the social links of an API item as a platform -> URL mapping.

    The API stores socialLinks as a JSON string and uses empty strings or
    the literal "None" for platforms that were left blank. Just like the
    official website only entries with a http(s) URL are kept.
    """
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except ValueError:
            return {}
        value = parsed

    if not isinstance(value, dict):
        return {}

    links: dict[str, str] = {}
    for platform, url in value.items():
        if not isinstance(platform, str) or not isinstance(url, str):
            continue
        url = url.strip()
        if not url or url.lower() == "none":
            continue
        if not url.startswith(("http://", "https://")):
            continue
        links[platform] = url

    ordered: dict[str, str] = {
        platform: links[platform]
        for platform in SOCIAL_PLATFORMS
        if platform in links
    }
    for platform, url in links.items():
        ordered.setdefault(platform, url)
    return ordered


def is_listed_item(data: dict) -> bool:
    """Return whether the website shows the item in its lists.

    The API also returns unpublished and prohibited (banned) records, which
    the official website filters out. Items without those flags are kept so
    cached payloads and other API versions keep working.
    """
    if not to_bool(data.get("published", True)):
        return False
    return not to_bool(data.get("prohibited", False))


def is_listed_bot(data: dict) -> bool:
    """Return whether the website shows the bot in its bot list.

    On top of the shared rules the website only lists bots that passed the
    official DCTW review (``is_official_verified``).
    """
    if not to_bool(
        data.get("is_official_verified", data.get("officialVerified", True))
    ):
        return False
    return is_listed_item(data)


def parse_datetime(value) -> datetime:
    """Parse an API timestamp, assuming UTC+8 for values without a timezone."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return datetime.now(timezone.utc)
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
    else:
        return datetime.now(timezone.utc)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=DCTW_TIMEZONE)

    return parsed.astimezone(timezone.utc)
