"""Application settings"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import platform
import os
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    """Application Settings"""

    app_name: str = "DCTWFlet"
    app_version: str = "0.1.2"
    hash: str = "unknown"
    update_channel: str = "developer"
    data_dir: Path = None
    cache_dir: Path = None
    image_cache_dir: Path = None
    log_dir: Path = None
    api_base_url: str = "https://dctw.nyanko.host/api/v1"
    api_key: Optional[str] = None
    cache_ttl: int = 60

    image_server_port_range: tuple[int, int] = (10000, 60000)

    def __post_init__(self):

        if self.data_dir is None:
            self.data_dir = self._get_default_data_dir()

        self.data_dir.mkdir(parents=True, exist_ok=True)

        if self.cache_dir is None:
            self.cache_dir = self.data_dir / "cache"

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if self.image_cache_dir is None:
            self.image_cache_dir = self.data_dir / "images"

        self.image_cache_dir.mkdir(parents=True, exist_ok=True)

        if self.log_dir is None:
            self.log_dir = self.data_dir / "logs"

        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Load API key from config.json if not already set

        if self.api_key is None:
            self._load_api_key_from_config()

    @staticmethod
    def _get_default_data_dir() -> Path:
        """Get the default data directory"""
        system = platform.system()

        if system == "Windows":
            base = Path(os.environ.get("APPDATA", Path.home()))
        elif system == "Darwin":  # macOS
            base = Path.home() / "Library" / "Application Support"
        else:  # Linux and others
            base = Path.home() / ".local" / "share"

        return base / "DCTWFlet"

    @property
    def config_file(self) -> Path:
        return self.data_dir / "config.json"

    @property
    def cache_file(self) -> Path:
        return self.cache_dir / "cache.json"

    @property
    def log_file(self) -> Path:
        return self.log_dir / "app.log"

    def _load_api_key_from_config(self) -> None:
        """Load API key from config.json file"""

        config_file = self.config_file

        if config_file.exists():

            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    # Load apikey from config (UserPreferences uses 'apikey')

                    api_key = config_data.get("apikey", "")
                    if api_key:
                        self.api_key = api_key
                        logger.info("API key loaded from config.json")

                    else:
                        logger.warning("No API key found in config.json")

            except Exception as e:
                logger.error(f"Failed to load API key from config: {e}")


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
