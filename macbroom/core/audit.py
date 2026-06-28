"""操作审计日志：把每次扫描与删除写到本地文件，可事后追溯。

参考 MacSift / MacOS-Maid 的做法：清理工具必须留痕，用户不开调试器也能
知道「这个工具到底动了什么」。

设计要点（对应全局「自测数据安全」硬约束）：
- 日志目录可用环境变量 ``MACBROOM_LOG_DIR`` 覆盖，自测一律指向 /tmp，
  绝不污染用户真实日志目录。
- 单文件大小封顶，超过就轮转一次（.1），避免无限增长。
- 仅本地写文件，不发网络，不记录文件内容、仅记录路径与动作。
"""

from __future__ import annotations

import json
import os
import threading
import time

_DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Library", "Logs", "MacBroom")
_MAX_BYTES = 512 * 1024  # 512KB 封顶，超过轮转
_LOCK = threading.Lock()


def log_dir() -> str:
    return os.environ.get("MACBROOM_LOG_DIR", _DEFAULT_DIR)


def log_path() -> str:
    return os.path.join(log_dir(), "macbroom.log")


def _rotate_if_needed(path: str) -> None:
    try:
        if os.path.getsize(path) <= _MAX_BYTES:
            return
    except OSError:
        return
    backup = path + ".1"
    try:
        if os.path.exists(backup):
            os.remove(backup)
        os.rename(path, backup)
    except OSError:
        pass


def tail(limit: int = 200) -> list[dict]:
    """读取最近 ``limit`` 条审计记录（最新在前），供应用内日志查看器展示。

    只读当前日志文件（不含已轮转的 .1），坏行跳过，不抛异常。
    """
    path = log_path()
    try:
        with _LOCK, open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []
    out: list[dict] = []
    for raw in reversed(lines):
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
        if len(out) >= limit:
            break
    return out


def record(event: str, **fields) -> None:
    """追加一条结构化日志。失败时静默（日志不应影响主流程）。"""
    line = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "event": event}
    line.update(fields)
    try:
        with _LOCK:
            d = log_dir()
            os.makedirs(d, exist_ok=True)
            path = log_path()
            _rotate_if_needed(path)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError:
        pass
