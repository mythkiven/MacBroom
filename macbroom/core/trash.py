"""安全删除：一律走 macOS「废纸篓」，可一键还原。

设计原则（对应全局「自测数据安全」硬约束）：
- 默认不做不可逆删除：移动到废纸篓而非 rm。
- 权限不足时不强删、不提权，返回可供用户手动执行的命令。
"""

from __future__ import annotations

import os
import subprocess

from .fsutil import is_protected

# 路径经 argv 传入，脚本内不做字符串插值，因此文件名含引号也不会破坏脚本或注入 AppleScript。
_TRASH_SCRIPT = (
    "on run argv\n"
    "    set out to {}\n"
    "    repeat with p in argv\n"
    "        set end of out to (POSIX file (p as text))\n"
    "    end repeat\n"
    '    tell application "Finder" to delete out\n'
    "end run"
)


def _osascript_trash(paths: list[str]) -> tuple[bool, str]:
    """用 Finder 把一批路径移入废纸篓（支持「放回原处」）。

    路径作为 argv 传给 osascript，绝不插进脚本字符串——macOS 文件名允许包含 `"`，
    插值会破坏脚本甚至被当作 AppleScript 代码执行。
    """
    if not paths:
        return True, ""
    try:
        proc = subprocess.run(
            ["osascript", "-e", _TRASH_SCRIPT, *paths],
            capture_output=True, text=True, timeout=120,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return False, str(exc)
    if proc.returncode == 0:
        return True, ""
    return False, (proc.stderr or proc.stdout).strip()


def trash_path(path: str) -> dict:
    """把单个路径移入废纸篓，返回结果字典。"""
    result = {"ok": False, "error": "", "needs_sudo": False, "command": ""}

    if not path:
        result["error"] = "空路径"
        return result
    if is_protected(path):
        result["error"] = "受保护路径，已拒绝删除"
        return result
    if not os.path.exists(path) and not os.path.islink(path):
        # 已经不存在，视为成功
        result["ok"] = True
        return result

    ok, err = _osascript_trash([path])
    if ok:
        result["ok"] = True
        return result

    # 失败：多半是权限问题。坚持「默认可还原、不强删」——绝不替用户生成
    # `rm -rf` 这类不可逆命令，也不自动提权，改为引导用户自行在「访达」处理。
    result["error"] = err or "移动到废纸篓失败"
    parent = os.path.dirname(path)
    if not os.access(parent, os.W_OK):
        result["needs_sudo"] = True
    result["hint"] = (
        "MacBroom 不会替你执行不可逆删除。可在「访达」中定位该路径并手动移入废纸篓；"
        "若位于系统 / 管理员目录，请确认确有必要后自行处理。"
    )
    return result


def run_safe_command(command: str) -> dict:
    """执行扫描器生成的「安全命令」（如 xcrun simctl / brew cleanup）。

    这些命令由本工具内部生成，不接受用户任意输入，因此可直接执行。
    需要 sudo 的命令不在这里执行（扫描器会标记为 manual）。
    """
    result = {"ok": False, "error": "", "output": "", "command": command}
    try:
        proc = subprocess.run(
            ["/bin/zsh", "-lc", command],
            capture_output=True, text=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        result["error"] = "命令执行超时"
        return result
    result["output"] = (proc.stdout or "")[-2000:]
    if proc.returncode == 0:
        result["ok"] = True
    else:
        result["error"] = (proc.stderr or proc.stdout or "命令执行失败").strip()[-2000:]
    return result
