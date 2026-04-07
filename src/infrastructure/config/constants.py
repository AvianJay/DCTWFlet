"""Application constants"""

APP_NAME = "DCTWFlet"
APP_VERSION = "0.1.2"
CACHE_TTL = 60  # seconds

# API URLs
DCTW_API_PROXY_BASE_URL = "https://dctw-apiproxy.avianjay.sbs/proxy/api/v2"
DCTW_API_AUTH_BASE_URL = "https://dctw.nkhost.dev"
DCTW_API_VERSION_PREFIX = "/api/v2"
DCTW_API_OPENAPI_URL = "https://dctw.nkhost.dev/api/v2/openapi.json"
DCTW_API_BASE_URL = DCTW_API_PROXY_BASE_URL
DCTW_WEBSITE_URL = "https://dctw.xyz"

# Update channels
UPDATE_CHANNEL_DEVELOPER = "developer"
UPDATE_CHANNEL_NIGHTLY = "nightly"
UPDATE_CHANNEL_RELEASE = "release"
