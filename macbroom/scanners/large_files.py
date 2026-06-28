"""大文件扫描：找出单个大于阈值（默认 100MB）的文件。

这些往往是用户数据（视频、镜像、归档），删除有风险，整体 recommend=False。
"""

from __future__ import annotations

import os

from macbroom.core.fsutil import HOME, is_icloud_path, iter_large_files, path_mtime
from macbroom.core.i18n import tr
from macbroom.core.model import RISK_MODERATE, RISK_RISKY, Category, ScanItem

CATEGORY = Category(
    key="large_files",
    title="大文件",
    description="单个文件大于 100MB。多为个人数据，删除前请确认。",
    icon="🐘",
    danger=True,
)

MIN_BYTES = 100 * 1024 * 1024  # 100MB
MAX_ITEMS = 400                # 防止结果过多拖垮前端

_ROOTS = [
    os.path.join(HOME, "Downloads"),
    os.path.join(HOME, "Desktop"),
    os.path.join(HOME, "Documents"),
    os.path.join(HOME, "Movies"),
    os.path.join(HOME, "Music"),
    HOME,  # 兜底扫整个 home，靠 fsutil 的跳过名单控量
]

_EXT_NOTE = {
    ".dmg": "large_files.ext.dmg",
    ".pkg": "large_files.ext.pkg",
    ".zip": "large_files.ext.zip",
    ".iso": "large_files.ext.iso",
    ".mp4": "large_files.ext.mp4",
    ".mov": "large_files.ext.mov",
}


def scan(lang: str = "zh") -> list[ScanItem]:
    found: dict[str, tuple[int, float]] = {}
    for path, size, mtime in iter_large_files(_ROOTS, MIN_BYTES, same_device_as=HOME):
        found[path] = (size, mtime)
        if len(found) > MAX_ITEMS * 3:
            break

    items: list[ScanItem] = []
    for path, (size, mtime) in found.items():
        ext = os.path.splitext(path)[1].lower()
        rel = path.replace(HOME, "~")
        note = tr(lang, _EXT_NOTE.get(ext, "large_files.default_note"))
        risk = RISK_MODERATE
        # iCloud 同步目录里的文件，删除会同步到所有设备，提升风险并加显式提示。
        if is_icloud_path(path):
            risk = RISK_RISKY
            note = tr(lang, "icloud.note") + " · " + note
        items.append(ScanItem(
            category=CATEGORY.key,
            name=os.path.basename(path),
            group=os.path.dirname(rel) or "~",
            path=path,
            size=size,
            mtime=mtime,
            note=note,
            recommend=False,
            risk=risk,
        ))

    items.sort(key=lambda x: x.size, reverse=True)
    return items[:MAX_ITEMS]
