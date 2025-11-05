import os
import json
import requests
from datetime import datetime, timedelta
import flet as ft
import hashlib
import shutil
import threading
import mimetypes
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
from flask import Flask, send_file
import random
import string
import traceback
from enum import Enum

app = Flask(__name__)
port = random.randint(10000, 60000)

app_version = "0.1.0"
config_version = 7
update_channel = "developer"
hash = "unknown"
if hash == "unknown":
    try:
        hash = os.popen("git rev-parse --short HEAD").read().strip()
    except Exception as e:
        print("Failed to get git hash:", str(e))
full_version = f"{app_version}-{update_channel}({hash})"

platform = os.getenv("FLET_PLATFORM")
datadir = os.getenv("FLET_APP_STORAGE_DATA", ".")
rel_datadir = os.path.relpath(datadir, os.getcwd())
rel_datadir = rel_datadir.replace("\\", "/")  # for Windows compatibility
if not os.path.exists(rel_datadir):
    os.makedirs(rel_datadir)
print("Data directory:", rel_datadir)

default_config = {
    "config_version": config_version,
    "theme": "system",
    "app_update_check": "popup",
    "home_index": 0,
    "apikey": "dctw_live_683165bb3e9be69a_TWb0eEaUfXoMuZ9ONbh1RyT12pnjFq6uZQYUnnE8CTj",  # default apikey
    "nsfw": False,
    "sort_order_bots": "bumped",
    "sort_order_servers": "bumped",
    "sort_order_templates": "bumped",
    "update_channel": update_channel,
}

config_path = os.path.join(datadir, "config.json")
_config = None

try:
    if os.path.exists(config_path):
        _config = json.load(open(config_path, "r"))
        # Todo: verify
    else:
        _config = default_config.copy()
        json.dump(_config, open(config_path, "w"))
except ValueError:
    _config = default_config.copy()
    json.dump(_config, open(config_path, "w"))

if _config.get("config_version", 0) < config_version:
    print("Updating config file from version", _config.get("config_version", 0), "to version", config_version)
    for k in default_config.keys():
        if not _config.get(k):
            _config[k] = default_config[k]
    _config["config_version"] = config_version
    print("Saving...")
    json.dump(_config, open(config_path, "w"))
    print("Done.")

def config(key, value=None, mode="r"):
    if mode == "r":
        return _config.get(key)
    elif mode == "w":
        _config[key] = value
        json.dump(_config, open(config_path, "w"))
        return True
    else:
        raise ValueError(f"Invalid mode: {mode}")

page = None  # will be set in main.py

cache_limiter = threading.Semaphore(1)
def cache(key, value=None, mode="r", expire=None, force=False):
    cache_limiter.acquire()
    try:
        cache_path = os.path.join(datadir, "cache.json")
        if not os.path.exists(cache_path):
            with open(cache_path, "w") as f:
                json.dump({}, f)
        
        with open(cache_path, "r") as f:
            cache_data = json.load(f)
        
        if mode == "r":
            cache_item = cache_data.get(key)
            if cache_item:
                if cache_item["expire"] is None or cache_item["expire"] > datetime.now().timestamp() or force:
                    cache_limiter.release()
                    return cache_item["value"]
                # else:
                #     del cache_data[key]
                #     with open(cache_path, "w") as f:
                #         json.dump(cache_data, f)
            cache_limiter.release()
            return None
        elif mode == "w":
            cache_data[key] = {"value": value, "expire": (datetime.now() + timedelta(seconds=expire)).timestamp() if expire else None}
            with open(cache_path, "w") as f:
                json.dump(cache_data, f)
            cache_limiter.release()
            return True
        else:
            cache_limiter.release()
            raise ValueError(f"Invalid mode: {mode}")
    except Exception as e:
        cache_limiter.release()
        print(f"Cache error: {e}")
        traceback.print_exc()

BASE_URL = "https://dctw.xyz"
DEFAULT_IMAGE = BASE_URL + "/icon.png"

def _cache_image(url):
    original_url = url
    images_dir = os.path.join(datadir, "images")
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
    url_hash = hashlib.md5(url.encode()).hexdigest()
    image_path = os.path.join(images_dir, url_hash)
    try:
        # https://cdn.discordapp.com/avatars/1048838352427831308/a_2a6944984eb7710d7408da402527db15.gif?size=1024
        extension = os.path.splitext(url.split("?")[0])[1]
        if not extension:
            content_type = requests.head(url).headers.get('Content-Type')
            extension = mimetypes.guess_extension(content_type) if content_type else ''
        image_path += extension
        if os.path.exists(image_path):
            return image_path
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(image_path, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        images = cache("images", mode="r") or {}
        images[original_url] = image_path
        cache("images", images, mode="w")
        return image_path
    except requests.RequestException as e:
        print(f"Error caching image from {url}: {e}")
        print("Try to use default image.")
        try:
            if url != DEFAULT_IMAGE:
                return _cache_image(DEFAULT_IMAGE)
        except Exception as e:
            print(f"Error caching default image: {e}")

def cache_image(url, callback=None, size=None):
    images_dir = os.path.join(datadir, "images")
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
    
    if not url.startswith("http"):
        url = BASE_URL + url
    # set size param
    if size:
        url_parts = urlparse(url)
        query_params = parse_qs(url_parts.query)
        query_params["size"] = size
        url = urlunparse(url_parts._replace(query=urlencode(query_params, doseq=True)))

    # images = cache("images", mode="r") or {}
    id = "".join(random.choices(string.ascii_letters + string.digits, k=16))
    image_ids[id] = url
    url = f"http://127.0.0.1:{port}/image/{id}"
    return url

def clear_cache():
    try:
        clear_image_cache()
        with open(os.path.join(datadir, "cache.json"), "w") as f:
            json.dump({}, f)
        return True
    except Exception as e:
        print(f"Error clearing cache: {e}")
        return False

def clear_image_cache():
    images_dir = os.path.join(datadir, "images")
    if os.path.exists(images_dir):
        for filename in os.listdir(images_dir):
            file_path = os.path.join(images_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Error deleting cached image {file_path}: {e}")
    # cache("images", mode="w", value={})

bots, servers, templates = [], [], []

class SortOrder(Enum):
    NEWEST = "newest"
    VOTE = "vote"
    BUMPED = "bumped"
    SERVER = "server"

def get_bots(sort=SortOrder.BUMPED, tag=None, force=False):
    global bots
    if not force:
        bots = cache("bots")
    if force or bots is None:
        try:
            response = requests.get(
                "https://dctw.nyanko.host/api/v1/bots",
                headers={
                    "User-Agent": f"DCTWFlet/{app_version}",
                    "x-api-key": config("apikey", "")
                }
            )
            response.raise_for_status()
            bots = response.json()["data"]
            cache("bots", bots, mode="w", expire=60)
            # return bots
        except requests.RequestException as e:
            print(f"Error fetching bots: {e}")
            page.open(
                ft.SnackBar(
                    ft.Text("無法取得機器人列表，請檢查網路連線或 API Key 是否正確。"),
                    bgcolor=ft.Colors.RED,
                )
            )
            c = cache("bots", force=True)
            if c:
                return c
            return []
    for bot in bots:
        if not bot.get("bumped_at"):
            bot["bumped_at"] = "1999-01-01T00:00:00Z"
        if not bot.get("created_at"):
            bot["created_at"] = "1999-01-01T00:00:00Z"
    if sort == SortOrder.VOTE:
        bots.sort(key=lambda x: x.get("votes", 0), reverse=True)
    elif sort == SortOrder.NEWEST:
        bots.sort(key=lambda x: datetime.fromisoformat(x.get("created_at", "1999-01-01T00:00:00Z")).astimezone(), reverse=True)
    elif sort == SortOrder.SERVER:
        bots.sort(key=lambda x: x.get("servers", 0), reverse=True)
    elif sort == SortOrder.BUMPED:
        # sort by bumped_at (datetime TZ)
        bots.sort(key=lambda x: datetime.fromisoformat(x.get("bumped_at", "1999-01-01T00:00:00Z")).astimezone(), reverse=True)
    if tag:
        bots = [bot for bot in bots if tag in bot.get("tags", [])]
    return bots

def get_bot_comments(bot_id):
    try:
        response = requests.get(
            f"https://dctw.nyanko.host/api/v1/bots/{bot_id}/comments",
            headers={"User-Agent": f"DCTWFlet/{app_version}", "x-api-key": config("apikey", "")}
        )
        response.raise_for_status()
        comments = response.json()["data"]
        return comments
    except requests.RequestException as e:
        print(f"Error fetching bot comments: {e}")
        return []

def get_servers(sort=SortOrder.BUMPED, tag=None, force=False):
    global servers
    if not force:
        servers = cache("servers")
    if force or servers is None:
        try:
            response = requests.get(
                "https://dctw.nyanko.host/api/v1/servers",
                headers={"User-Agent": f"DCTWFlet/{app_version}", "x-api-key": config("apikey", "")}
            )
            response.raise_for_status()
            servers = response.json()["data"]
            cache("servers", servers, mode="w", expire=60)
            # return servers
        except requests.RequestException as e:
            print(f"Error fetching servers: {e}")
            page.open(
                ft.SnackBar(
                    ft.Text("無法取得伺服器列表，請檢查網路連線或 API Key 是否正確。"),
                    bgcolor=ft.Colors.RED,
                )
            )
            c = cache("servers", force=True)
            if c:
                return c
            return []
    for server in servers:
        if not server.get("bumped_at"):
            server["bumped_at"] = "1999-01-01T00:00:00Z"
        if not server.get("created_at"):
            server["created_at"] = "1999-01-01T00:00:00Z"
    if sort == SortOrder.VOTE:
        servers.sort(key=lambda x: x.get("votes", 0), reverse=True)
    elif sort == SortOrder.NEWEST:
        servers.sort(key=lambda x: datetime.fromisoformat(x.get("created_at", "1999-01-01T00:00:00Z")).astimezone(), reverse=True)
    elif sort == SortOrder.SERVER:
        servers.sort(key=lambda x: x.get("members", 0), reverse=True)
    elif sort == SortOrder.BUMPED:
        # sort by bumped_at (datetime TZ)
        servers.sort(key=lambda x: datetime.fromisoformat(x.get("bumped_at", "1999-01-01T00:00:00Z")).astimezone(), reverse=True)
    if tag:
        servers = [server for server in servers if tag in server.get("tags", [])]
    return servers

def get_server_comments(server_id):
    try:
        response = requests.get(
            f"https://dctw.nyanko.host/api/v1/servers/{server_id}/comments",
            headers={"User-Agent": f"DCTWFlet/{app_version}", "x-api-key": config("apikey", "")}
        )
        response.raise_for_status()
        comments = response.json()["data"]
        return comments
    except requests.RequestException as e:
        print(f"Error fetching server comments: {e}")
        page.open(
            ft.SnackBar(
                ft.Text("無法取得伺服器評論，請檢查網路連線或 API Key 是否正確。"),
                bgcolor=ft.Colors.RED,
            )
        )
        return []

def get_templates(sort=SortOrder.BUMPED, tag=None, force=False):
    global templates
    if not force:
        templates = cache("templates")
    if force or templates is None:
        try:
            response = requests.get(
                "https://dctw.nyanko.host/api/v1/templates",
                headers={"User-Agent": f"DCTWFlet/{app_version}", "x-api-key": config("apikey", "")}
            )
            response.raise_for_status()
            templates = response.json()["data"]
            cache("templates", templates, mode="w", expire=60)
            # return templates
        except requests.RequestException as e:
            print(f"Error fetching templates: {e}")
            page.open(
                ft.SnackBar(
                    ft.Text("無法取得模板列表，請檢查網路連線或 API Key 是否正確。"),
                    bgcolor=ft.Colors.RED,
                )
            )
            c = cache("templates", force=True)
            if c:
                return c
            return []
    for template in templates:
        if "bumped_at" not in template or not template["bumped_at"]:
            template["bumped_at"] = "1999-01-01T00:00:00Z"
        if "created_at" not in template or not template["created_at"]:
            template["created_at"] = "1999-01-01T00:00:00Z"
    if sort == SortOrder.VOTE:
        templates.sort(key=lambda x: x.get("votes", 0), reverse=True)
    elif sort == SortOrder.NEWEST:
        templates.sort(key=lambda x: datetime.fromisoformat(x.get("created_at", "1999-01-01T00:00:00Z")).astimezone(), reverse=True)
    elif sort == SortOrder.BUMPED:
        # sort by bumped_at (datetime TZ)
        templates.sort(key=lambda x: datetime.fromisoformat(x.get("bumped_at", "1999-01-01T00:00:00Z")).astimezone(), reverse=True)
    if tag:
        templates = [template for template in templates if tag in template.get("tags", [])]
    return templates

def get_template_comments(template_id):
    try:
        response = requests.get(
            f"https://dctw.nyanko.host/api/v1/templates/{template_id}/comments",
            headers={"User-Agent": f"DCTWFlet/{app_version}", "x-api-key": config("apikey", "")}
        )
        response.raise_for_status()
        comments = response.json()["data"]
        return comments
    except requests.RequestException as e:
        print(f"Error fetching template comments: {e}")
        page.open(
            ft.SnackBar(
                ft.Text("無法取得模板評論，請檢查網路連線或 API Key 是否正確。"),
                bgcolor=ft.Colors.RED,
            )
        )
        return []

def is_partner(id, type="bots"):
    response = requests.post(
        f"https://dctw.xyz/{type}/{id}",
        headers={"User-Agent": f"DCTWFlet/{app_version}", "next-action": "7fa3998288bd6224af84ea89a09a241417ef8fc622"},
        data=f'["{id}", "partner"]'
    )
    response.raise_for_status()
    print("is_partner response:", response.text)
    data = json.loads(response.text.split("1:")[1])
    item = data.get("item", {})
    return bool(item.get("partner", False))

# image cache server
# 暴力解 超讚
image_ids = {}
@app.route('/image/<path:id>')
def image_cache(id):
    # images = cache("images", mode="r") or {}
    url = image_ids.get(id, id)
    return send_file(_cache_image(url))

def run_image_cache_server():
    app.run(host="127.0.0.1", port=port)

threading.Thread(target=run_image_cache_server, daemon=True).start()

# check updates
def check_update():
    global app_version
    if config("update_channel") == "nightly":
        workflows_url = "https://api.github.com/repos/" \
            "AvianJay/DCTWFlet/actions/workflows"
        res = requests.get(workflows_url).json()
        workflow_url = next(
            (s["url"] for s in res.get("workflows") if s["name"] == "Build"),
            None
        )
        if not workflow_url:
            return False, "Workflow not found"
        workflow_url += "/runs?per_page=1"
        res = requests.get(workflow_url).json()
        online_hash = res.get("workflow_runs")[0].get("head_sha")[0:7].strip().lower()
        if not online_hash == hash:
            if res.get("workflow_runs")[0].get("status") == "completed":
                return (
                    f"### New commit: {online_hash}\n\n"
                    f"**Full Changelog**: [{hash}...{online_hash}]"
                    "(https://github.com/AvianJay/DCTWFlet/compare/"
                    f"{hash}...{online_hash})",
                    "https://nightly.link/AvianJay/DCTWFlet/"
                    f"workflows/build/main/DCTWFlet-{platform}.zip"
                )
        return False, None
    elif config("update_channel") == "developer":
        return False, None  # No updates for developer channel
    elif config("update_channel") == "release":
        headers = {
            "User-Agent": "DCTWFlet/" + app_version
        }
        r = requests.get(
            "https://api.github.com/repos/AvianJay/DCTWFlet/releases",
            headers=headers,
            timeout=5
        )
        r.raise_for_status()
        releases = r.json()
        if releases:
            latest_version = releases[0]["tag_name"]
            # get file
            for asset in releases[0]["assets"]:
                if platform in asset["name"]:
                    file_url = asset["browser_download_url"]
            if latest_version != app_version:
                return releases[0]["body"] + \
                    f"\n[original]({releases[0]['html_url']})", file_url
    return False, None

def upload_log() -> str:
    log_path = os.environ.get("FLET_APP_CONSOLE")
    if not log_path or not os.path.isfile(log_path):
        raise FileNotFoundError(f"找不到檔案: {log_path}")

    with open(log_path, "rb") as f:
        files = {"file": f}
        r = requests.post(
            "https://0x0.st",
            files=files,
            headers={
                "User-Agent": f"TaiwanBusFlet/{app_version}"
            }
        )

    if r.status_code == 200:
        return r.text.strip()  # 回傳短網址
    else:
        raise Exception(f"{r.status_code} {r.text}")

bot_tags = {
    "music": ("音樂", ft.Icons.MUSIC_NOTE),
    "minigames": ("小遊戲", ft.Icons.GAMES),
    "fun": ("有趣", ft.Icons.EMOJI_EMOTIONS),
    "utility": ("工具", ft.Icons.BUILD),
    "management": ("管理", ft.Icons.SETTINGS),
    "customizable": ("可自訂", ft.Icons.PALETTE),
    "automation": ("自動化", ft.Icons.AUTO_FIX_HIGH),
    "roleplay": ("角色扮演", ft.Icons.PEOPLE),
    "nsfw": ("NSFW", ft.Icons.DO_NOT_DISTURB)
}

# gaming,community,anime,art,hangout,programming,acting,nsfw,roleplay,politics
server_tags = {
    "gaming": ("遊戲", ft.Icons.VIDEOGAME_ASSET),
    "community": ("社群", ft.Icons.GROUP),
    "anime": ("動漫", ft.Icons.FLASH_ON),
    "art": ("藝術", ft.Icons.BRUSH),
    "hangout": ("閒聊", ft.Icons.FORUM),
    "programming": ("程式設計", ft.Icons.CODE),
    "programing": ("程式設計", ft.Icons.CODE),  # bro wtf API 作者的英文可能被當了
    "acting": ("表演", ft.Icons.MIC),
    "nsfw": ("NSFW", ft.Icons.DO_NOT_DISTURB),
    "roleplay": ("角色扮演", ft.Icons.PEOPLE),
    "politics": ("政治", ft.Icons.GAVEL)
}

template_tags = {  # 這根本是亂打的吧
    "community": ("支援", ft.Icons.GROUP),  # 這個好像應該還好
    "gaming": ("遊戲", ft.Icons.VIDEOGAME_ASSET),  # 這個也還好
    "anime": ("大型", ft.Icons.FLASH_ON),  # 我真的搞不懂了 (悲
    "art": ("趣味", ft.Icons.BRUSH),  # ???????
    "nsfw": ("NSFW", ft.Icons.DO_NOT_DISTURB),
}

status_colors = {
    "online": ft.Colors.GREEN,
    "idle": ft.Colors.YELLOW,
    "dnd": ft.Colors.RED,
    "offline": ft.Colors.GREY,
}

status_texts = {
    "online": "線上",
    "idle": "閒置",
    "dnd": "請勿打擾",
    "offline": "離線",
}