"""macbroom doctor — 启动前环境预检与权限引导。"""

from __future__ import annotations

import os
import platform
import socket
import sys
from typing import Any

from macbroom.core import audit
from macbroom.core.fsutil import HOME

DEFAULT_PORT = 37700

# 无「完全磁盘访问」时通常读不到的敏感路径（用于探测）。
_FDA_PROBE_PATHS = [
    os.path.join(HOME, "Library", "Safari", "Bookmarks.plist"),
    os.path.join(HOME, "Library", "Mail"),
    os.path.join(HOME, "Library", "Containers"),
]


def _check_python() -> dict[str, Any]:
    v = sys.version_info
    ok = v >= (3, 9)
    return {
        "id": "python",
        "ok": ok,
        "detail": f"{v.major}.{v.minor}.{v.micro}",
        "hint_key": "doctor.hint.python" if not ok else "",
    }


def _check_macos() -> dict[str, Any]:
    ok = platform.system() == "Darwin"
    rel = platform.mac_ver()[0] or "unknown"
    return {
        "id": "macos",
        "ok": ok,
        "detail": rel,
        "hint_key": "doctor.hint.macos" if not ok else "",
    }


def _check_full_disk_access() -> dict[str, Any]:
    readable = 0
    denied = 0
    for p in _FDA_PROBE_PATHS:
        try:
            if os.path.isdir(p):
                os.listdir(p)
            elif os.path.isfile(p):
                with open(p, "rb") as f:
                    f.read(1)
            else:
                continue
            readable += 1
        except PermissionError:
            denied += 1
        except OSError:
            pass
    # 全部拒绝 → 很可能没开完全磁盘访问；至少一个可读 → 基本够用
    ok = readable > 0 and denied == 0
    partial = readable > 0 and denied > 0
    detail = f"{readable} readable, {denied} denied"
    hint = ""
    if not ok:
        hint = "doctor.hint.fda_partial" if partial else "doctor.hint.fda"
    return {"id": "full_disk_access", "ok": ok, "detail": detail, "hint_key": hint}


def _check_log_dir() -> dict[str, Any]:
    try:
        p = audit.log_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8"):
            pass
        return {"id": "log_dir", "ok": True, "detail": p, "hint_key": ""}
    except OSError as exc:
        return {
            "id": "log_dir",
            "ok": False,
            "detail": str(exc),
            "hint_key": "doctor.hint.log_dir",
        }


def _check_port(port: int) -> dict[str, Any]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", port))
        return {"id": "port", "ok": True, "detail": str(port), "hint_key": ""}
    except OSError:
        return {
            "id": "port",
            "ok": False,
            "detail": str(port),
            "hint_key": "doctor.hint.port",
        }


def run_checks(port: int = DEFAULT_PORT) -> list[dict[str, Any]]:
    return [
        _check_python(),
        _check_macos(),
        _check_full_disk_access(),
        _check_log_dir(),
        _check_port(port),
    ]


def format_report(checks: list[dict[str, Any]], lang: str = "zh") -> str:
    from macbroom.core.i18n import tr

    lines = [tr(lang, "doctor.title"), ""]
    for c in checks:
        mark = "✓" if c["ok"] else "✗"
        title = tr(lang, f"doctor.check.{c['id']}")
        lines.append(f"  {mark} {title}: {c['detail']}")
        if c.get("hint_key"):
            lines.append(f"      → {tr(lang, c['hint_key'])}")
    lines.append("")
    all_ok = all(c["ok"] for c in checks)
    lines.append(tr(lang, "doctor.summary_ok" if all_ok else "doctor.summary_issues"))
    return "\n".join(lines)
