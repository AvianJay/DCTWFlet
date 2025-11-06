from typing import Set
from domain.shared import ValueObject, InvalidArgumentException


class Tag(ValueObject):
    VALID_TAGS: Set[str] = set()

    def __init__(self, name: str):
        if not name:
            raise InvalidArgumentException("name", "Tag name cannot be empty")
        self._name = name.lower()
        self._validate()

    @property
    def name(self) -> str:
        return self._name

    def _validate(self):
        if self.VALID_TAGS and self._name not in self.VALID_TAGS:
            raise InvalidArgumentException(
                "name", f"Invalid tag: {self._name}. Valid tags: {self.VALID_TAGS}"
            )

    def _equality_components(self) -> tuple:
        return (self._name,)

    def __str__(self) -> str:
        return self._name


class BotTag(Tag):
    """Bot tag"""

    VALID_TAGS = {
        "music",
        "minigames",
        "fun",
        "utility",
        "management",
        "customizable",
        "automation",
        "roleplay",
        "nsfw",
    }


class ServerTag(Tag):
    """Server tag"""

    VALID_TAGS = {
        "gaming",
        "community",
        "anime",
        "art",
        "hangout",
        "programming",
        "acting",
        "nsfw",
        "roleplay",
        "politics",
    }


class TemplateTag(Tag):
    """Template tag"""

    VALID_TAGS = {
        "community",
        "gaming",
        "anime",
        "art",
        "nsfw",
    }
