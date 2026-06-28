"""登录项 / 启动项扫描：找出开机自启的「孤儿」LaunchAgents / LaunchDaemons。

macOS 的开机自启很多通过 ~/Library/LaunchAgents、/Library/LaunchAgents、
/Library/LaunchDaemons 下的 .plist 注册。App 卸载后这些 plist 常被遗留，指向一个
已不存在的程序——它们就是用户在「系统设置 › 通用 › 登录项」里看到的报错「后台项」。

本扫描器只标记「指向的程序已不存在」的孤儿项（最明确、最安全的可清理信号），
绝不动 Apple 自带项，也不动指向有效程序的正常启动项。
"""

from __future__ import annotations

import os
import plistlib
import shutil

from macbroom.core.fsutil import HOME, actual_size
from macbroom.core.i18n import tr
from macbroom.core.model import ACTION_MANUAL, RISK_MODERATE, Category, ScanItem

CATEGORY = Category(
    key="login_items",
    title="登录项 / 启动项",
    description="开机自启的 LaunchAgents / LaunchDaemons，重点找出指向已删除程序的孤儿残留项。",
    icon="🚀",
    danger=True,
)

# (目录, 是否需要 sudo 才能删)
_USER_AGENTS = os.path.join(HOME, "Library", "LaunchAgents")
_GLOBAL_DIRS = [
    "/Library/LaunchAgents",
    "/Library/LaunchDaemons",
]

# 内建命令解释器等始终存在的可执行，跳过判定（避免误判）。
_ALWAYS_OK_PREFIXES = ("/System/", "/usr/", "/bin/", "/sbin/")


def _target_executable(data: dict) -> str | None:
    """从 plist 解析出它启动的可执行路径 / 命令名。"""
    prog = data.get("Program")
    if isinstance(prog, str) and prog.strip():
        return prog.strip()
    args = data.get("ProgramArguments")
    if isinstance(args, list) and args and isinstance(args[0], str):
        return args[0].strip()
    bundle = data.get("BundleProgram")
    if isinstance(bundle, str) and bundle.strip():
        return bundle.strip()
    return None


def _executable_exists(target: str) -> bool:
    if target.startswith(_ALWAYS_OK_PREFIXES):
        return True
    if "/" in target:
        return os.path.exists(os.path.expanduser(target))
    # 仅是命令名：在 PATH 里找
    return shutil.which(target) is not None


def _is_apple(label: str, filename: str) -> bool:
    name = (label or filename).lower()
    return name.startswith("com.apple.") or name.startswith("apple.")


def _scan_dir(directory: str, needs_sudo: bool, lang: str) -> list[ScanItem]:
    items: list[ScanItem] = []
    try:
        entries = os.listdir(directory)
    except OSError:
        return items
    for entry in entries:
        if not entry.endswith(".plist"):
            continue
        path = os.path.join(directory, entry)
        if os.path.islink(path) or not os.path.isfile(path):
            continue
        try:
            with open(path, "rb") as f:
                data = plistlib.load(f)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        label = str(data.get("Label") or "")
        filename = entry[:-6]  # 去掉 .plist
        if _is_apple(label, filename):
            continue
        target = _target_executable(data)
        if not target:
            continue
        if _executable_exists(target):
            continue  # 指向有效程序的正常启动项，不动

        try:
            size = actual_size(os.lstat(path))
        except OSError:
            size = 0
        display = label or filename
        if needs_sudo:
            items.append(ScanItem(
                category=CATEGORY.key,
                name=tr(lang, "login_items.orphan.name", label=display),
                group=tr(lang, "login_items.group.global"),
                path=path,
                action=ACTION_MANUAL,
                command=f"sudo rm {_shquote(path)}",
                size=size,
                needs_sudo=True,
                note=tr(lang, "login_items.orphan.note_sudo", target=target),
                recommend=False,
                risk=RISK_MODERATE,
            ))
        else:
            items.append(ScanItem(
                category=CATEGORY.key,
                name=tr(lang, "login_items.orphan.name", label=display),
                group=tr(lang, "login_items.group.user"),
                path=path,
                size=size,
                note=tr(lang, "login_items.orphan.note", target=target),
                recommend=False,
                risk=RISK_MODERATE,
            ))
    return items


def _shquote(path: str) -> str:
    return "'" + path.replace("'", "'\\''") + "'"


def scan(lang: str = "zh") -> list[ScanItem]:
    items = _scan_dir(_USER_AGENTS, needs_sudo=False, lang=lang)
    for d in _GLOBAL_DIRS:
        items.extend(_scan_dir(d, needs_sudo=True, lang=lang))
    items.sort(key=lambda x: x.name)
    return items
