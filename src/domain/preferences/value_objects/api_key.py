from typing import Optional
from domain.shared import ValueObject


class ApiKey(ValueObject):
    def __init__(self, key: Optional[str] = None):
        self._key = key.strip() if key else None

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
