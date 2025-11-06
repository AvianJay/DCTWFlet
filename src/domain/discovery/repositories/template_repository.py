"""Template repository interface"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities import Template


class TemplateRepository(ABC):
    """Template repository interface"""

    @abstractmethod
    async def find_all(self) -> List[Template]:
        """Get allTemplates"""
        pass

    @abstractmethod
    async def find_by_id(self, template_id: int) -> Optional[Template]:
        """Find Template by ID"""
        pass

    @abstractmethod
    async def clear_cache(self) -> None:
        """Clear cache"""
        pass
