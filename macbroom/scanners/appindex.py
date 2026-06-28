"""已安装 App 索引：bundle id ↔ 名称映射。

缓存分组与卸载残留判定都依赖它。读取 Info.plist 用 plistlib（兼容二进制 plist），
不额外起子进程。结果做进程内缓存。
"""

from __future__ import annotations

import os
import plistlib

from macbroom.core.fsutil import HOME, safe_listdir

APP_DIRS = [
    "/Applications",
    "/Applications/Utilities",
    "/System/Applications",
    "/System/Applications/Utilities",
    os.path.join(HOME, "Applications"),
]

# 这些 bundle id 前缀属于系统/Apple，残留判定时永不标记。
SYSTEM_PREFIXES = (
    "com.apple.",
    "group.com.apple.",
    "com.apple",
)

_cache: dict | None = None


def _read_bundle_id(app_path: str) -> str | None:
    plist = os.path.join(app_path, "Contents", "Info.plist")
    try:
        with open(plist, "rb") as f:
            data = plistlib.load(f)
        return data.get("CFBundleIdentifier")
    except Exception:
        return None


def _build() -> dict:
    bundle_to_name: dict[str, str] = {}
    names: set[str] = set()
    for d in APP_DIRS:
        for entry in safe_listdir(d):
            if not entry.endswith(".app"):
                continue
            app_path = os.path.join(d, entry)
            base = entry[:-4]
            names.add(base.lower())
            bid = _read_bundle_id(app_path)
            if bid:
                bundle_to_name[bid.lower()] = base
    return {"bundle_to_name": bundle_to_name, "names": names}


def index() -> dict:
    global _cache
    if _cache is None:
        _cache = _build()
    return _cache


def app_name_for(identifier: str) -> str | None:
    """把一个 bundle id / 目录名 尽量映射到可读 App 名。"""
    idx = index()
    low = identifier.lower()
    if low in idx["bundle_to_name"]:
        return idx["bundle_to_name"][low]
    # com.foo.Bar -> Bar
    if "." in identifier:
        return identifier.rsplit(".", 1)[-1]
    return identifier


def is_installed(identifier: str) -> bool:
    idx = index()
    low = identifier.lower()
    if low in idx["bundle_to_name"]:
        return True
    if low in idx["names"]:
        return True
    # 目录名是 bundle id：取末段与 App 名比对
    if "." in identifier:
        tail = identifier.rsplit(".", 1)[-1].lower()
        if tail in idx["names"]:
            return True
    return False


def is_installed_bundle(identifier: str) -> bool:
    """仅按 bundle id 精确匹配已安装 App（残留判定用，避免末段同名误关联）。"""
    return identifier.lower() in index()["bundle_to_name"]


def is_system(identifier: str) -> bool:
    return identifier.lower().startswith(SYSTEM_PREFIXES)
