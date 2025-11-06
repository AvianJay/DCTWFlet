from typing import Optional
from domain.shared import ValueObject, InvalidArgumentException


class Url(ValueObject):
    """URL base class"""

    def __init__(self, url: str):
        if not url:
            raise InvalidArgumentException("url", "URL cannot be empty")
        self._url = url.strip()
        self._validate()

    @property
    def value(self) -> str:
        return self._url

    def _validate(self):
        """Validate URL format (can be overridden by subclasses)"""
        if not self._url.startswith(("http://", "https://")):
            raise InvalidArgumentException("url", f"Invalid URL format: {self._url}")

    def _equality_components(self) -> tuple:
        return (self._url,)

    def __str__(self) -> str:
        return self._url


class AvatarUrl(Url):
    """Avatar URL"""

    pass


class BannerUrl(Url):
    """Banner URL"""

    pass


class InviteUrl(Url):
    """Invite URL"""

    pass


class WebsiteUrl(Url):
    """Website URL"""

    pass


class OptionalUrl(ValueObject):
    """Optional URL"""

    def __init__(self, url: Optional[str] = None):
        self._url = url.strip() if url else None

    @property
    def value(self) -> Optional[str]:
        return self._url

    @property
    def is_present(self) -> bool:
        return self._url is not None and len(self._url) > 0

    def _equality_components(self) -> tuple:
        return (self._url,)

    def __str__(self) -> str:
        return self._url or ""
