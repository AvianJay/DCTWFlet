"""Shared helpers for validating and storing the DCTW API key."""

import logging
from typing import Optional, Tuple

import flet as ft

from application.services import DiscoveryService, PreferenceService
from infrastructure.api import DctwApiClient

logger = logging.getLogger(__name__)


async def apply_api_key(
    value: Optional[str],
    preference_service: PreferenceService,
    discovery_service: DiscoveryService,
    api_client: DctwApiClient,
) -> Tuple[bool, str]:
    """Validate an API key and store it.

    Returns:
        A tuple of (success, message).
    """
    key = (value or "").strip()
    if not key:
        return False, "剪貼簿中沒有可用的 API Key，請先在 DCTW 後台複製 API KEY。"

    try:
        is_valid = await api_client.validate_api_key(key)
    except Exception as ex:
        logger.exception("API key validation failed")
        return False, f"驗證失敗（{ex}），請確認網路連線後再試。"

    if not is_valid:
        return False, "此 API Key 無效或已失效，請重新複製正確的 API KEY。"

    try:
        await preference_service.update_api_key(key)
        await discovery_service.clear_all_caches()
    except Exception as ex:
        logger.exception("Failed to store API key")
        return False, f"儲存 API Key 失敗：{ex}"

    return True, "已成功儲存 API Key，正在重新載入資料…"


async def apply_api_key_from_clipboard(
    preference_service: PreferenceService,
    discovery_service: DiscoveryService,
    api_client: DctwApiClient,
) -> Tuple[bool, str]:
    """Read the clipboard and apply the API key found in it."""
    try:
        clipboard_value = await ft.Clipboard().get()
    except Exception:
        logger.exception("Failed to read clipboard")
        return False, "無法讀取剪貼簿，請改用手動輸入 API Key。"

    return await apply_api_key(
        clipboard_value, preference_service, discovery_service, api_client
    )
