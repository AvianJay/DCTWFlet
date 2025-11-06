"""Configuration storage"""

import json
import aiofiles
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ConfigStorage:
    """Configuration file storage"""

    def __init__(self, config_file: Path):
        self._config_file = config_file

    async def load(self) -> Dict[str, Any]:
        if not self._config_file.exists():
            return {}

        try:
            async with aiofiles.open(self._config_file, "r", encoding="utf-8") as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    async def save(self, data: Dict[str, Any]) -> None:
        self._config_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with aiofiles.open(self._config_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))
            logger.info("Config saved successfully")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise

    async def exists(self) -> bool:
        return self._config_file.exists()
