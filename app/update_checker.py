#/ =====================================================================================
#/  Update checker — fetches latest release version from GitHub
#/  Проверка обновлений — получает номер последнего релиза с GitHub
#/
#/  HOW IT WORKS:
#/    1. On first call, fetches https://api.github.com/repos/.../releases/latest
#/    2. Caches result in .update_cache.json (TTL 1 hour)
#/    3. Compares with local VERSION file
#/    4. If GitHub version > local version → update_available=True
#/
#/  Disable entirely: set CHECK_UPDATES=false in .env
#/ =====================================================================================

import json
import os
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

BASE_DIR = Path(__file__).resolve().parent.parent
VERSION_FILE = BASE_DIR / "VERSION"              # Local version (e.g. "1.0.0")
CACHE_FILE = BASE_DIR / ".update_cache.json"     # Cached GitHub response
CACHE_TTL = 3600                                  # 1 hour cache

GITHUB_OWNER = "AnonimPython"
GITHUB_REPO = "Private-School"


def get_current_version() -> str:
    """Read local version from VERSION file."""
    try:
        return VERSION_FILE.read_text().strip()
    except FileNotFoundError:
        return "0.0.0"


def parse_version(v: str) -> tuple:
    """Convert '1.2.3' → (1, 2, 3) for comparison."""
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _load_cache() -> dict:
    """Load cached GitHub response from disk."""
    try:
        return json.loads(CACHE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(data: dict) -> None:
    """Save GitHub response to disk cache."""
    CACHE_FILE.write_text(json.dumps(data, indent=2))


def check_latest_version() -> dict:
    """
    Fetch the latest release from GitHub (or return cached data).

    Returns:
        dict with keys: latest_version, release_url, release_name, timestamp
    """
    cache = _load_cache()
    now = time.time()

    # Return cached data if still fresh
    if cache.get("timestamp") and (now - cache["timestamp"]) < CACHE_TTL:
        return cache

    # Fetch from GitHub API
    try:
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
        req = Request(url, headers={"User-Agent": f"{GITHUB_REPO}-update-checker"})
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())

        result = {
            "latest_version": data.get("tag_name", "").lstrip("v"),
            "release_url": data.get("html_url", ""),
            "release_name": data.get("name", ""),
            "timestamp": now,
        }
        _save_cache(result)
        return result

    # On any error (no releases, no network, etc.) — return cache or empty
    except (URLError, json.JSONDecodeError, Exception):
        return cache or {"latest_version": None, "release_url": None, "timestamp": now}


def get_update_info() -> dict:
    """
    Compare local vs remote version and return update status.

    Returns:
        dict: current_version, latest_version, update_available (bool), release_url
    """
    current = get_current_version()
    current_v = parse_version(current)

    latest_data = check_latest_version()
    latest = latest_data.get("latest_version") or current
    latest_v = parse_version(latest)

    return {
        "current_version": current,
        "latest_version": latest,
        "update_available": latest_v > current_v,
        "release_url": latest_data.get("release_url", ""),
    }
