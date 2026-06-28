"""移动端开发工具遗留扫描。

包含 iOS/Xcode、Android/Android Studio、HarmonyOS/DevEco Studio 的
构建产物、缓存、模拟器、SDK 临时目录和旧设备支持文件。
"""

from __future__ import annotations

import json
import os
import subprocess
from glob import glob

from macbroom.core.fsutil import HOME, dir_size, path_mtime, safe_listdir
from macbroom.core.i18n import tr
from macbroom.core.model import ACTION_RUN, RISK_MODERATE, RISK_RISKY, RISK_SAFE, Category, ScanItem

CATEGORY = Category(
    key="dev_clutter",
    title="开发残留",
    description="iOS、Android、鸿蒙开发工具的构建产物、缓存、模拟器和旧设备支持文件。",
    icon="🛠️",
)

_DEV = os.path.join(HOME, "Library", "Developer")
_XCODE = os.path.join(_DEV, "Xcode")
_ANDROID_SDK = os.path.join(HOME, "Library", "Android", "sdk")
_HARMONY_SDK = os.path.join(HOME, "Library", "Huawei", "Sdk")

# 可整目录清理的项：(展示名, 路径, 说明, 分组, 默认勾选, 风险等级)
_SAFE_DIRS = [
    ("ios.derived_data.name", os.path.join(_XCODE, "DerivedData"),
     "ios.derived_data.note", "group.ios_xcode", True, RISK_SAFE),
    ("ios.sim_cache.name", os.path.join(_DEV, "CoreSimulator", "Caches"),
     "ios.sim_cache.note", "group.ios_xcode", True, RISK_SAFE),
    ("ios.xcode_cache.name", os.path.join(HOME, "Library", "Caches", "com.apple.dt.Xcode"),
     "ios.xcode_cache.note", "group.ios_xcode", True, RISK_SAFE),
    ("ios.device_support.name", os.path.join(_XCODE, "iOS DeviceSupport"),
     "ios.device_support.note", "group.ios_xcode", False, RISK_MODERATE),
    ("ios.watch_support.name", os.path.join(_XCODE, "watchOS DeviceSupport"),
     "ios.support.note", "group.ios_xcode", False, RISK_MODERATE),
    ("ios.tv_support.name", os.path.join(_XCODE, "tvOS DeviceSupport"),
     "ios.support.note", "group.ios_xcode", False, RISK_MODERATE),
    ("ios.archives.name", os.path.join(_XCODE, "Archives"),
     "ios.archives.note", "group.ios_xcode", False, RISK_RISKY),
    ("android.sdk_temp.name", os.path.join(_ANDROID_SDK, ".temp"),
     "android.sdk_temp.note", "group.android", True, RISK_SAFE),
    ("android.sdk_temp.name", os.path.join(_ANDROID_SDK, ".downloadIntermediates"),
     "android.sdk_temp.note", "group.android", True, RISK_SAFE),
    ("android.avd.name", os.path.join(HOME, ".android", "avd"),
     "android.avd.note", "group.android", False, RISK_RISKY),
    ("harmony.hvigor_cache.name", os.path.join(HOME, ".hvigor", "caches"),
     "harmony.hvigor_cache.note", "group.harmonyos", True, RISK_SAFE),
    ("harmony.ohpm_cache.name", os.path.join(HOME, ".ohpm"),
     "harmony.ohpm_cache.note", "group.harmonyos", False, RISK_MODERATE),
    ("harmony.sdk_temp.name", os.path.join(_HARMONY_SDK, ".temp"),
     "harmony.sdk_temp.note", "group.harmonyos", True, RISK_SAFE),
    ("harmony.sdk_temp.name", os.path.join(_HARMONY_SDK, ".downloadIntermediates"),
     "harmony.sdk_temp.note", "group.harmonyos", True, RISK_SAFE),
    ("harmony.sdk_images.name", os.path.join(_HARMONY_SDK, "system-image"),
     "harmony.sdk_images.note", "group.harmonyos", False, RISK_RISKY),
]


_PATTERN_DIRS = [
    ("android.studio_cache.name",
     os.path.join(HOME, "Library", "Caches", "Google", "AndroidStudio*"),
     "android.studio_cache.note", "group.android", True, RISK_SAFE),
    ("android.studio_cache.name",
     os.path.join(HOME, "Library", "Application Support", "Google", "AndroidStudio*", "caches"),
     "android.studio_cache.note", "group.android", True, RISK_SAFE),
    ("harmony.deveco_cache.name",
     os.path.join(HOME, "Library", "Caches", "Huawei", "DevEcoStudio*"),
     "harmony.deveco_cache.note", "group.harmonyos", True, RISK_SAFE),
    ("harmony.deveco_cache.name",
     os.path.join(HOME, "Library", "Application Support", "Huawei", "DevEcoStudio*", "caches"),
     "harmony.deveco_cache.note", "group.harmonyos", True, RISK_SAFE),
]


def _append_dir_item(
    items: list[ScanItem],
    *,
    lang: str,
    name_key: str,
    path: str,
    note_key: str,
    group_key: str,
    recommend: bool,
    risk: str = RISK_MODERATE,
) -> None:
    if not os.path.isdir(path) or os.path.islink(path):
        return
    size = dir_size(path)
    if size <= 0:
        return
    items.append(ScanItem(
        category=CATEGORY.key,
        name=tr(lang, name_key),
        group=tr(lang, group_key),
        path=path,
        size=size,
        mtime=path_mtime(path),
        note=tr(lang, note_key),
        recommend=recommend,
        risk=risk,
    ))


def _scan_android_project_builds(lang: str = "zh", max_items: int = 50) -> list[ScanItem]:
    """Find Gradle ``build`` directories in likely Android projects.

    The traversal is intentionally shallow and skips Library/hidden directories to avoid
    turning this into a full-disk search.
    """
    items: list[ScanItem] = []
    roots = [
        os.path.join(HOME, "AndroidStudioProjects"),
        os.path.join(HOME, "Documents"),
        os.path.join(HOME, "Developer"),
        os.path.join(HOME, "Projects"),
    ]
    for root in roots:
        if not os.path.isdir(root):
            continue
        base_depth = root.rstrip(os.sep).count(os.sep)
        for cur, dirs, files in os.walk(root, topdown=True, onerror=lambda e: None):
            depth = cur.rstrip(os.sep).count(os.sep) - base_depth
            if depth > 4:
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"node_modules", ".git"}]
            if "build" not in dirs:
                continue
            looks_android = any(name in files for name in ("build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"))
            if not looks_android:
                continue
            path = os.path.join(cur, "build")
            size = dir_size(path)
            if size <= 0:
                continue
            rel = cur.replace(HOME, "~")
            items.append(ScanItem(
                category=CATEGORY.key,
                name=tr(lang, "android.gradle_project_build.name",
                        project=os.path.basename(cur) or rel),
                group=tr(lang, "group.android"),
                path=path,
                size=size,
                mtime=path_mtime(path),
                note=tr(lang, "android.gradle_project_build.note", path=rel),
                recommend=True,
                risk=RISK_SAFE,
            ))
            if len(items) >= max_items:
                return items
    return items


def _runtime_name(info: dict) -> str:
    """从 simctl 运行时信息推导可读名，如「iOS 26.5」。"""
    version = info.get("version", "")
    rid = info.get("runtimeIdentifier", "")
    os_name = "iOS"
    if rid:
        suffix = rid.rsplit(".", 1)[-1]      # iOS-26-5
        os_name = suffix.split("-", 1)[0]    # iOS
    return f"{os_name} {version}".strip()


def _scan_runtimes(lang: str = "zh") -> list[ScanItem]:
    """列出模拟器运行时，默认保留最新一个，其余标记可删。"""
    items: list[ScanItem] = []
    try:
        proc = subprocess.run(
            ["xcrun", "simctl", "runtime", "list", "-j"],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0:
            return items
        data = json.loads(proc.stdout or "{}")
    except Exception:
        return items

    runtimes = []
    for rid, info in data.items():
        if not isinstance(info, dict):
            continue
        runtimes.append({
            "id": info.get("identifier", rid),
            "name": _runtime_name(info),
            "version": info.get("version", "0"),
            "size": int(info.get("sizeBytes", 0) or 0),
            "deletable": bool(info.get("deletable", True)),
        })

    if not runtimes:
        return items

    def vkey(r):
        parts = []
        for p in str(r["version"]).split("."):
            parts.append(int(p) if p.isdigit() else 0)
        return parts
    runtimes.sort(key=vkey, reverse=True)
    keep_id = runtimes[0]["id"]

    for r in runtimes:
        keep = r["id"] == keep_id
        deletable = r["deletable"] and not keep
        items.append(ScanItem(
            category=CATEGORY.key,
            name=tr(lang, "ios.runtime.name", runtime=r["name"]),
            group=tr(lang, "group.ios_xcode"),
            action=ACTION_RUN,
            command=f"xcrun simctl runtime delete '{r['id']}'",
            size=r["size"],
            note=(tr(lang, "ios.runtime.keep_note") if keep
                  else tr(lang, "ios.runtime.extra_note")),
            recommend=deletable,
            risk=RISK_SAFE,
        ))
    return items


def scan(lang: str = "zh") -> list[ScanItem]:
    items: list[ScanItem] = []

    for name_key, path, note_key, group_key, recommend, risk in _SAFE_DIRS:
        _append_dir_item(
            items,
            lang=lang,
            name_key=name_key,
            path=path,
            note_key=note_key,
            group_key=group_key,
            recommend=recommend,
            risk=risk,
        )

    for name_key, pattern, note_key, group_key, recommend, risk in _PATTERN_DIRS:
        for path in glob(pattern):
            _append_dir_item(
                items,
                lang=lang,
                name_key=name_key,
                path=path,
                note_key=note_key,
                group_key=group_key,
                recommend=recommend,
                risk=risk,
            )

    # 无效模拟器设备（运行时已删但设备残留）
    items.append(ScanItem(
        category=CATEGORY.key,
        name=tr(lang, "ios.unavailable_devices.name"),
        group=tr(lang, "group.ios_xcode"),
        action=ACTION_RUN,
        command="xcrun simctl delete unavailable >/dev/null 2>&1; echo cleaned",
        size=0,
        note=tr(lang, "ios.unavailable_devices.note"),
        recommend=True,
        risk=RISK_SAFE,
    ))

    items.extend(_scan_runtimes(lang))
    items.extend(_scan_android_project_builds(lang))

    items.sort(key=lambda x: x.size, reverse=True)
    return items
