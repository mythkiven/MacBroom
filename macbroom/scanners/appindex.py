"""已安装 App 索引：bundle id ↔ 名称映射。

缓存分组与卸载残留判定都依赖它。读取 Info.plist 用 plistlib（兼容二进制 plist），
不额外起子进程。结果做进程内缓存。
"""

from __future__ import annotations

import os
import plistlib

from macbroom.core.fsutil import HOME

# 递归发现各根目录下的 .app（含 Utilities 等子目录），故无需再单列 Utilities。
APP_DIRS = [
    "/Applications",
    "/System/Applications",
    os.path.join(HOME, "Applications"),
]

# 这些 bundle id 前缀属于系统/Apple，残留判定时永不标记。
SYSTEM_PREFIXES = (
    "com.apple.",
    "group.com.apple.",
    "com.apple",
)

# 下钻发现 .app 的最大层数（相对各 APP_DIRS 根）。覆盖 /Applications/Setapp/Foo.app、
# /Applications/厂商/子目录/Foo.app 等常见嵌套，又不至于全盘遍历拖慢索引。
_MAX_APP_DEPTH = 2

_cache: dict | None = None


def _iter_app_bundles(root: str):
    """产出 root 下（含有限层子目录）的 .app 绝对路径，不下钻进 .app 内部。"""
    root = root.rstrip("/")
    base_depth = root.count("/")
    for cur, dirs, _files in os.walk(root, topdown=True, onerror=lambda e: None):
        depth = cur.count("/") - base_depth
        keep = []
        for d in dirs:
            if d.endswith(".app"):
                yield os.path.join(cur, d)  # 命中即收，且不再深入其内部
            elif depth < _MAX_APP_DEPTH and not os.path.islink(os.path.join(cur, d)):
                keep.append(d)
        dirs[:] = keep


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
        for app_path in _iter_app_bundles(d):
            base = os.path.basename(app_path)[:-4]
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


def is_installed_bundle(identifier: str) -> bool:
    """仅按 bundle id 精确匹配已安装 App（残留判定用，避免末段同名误关联）。"""
    return identifier.lower() in index()["bundle_to_name"]


def is_system(identifier: str) -> bool:
    return identifier.lower().startswith(SYSTEM_PREFIXES)
