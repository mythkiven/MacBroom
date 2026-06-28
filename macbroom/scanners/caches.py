"""缓存扫描：按软件维度列出可安全删除、能自动重建的缓存。

只收录「删了不丢数据、应用会自动重建」的缓存目录，因此整体 recommend=True。
"""

from __future__ import annotations

import os

from macbroom.core.fsutil import HOME, dir_size, path_mtime, safe_listdir
from macbroom.core.i18n import tr
from macbroom.core.model import ACTION_RUN, RISK_SAFE, Category, ScanItem
from . import appindex

CATEGORY = Category(
    key="caches",
    title="应用缓存",
    description="可自动重建的缓存，按软件分组。删除不会丢失数据。",
    icon="🧹",
)

# 用户级缓存根目录：每个子目录通常对应一个 App（bundle id 命名）。
_USER_CACHE_ROOTS = [
    os.path.join(HOME, "Library", "Caches"),
]

# 开发者工具缓存：路径固定、可放心清。(name, path, 是否走命令)
_DEV_CACHES = [
    ("cache.npm", os.path.join(HOME, ".npm", "_cacache")),
    ("cache.yarn", os.path.join(HOME, "Library", "Caches", "Yarn")),
    ("cache.pip", os.path.join(HOME, "Library", "Caches", "pip")),
    ("cache.go", os.path.join(HOME, "Library", "Caches", "go-build")),
    ("cache.gradle", os.path.join(HOME, ".gradle", "caches")),
    ("cache.cocoapods", os.path.join(HOME, "Library", "Caches", "CocoaPods")),
    ("cache.homebrew", os.path.join(HOME, "Library", "Caches", "Homebrew")),
    ("cache.dot_cache", os.path.join(HOME, ".cache")),
    ("cache.pnpm", os.path.join(HOME, "Library", "pnpm", "store")),
    ("cache.puppeteer", os.path.join(HOME, ".cache", "puppeteer")),
]

# 浏览器缓存：~/Library/Caches 的通用扫描覆盖不到藏在 Application Support
# 配置目录里的 Cache，这里显式补齐。删除后浏览器会自动重建，不影响登录态。
_APP_SUPPORT = os.path.join(HOME, "Library", "Application Support")
_BROWSER_CACHES = [
    ("cache.browser.chrome", os.path.join(_APP_SUPPORT, "Google", "Chrome", "Default", "Cache")),
    ("cache.browser.chrome", os.path.join(_APP_SUPPORT, "Google", "Chrome", "Default", "Code Cache")),
    ("cache.browser.edge", os.path.join(_APP_SUPPORT, "Microsoft Edge", "Default", "Cache")),
    ("cache.browser.brave", os.path.join(_APP_SUPPORT, "BraveSoftware", "Brave-Browser", "Default", "Cache")),
    ("cache.browser.arc", os.path.join(HOME, "Library", "Caches", "company.thebrowser.Browser")),
    ("cache.browser.firefox", os.path.join(HOME, "Library", "Caches", "Firefox")),
]

# 常见桌面应用（多为 Electron/Chromium）的缓存目录通常藏在 Application Support 下，
# ~/Library/Caches 的通用扫描覆盖不到，这里按应用显式补齐。只收录明确的缓存子目录，
# 绝不触碰账号/本地数据目录。(应用名, 缓存子目录的绝对路径)
_APP_CACHES = [
    ("Slack", os.path.join(_APP_SUPPORT, "Slack", "Cache")),
    ("Slack", os.path.join(_APP_SUPPORT, "Slack", "Code Cache")),
    ("Slack", os.path.join(_APP_SUPPORT, "Slack", "GPUCache")),
    ("Slack", os.path.join(_APP_SUPPORT, "Slack", "Service Worker", "CacheStorage")),
    ("Discord", os.path.join(_APP_SUPPORT, "discord", "Cache")),
    ("Discord", os.path.join(_APP_SUPPORT, "discord", "Code Cache")),
    ("Discord", os.path.join(_APP_SUPPORT, "discord", "GPUCache")),
    ("VS Code", os.path.join(_APP_SUPPORT, "Code", "Cache")),
    ("VS Code", os.path.join(_APP_SUPPORT, "Code", "CachedData")),
    ("VS Code", os.path.join(_APP_SUPPORT, "Code", "Code Cache")),
    ("VS Code", os.path.join(_APP_SUPPORT, "Code", "GPUCache")),
    ("Microsoft Teams", os.path.join(_APP_SUPPORT, "Microsoft", "Teams", "Cache")),
    ("Microsoft Teams", os.path.join(_APP_SUPPORT, "Microsoft", "Teams", "Code Cache")),
    ("Microsoft Teams", os.path.join(_APP_SUPPORT, "Microsoft", "Teams", "GPUCache")),
    ("Spotify", os.path.join(_APP_SUPPORT, "Spotify", "PersistentCache")),
    ("Steam", os.path.join(_APP_SUPPORT, "Steam", "appcache")),
    ("Steam", os.path.join(_APP_SUPPORT, "Steam", "htmlcache")),
]

# 这些子目录名即便在 ~/Library/Caches 下也跳过（不是普通可弃缓存）。
_SKIP_CACHE_NAMES = {".DS_Store"}

_MIN = 1024 * 1024  # 1MB 以下不单列，避免噪音


def scan(lang: str = "zh") -> list[ScanItem]:
    items: list[ScanItem] = []
    seen_paths: set[str] = set()

    for root in _USER_CACHE_ROOTS:
        for entry in safe_listdir(root):
            if entry in _SKIP_CACHE_NAMES:
                continue
            path = os.path.join(root, entry)
            if not os.path.isdir(path) or os.path.islink(path):
                continue
            size = dir_size(path)
            if size < _MIN:
                continue
            seen_paths.add(os.path.realpath(path))
            app = appindex.app_name_for(entry)
            items.append(ScanItem(
                category=CATEGORY.key,
                name=tr(lang, "cache.app.name", app=app),
                group=app or entry,
                path=path,
                size=size,
                mtime=path_mtime(path),
                note=tr(lang, "cache.app.note"),
                recommend=True,
                risk=RISK_SAFE,
            ))

    for name_key, path in _DEV_CACHES:
        if not os.path.isdir(path) or os.path.islink(path):
            continue
        real = os.path.realpath(path)
        if real in seen_paths:
            continue
        size = dir_size(path)
        if size < _MIN:
            continue
        seen_paths.add(real)
        items.append(ScanItem(
            category=CATEGORY.key,
            name=tr(lang, name_key),
            group=tr(lang, "group.developer_tools"),
            path=path,
            size=size,
            mtime=path_mtime(path),
            note=tr(lang, "cache.dev.note"),
            recommend=True,
            risk=RISK_SAFE,
        ))

    for name_key, path in _BROWSER_CACHES:
        if not os.path.isdir(path) or os.path.islink(path):
            continue
        real = os.path.realpath(path)
        if real in seen_paths:
            continue
        size = dir_size(path)
        if size < _MIN:
            continue
        seen_paths.add(real)
        items.append(ScanItem(
            category=CATEGORY.key,
            name=tr(lang, name_key),
            group=tr(lang, "group.browsers"),
            path=path,
            size=size,
            mtime=path_mtime(path),
            note=tr(lang, "cache.browser.note"),
            recommend=True,
            risk=RISK_SAFE,
        ))

    for app_label, path in _APP_CACHES:
        if not os.path.isdir(path) or os.path.islink(path):
            continue
        real = os.path.realpath(path)
        if real in seen_paths:
            continue
        size = dir_size(path)
        if size < _MIN:
            continue
        seen_paths.add(real)
        items.append(ScanItem(
            category=CATEGORY.key,
            name=f"{app_label} · {os.path.basename(path)}",
            group=app_label,
            path=path,
            size=size,
            mtime=path_mtime(path),
            note=tr(lang, "cache.app_known.note"),
            recommend=True,
            risk=RISK_SAFE,
        ))

    # QuickLook 缩略图缓存：走命令重建更干净
    items.append(ScanItem(
        category=CATEGORY.key,
        name=tr(lang, "cache.quicklook.name"),
        group=tr(lang, "group.system"),
        action=ACTION_RUN,
        command="qlmanage -r cache >/dev/null 2>&1; echo done",
        size=0,
        note=tr(lang, "cache.quicklook.note"),
        recommend=False,
        risk=RISK_SAFE,
    ))

    items.sort(key=lambda x: x.size, reverse=True)
    return items
