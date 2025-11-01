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
from pathlib import Path
import base64
from flask import Flask, send_file
import random
import string

app = Flask(__name__)
port = random.randint(10000, 60000)

app_version = 1
config_version = 1

platform = os.getenv("FLET_PLATFORM")
datadir = os.getenv("FLET_APP_STORAGE_DATA", ".")
rel_datadir = os.path.relpath(datadir, os.getcwd())
rel_datadir = rel_datadir.replace("\\", "/")  # for Windows compatibility
if not os.path.exists(rel_datadir):
    os.makedirs(rel_datadir)
print("Data directory:", rel_datadir)

default_config = {
    "config_version": config_version,
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

cache_limiter = threading.Semaphore(1)
def cache(key, value=None, mode="r", expire=None):
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
                if cache_item["expire"] is None or cache_item["expire"] > datetime.now().timestamp():
                    cache_limiter.release()
                    return cache_item["value"]
                else:
                    del cache_data[key]
                    with open(cache_path, "w") as f:
                        json.dump(cache_data, f)
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

BASE_URL = "https://dctw.xyz"

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
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(image_path, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        images = cache("images", mode="r") or {}
        images[original_url] = image_path
        cache("images", images, mode="w")
    except requests.RequestException as e:
        print(f"Error caching image from {url}: {e}")

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

    images = cache("images", mode="r") or {}

    if url in images:
        # to image cache server
        id = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        image_ids[id] = url
        images[url] = f"http://127.0.0.1:{port}/image/{id}"
        if callback:
            callback()
        print("Image found in cache:", images[url])
        return images[url]
    else:
        if callback:
            def _cache_image_with_callback(url, callback):
                _cache_image(url)
                callback()
            threading.Thread(target=_cache_image_with_callback, args=(url, callback)).start()
        else:
            threading.Thread(target=_cache_image, args=(url,)).start()
            print(f"Caching image in background: {url}")
            return url  # Return original URL until cached image is ready

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
    cache("images", mode="w", value={})

bots, servers, templates = [], [], []

def get_bots(force=False):
    global bots
    if not force:
        bots = cache("bots")
        if bots:
            return bots
    try:
        response = requests.get("https://dctw.xyz/api/v1/bots")
        response.raise_for_status()
        bots = response.json()
        # sort by bump_at (datetime TZ)
        bots.sort(key=lambda x: datetime.fromisoformat(x.get("bump_at", "")).astimezone(), reverse=True)
        cache("bots", bots, mode="w", expire=600)
        return bots
    except requests.RequestException as e:
        print(f"Error fetching bots: {e}")

def get_servers(force=False):
    global servers
    if not force:
        servers = cache("servers")
        if servers:
            return servers
    try:
        response = requests.get("https://dctw.xyz/api/v1/servers")
        response.raise_for_status()
        servers = response.json()
        cache("servers", servers, mode="w", expire=600)
        return servers
    except requests.RequestException as e:
        print(f"Error fetching servers: {e}")

def get_templates(force=False):
    global templates
    if not force:
        templates = cache("templates")
        if templates:
            return templates
    try:
        response = requests.get("https://dctw.xyz/api/v1/templates")
        response.raise_for_status()
        templates = response.json()
        cache("templates", templates, mode="w", expire=600)
        return templates
    except requests.RequestException as e:
        print(f"Error fetching templates: {e}")

# image cache server
# 暴力解 超讚
image_ids = {}
@app.route('/image/<path:id>')
def image_cache(id):
    images = cache("images", mode="r") or {}
    url = image_ids.get(id, id)
    if url in images:
        return send_file(images[url])
    else:
        return "Image not found", 404

def run_image_cache_server():
    app.run(host="127.0.0.1", port=port)

threading.Thread(target=run_image_cache_server, daemon=True).start()
