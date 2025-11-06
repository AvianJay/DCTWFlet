from abc import ABC
from typing import Any, TypeVar, Generic

TId = TypeVar("TId")


class Entity(ABC, Generic[TId]):

    def __init__(self, id: TId):
        if id is None:
            raise ValueError("Entity ID cannot be None")
        self._id = id

    @property
    def id(self) -> TId:
        return self._id

    def __eq__(self, other: Any) -> bool:
        """Two entities are equal if they have the same ID"""
        if not isinstance(other, self.__class__):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        """Hash based on ID"""
        return hash((self.__class__.__name__, self._id))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self._id})"
