"""安全删除：一律走 macOS「废纸篓」，可一键还原。

设计原则（对应全局「自测数据安全」硬约束）：
- 默认不做不可逆删除：移动到废纸篓而非 rm。
- 权限不足时不强删、不提权，返回可供用户手动执行的命令。
"""

from __future__ import annotations

import os
import subprocess

from .fsutil import is_protected


def _osascript_trash(paths: list[str]) -> tuple[bool, str]:
    """用 Finder 把一批路径移入废纸篓（支持「放回原处」）。"""
    if not paths:
        return True, ""
    # 构造 AppleScript 的 POSIX file 列表
    items = ", ".join(f'POSIX file "{p}"' for p in paths)
    script = f'tell application "Finder" to delete {{{items}}}'
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
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

    # 失败：多半是权限问题。给出手动命令，绝不自动提权。
    result["error"] = err or "移动到废纸篓失败"
    if "not allowed" in err.lower() or "permission" in err.lower() or os.geteuid() != 0:
        # 判定是否大概率需要 sudo
        parent = os.path.dirname(path)
        if not os.access(parent, os.W_OK):
            result["needs_sudo"] = True
            result["command"] = f"sudo rm -rf '{path}'"
    if not result["command"]:
        result["command"] = f"rm -rf '{path}'"
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
