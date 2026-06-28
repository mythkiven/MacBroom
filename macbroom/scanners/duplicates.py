"""重复文件扫描：找出内容完全相同的文件。

为兼顾速度与准确，分三级收敛，逐级只对「仍有重复可能」的候选做更贵的计算：
1. 按文件大小分组（最便宜，先排除独一无二的大小）。
2. 对同大小文件算「部分哈希」（首尾各 8KB），快速排除大部分非重复项。
3. 对仍同组的文件算完整 SHA-256 确认逐字节相同。

重复文件多为个人数据（照片、视频、下载），删除不可逆，整体标记为高风险，
默认不勾选；每组保留最新的一份不建议删除，其余作为候选列出。
"""

from __future__ import annotations

import hashlib
import os
from collections import defaultdict

from macbroom.core.fsutil import HOME, human_size, is_icloud_path, iter_large_files, path_mtime
from macbroom.core.i18n import tr
from macbroom.core.model import RISK_RISKY, Category, ScanItem

CATEGORY = Category(
    key="duplicates",
    title="重复文件",
    description="内容完全相同的文件，逐字节校验。删除前请确认保留哪一份。",
    icon="🧬",
    danger=True,
)

_ROOTS = [
    os.path.join(HOME, "Downloads"),
    os.path.join(HOME, "Desktop"),
    os.path.join(HOME, "Documents"),
    os.path.join(HOME, "Movies"),
    os.path.join(HOME, "Music"),
    os.path.join(HOME, "Pictures"),
]

_MIN_BYTES = 1024 * 1024   # 1MB 以下不参与查重（噪音大、收益低）
_PARTIAL = 8 * 1024        # 部分哈希读取的字节数（首尾各取）
_MAX_GROUPS = 60           # 最多列出的重复组数


def _partial_hash(path: str, size: int) -> str | None:
    try:
        with open(path, "rb") as f:
            head = f.read(_PARTIAL)
            if size > _PARTIAL * 2:
                f.seek(max(0, size - _PARTIAL))
                tail = f.read(_PARTIAL)
            else:
                tail = b""
        return hashlib.blake2b(head + tail, digest_size=16).hexdigest()
    except OSError:
        return None


def _full_hash(path: str) -> str | None:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def scan(lang: str = "zh") -> list[ScanItem]:
    # 1) 按大小分组
    by_size: dict[int, list[str]] = defaultdict(list)
    for path, size, _ in iter_large_files(_ROOTS, _MIN_BYTES, same_device_as=HOME):
        by_size[size].append(path)

    # 2) 同大小 → 部分哈希
    by_partial: dict[tuple[int, str], list[str]] = defaultdict(list)
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        for p in paths:
            ph = _partial_hash(p, size)
            if ph is not None:
                by_partial[(size, ph)].append(p)

    # 3) 部分哈希同组 → 完整哈希确认
    by_full: dict[str, list[str]] = defaultdict(list)
    full_size: dict[str, int] = {}
    for (size, _), paths in by_partial.items():
        if len(paths) < 2:
            continue
        for p in paths:
            fh = _full_hash(p)
            if fh is not None:
                by_full[fh].append(p)
                full_size[fh] = size

    items: list[ScanItem] = []
    groups = 0
    # 重复组按「可释放空间」从大到小排序
    ordered = sorted(
        ((fh, paths) for fh, paths in by_full.items() if len(paths) >= 2),
        key=lambda kv: full_size[kv[0]] * (len(kv[1]) - 1),
        reverse=True,
    )
    for fh, paths in ordered:
        if groups >= _MAX_GROUPS:
            break
        groups += 1
        size = full_size[fh]
        # 保留最新的一份，其余作为可删候选
        paths_sorted = sorted(paths, key=path_mtime, reverse=True)
        keep = paths_sorted[0]
        label = tr(lang, "duplicates.group",
                   name=os.path.basename(keep), size=human_size(size))
        for idx, p in enumerate(paths_sorted):
            is_keep = p == keep
            rel = p.replace(HOME, "~")
            note = (tr(lang, "duplicates.keep_note", path=rel) if is_keep
                    else tr(lang, "duplicates.dup_note", path=rel))
            if is_icloud_path(p):
                note = tr(lang, "icloud.note") + " · " + note
            items.append(ScanItem(
                category=CATEGORY.key,
                name=os.path.basename(p),
                group=label,
                path=p,
                size=size,
                mtime=path_mtime(p),
                note=note,
                recommend=False,
                deletable=not is_keep,  # 保留项（每组最新一份）禁止勾选删除
                risk=RISK_RISKY,
            ))
    return items
