"""卸载残留扫描：找出已卸载 App 遗留的支持文件、偏好、日志、容器等。

判定是启发式的：目录名映射不到任何已安装 App、且不属于系统/Apple，
才标记为「疑似残留」。为安全起见整体 recommend=False，交用户复核。
"""

from __future__ import annotations

import os

from macbroom.core.fsutil import HOME, actual_size, dir_size, path_mtime, safe_listdir
from macbroom.core.i18n import tr
from macbroom.core.model import RISK_MODERATE, Category, ScanItem
from . import appindex

CATEGORY = Category(
    key="leftovers",
    title="卸载残留",
    description="疑似已卸载 App 遗留的支持文件 / 日志 / 偏好。请复核后删除。",
    icon="👻",
    danger=True,
)

# (展示前缀, 目录, 条目是否为 .plist 文件)
_SCAN_LOCATIONS = [
    ("leftover.application_support", os.path.join(HOME, "Library", "Application Support"), False),
    ("leftover.containers", os.path.join(HOME, "Library", "Containers"), False),
    ("leftover.group_containers", os.path.join(HOME, "Library", "Group Containers"), False),
    ("leftover.logs", os.path.join(HOME, "Library", "Logs"), False),
    ("leftover.saved_state", os.path.join(HOME, "Library", "Saved Application State"), False),
    ("leftover.http_storage", os.path.join(HOME, "Library", "HTTPStorages"), False),
    ("leftover.preferences", os.path.join(HOME, "Library", "Preferences"), True),
]

# Application Support 下这些是系统/共享目录，跳过不判残留。
_SKIP_NAMES = {
    "com.apple", "CrashReporter", "MobileSync", "AddressBook", "Knowledge",
    "CallHistoryDB", "icdd", "SyncServices", ".DS_Store", "App Store",
    "CloudDocs", "Google", "Microsoft",  # 这些误判代价高，保守跳过
}

_MIN = 512 * 1024  # 512KB 以下忽略


def _identifier_from_entry(entry: str, is_plist: bool) -> str:
    name = entry
    if is_plist and name.endswith(".plist"):
        name = name[:-6]
    # Saved Application State: com.foo.bar.savedState
    if name.endswith(".savedState"):
        name = name[: -len(".savedState")]
    if name.endswith(".binarycookies"):
        name = name[: -len(".binarycookies")]
    return name


def scan(lang: str = "zh") -> list[ScanItem]:
    items: list[ScanItem] = []
    appindex.index()  # 预热

    for label_key, base, is_plist in _SCAN_LOCATIONS:
        for entry in safe_listdir(base):
            if entry in _SKIP_NAMES or entry.startswith("."):
                continue
            ident = _identifier_from_entry(entry, is_plist)
            if appindex.is_system(ident) or any(ident.startswith(s) for s in _SKIP_NAMES):
                continue
            # 只对「像 bundle id」的项做残留判定，降低误报
            looks_like_bundle = ident.count(".") >= 2
            if not looks_like_bundle:
                continue
            if appindex.is_installed(ident):
                continue

            path = os.path.join(base, entry)
            if os.path.islink(path):
                continue
            size = dir_size(path) if os.path.isdir(path) else (
                actual_size(os.lstat(path)) if os.path.exists(path) else 0)
            if size < _MIN:
                continue
            app = appindex.app_name_for(ident)
            label = tr(lang, label_key)
            items.append(ScanItem(
                category=CATEGORY.key,
                name=tr(lang, "leftover.name", label=label, app=app),
                group=app or ident,
                path=path,
                size=size,
                mtime=path_mtime(path),
                note=tr(lang, "leftover.note", identifier=ident),
                recommend=False,
                risk=RISK_MODERATE,
            ))

    items.sort(key=lambda x: x.size, reverse=True)
    return items
