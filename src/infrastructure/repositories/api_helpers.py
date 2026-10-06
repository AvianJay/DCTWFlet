"""Helpers for the data returned by the DCTW API."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from ..config.constants import DCTW_API_BASE_URL, DEFAULT_AVATAR_URL

# DCTW stores timestamps without a timezone offset in UTC+8 (Taipei).
DCTW_TIMEZONE = timezone(timedelta(hours=8))

# Avatar used when the API does not provide a usable image.
FALLBACK_AVATAR_URL = DEFAULT_AVATAR_URL

# Relative paths the website uses as placeholders for items without an icon.
# They are not served as real images, so they fall back to the default avatar.
_PLACEHOLDER_PATHS = {"/guild-icon.png"}


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
            return fallback
        return DCTW_API_BASE_URL.rstrip("/") + url

    if not url.startswith(("http://", "https://")):
        return fallback

    return url


def normalize_optional_url(value: Optional[str]) -> Optional[str]:
    """Return an absolute URL, or ``None`` when there is no usable one."""
    return normalize_url(value) or None


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
