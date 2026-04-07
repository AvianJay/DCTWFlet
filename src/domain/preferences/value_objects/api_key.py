from typing import Optional
from domain.shared import ValueObject


class ApiKey(ValueObject):
    LEGACY_DEFAULT_API_KEY = (
        "dctw_live_683165bb3e9be69a_TWb0eEaUfXoMuZ9ONbh1RyT12pnjFq6uZQYUnnE8CTj"
    )

    def __init__(self, key: Optional[str] = None):
        self._key = self.normalize(key)

    @classmethod
    def normalize(cls, key: Optional[str]) -> Optional[str]:
        normalized = key.strip() if key else None
        if not normalized or normalized == cls.LEGACY_DEFAULT_API_KEY:
            return None
        return normalized

    @property
    def value(self) -> Optional[str]:
        return self._key

    @property
    def is_set(self) -> bool:
        """Check if API key is set"""
        return self._key is not None and len(self._key) > 0

    def _equality_components(self) -> tuple:
        return (self._key,)

    def __str__(self) -> str:
        if not self.is_set:
            return ""
        if len(self._key) > 8:
            return f"{self._key[:4]}...{self._key[-4:]}"
        return "****"

    def __repr__(self) -> str:
        return f"ApiKey(is_set={self.is_set})"
