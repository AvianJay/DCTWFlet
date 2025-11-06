from abc import ABC
from typing import Any


class ValueObject(ABC):

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._equality_components() == other._equality_components()

    def __hash__(self) -> int:
        return hash(self._equality_components())

    def _equality_components(self) -> tuple:
        return tuple(
            getattr(self, attr)
            for attr in dir(self)
            if not attr.startswith("_") and not callable(getattr(self, attr))
        )

    def __repr__(self) -> str:
        attrs = ", ".join(
            f"{k}={v!r}" for k, v in self.__dict__.items() if not k.startswith("_")
        )
        return f"{self.__class__.__name__}({attrs})"
