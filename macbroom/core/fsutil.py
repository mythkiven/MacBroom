"""文件系统工具：体量计算、安全遍历、受保护路径判定。

所有扫描器共用这里的能力，避免各自重写 du / walk 逻辑。
"""

from __future__ import annotations

import os
from typing import Iterator

HOME = os.path.expanduser("~")

# iCloud Drive 在本地的根目录。位于其下的文件删除后会同步到所有设备，需高风险对待。
ICLOUD_ROOT = os.path.join(HOME, "Library", "Mobile Documents", "com~apple~CloudDocs")


def is_icloud_path(path: str) -> bool:
    """判断路径是否落在 iCloud 同步范围内。

    覆盖两种情况：
    1. 直接位于 iCloud Drive（~/Library/Mobile Documents/com~apple~CloudDocs）；
    2. 开启「桌面与文档存入 iCloud」后，~/Desktop、~/Documents 实际被 iCloud 接管
       （其 realpath 会指向 Mobile Documents 下）。
    """
    try:
        real = os.path.realpath(path)
    except OSError:
        return False
    mobile_docs = os.path.join(HOME, "Library", "Mobile Documents")
    return real == mobile_docs or real.startswith(mobile_docs + os.sep)


# 绝不触碰的路径前缀（即便扫描到也不允许作为删除项）。
# 注意：is_protected 用 realpath 比对，故这里写「真实路径」前缀——
# 例如 /etc、/var 会被 realpath 解析为 /private/etc、/private/var，需以后者登记。
PROTECTED_PREFIXES = (
    "/System",
    "/usr",
    "/bin",
    "/sbin",
    "/Applications",       # 已安装 App：扫描器从不经废纸篓删整个 App，加一道硬阻断
    "/private/etc",        # /etc 的真实路径
    "/private/var",        # /var 的真实路径（含 db / 系统状态），扫描器不在此清理
    "/Library/Apple",
    os.path.join(HOME, "Library", "Keychains"),
    os.path.join(HOME, ".ssh"),
    os.path.join(HOME, ".gnupg"),
)

# 大文件遍历时跳过的目录名（性能 + 噪音控制）。
SKIP_DIR_NAMES = {
    ".git",
    "node_modules",
    ".Trash",
    "CoreSimulator",          # iOS 模拟器单独扫
    "DerivedData",            # iOS 构建产物单独扫
}

# 大文件遍历时跳过的目录后缀（macOS 的「包」本质是目录）。
SKIP_DIR_SUFFIXES = (
    ".app",
    ".framework",
    ".photoslibrary",
    ".photolibrary",
    ".pkg",
)


def actual_size(st: os.stat_result) -> int:
    """实际占用磁盘的字节数（按 512B 块计），正确处理稀疏文件。

    稀疏镜像（OrbStack/VM/磁盘镜像）的 st_size 是逻辑大小，可能远大于真实占用，
    用 st_blocks 才不会虚报可释放空间。
    """
    try:
        return st.st_blocks * 512
    except AttributeError:
        return st.st_size


def human_size(num: float) -> str:
    """字节数转可读字符串。"""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:.1f} {unit}" if unit != "B" else f"{int(num)} B"
        num /= 1024.0
    return f"{num:.1f} PB"


# Freedesktop 缓存目录标记（CACHEDIR.TAG）及少数工具使用的 CACHEDIR.txt。
_CACHE_MARKERS = ("CACHEDIR.TAG", "CACHEDIR.txt")


def is_marked_cache_dir(path: str) -> bool:
    """目录内是否带有标准缓存标记文件。"""
    if not path or not os.path.isdir(path):
        return False
    return any(os.path.isfile(os.path.join(path, name)) for name in _CACHE_MARKERS)


def is_protected(path: str) -> bool:
    real = os.path.realpath(path)
    return any(real == p or real.startswith(p + os.sep) for p in PROTECTED_PREFIXES)


def safe_listdir(path: str) -> list[str]:
    try:
        return os.listdir(path)
    except (PermissionError, FileNotFoundError, NotADirectoryError, OSError):
        return []


def dir_size(path: str, follow_symlinks: bool = False) -> int:
    """递归计算目录占用，吞掉权限/损坏错误。文件则返回自身大小。"""
    try:
        st = os.lstat(path)
    except OSError:
        return 0
    if os.path.islink(path):
        return 0
    if not os.path.isdir(path):
        return actual_size(st)
    total = 0
    for root, dirs, files in os.walk(path, topdown=True, onerror=lambda e: None,
                                     followlinks=follow_symlinks):
        for name in files:
            fp = os.path.join(root, name)
            try:
                if not os.path.islink(fp):
                    total += actual_size(os.lstat(fp))
            except OSError:
                continue
    return total


def path_mtime(path: str) -> float:
    try:
        return os.lstat(path).st_mtime
    except OSError:
        return 0.0


def iter_large_files(roots: list[str], min_bytes: int,
                     same_device_as: str | None = None) -> Iterator[tuple[str, int, float]]:
    """遍历 roots 下大于 min_bytes 的普通文件，产出 (path, size, mtime)。

    会跳过符号链接、受保护路径、SKIP 目录、跨设备挂载点。
    """
    base_dev = None
    if same_device_as:
        try:
            base_dev = os.lstat(same_device_as).st_dev
        except OSError:
            base_dev = None

    seen: set[str] = set()
    for root in roots:
        root = os.path.realpath(root)
        if root in seen:
            continue
        seen.add(root)
        for cur, dirs, files in os.walk(root, topdown=True, onerror=lambda e: None):
            # 原地裁剪要跳过的子目录
            pruned = []
            for d in dirs:
                full = os.path.join(cur, d)
                if os.path.islink(full):
                    continue
                if d in SKIP_DIR_NAMES or d.endswith(SKIP_DIR_SUFFIXES):
                    continue
                if base_dev is not None:
                    try:
                        if os.lstat(full).st_dev != base_dev:
                            continue
                    except OSError:
                        continue
                pruned.append(d)
            dirs[:] = pruned

            for name in files:
                fp = os.path.join(cur, name)
                try:
                    st = os.lstat(fp)
                except OSError:
                    continue
                if os.path.islink(fp):
                    continue
                size = actual_size(st)
                if size >= min_bytes:
                    yield fp, size, st.st_mtime
