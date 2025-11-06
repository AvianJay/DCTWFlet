"""Dependency injection"""

from .container import DiContainer, get_container, setup_container

__all__ = [
    "DiContainer",
    "get_container",
    "setup_container",
]
