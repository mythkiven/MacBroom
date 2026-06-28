"""系统额外项：清单里没单列、但值得清理的杂项。

包含：诊断报告 / 崩溃日志、iOS 设备备份、Homebrew 残留、Docker 镜像、
Time Machine 本地快照、散落的 node_modules、邮件附件缓存、旧下载。
（废纸篓不在此列：逐项移入已在废纸篓的文件无意义，而「清空废纸篓」不可逆，不做一键项。）
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time

from macbroom.core.fsutil import HOME, actual_size, dir_size, path_mtime, safe_listdir
from macbroom.core.i18n import tr
from macbroom.core.model import (ACTION_MANUAL, ACTION_RUN, RISK_MODERATE, RISK_RISKY,
                                 RISK_SAFE, Category, ScanItem)

CATEGORY = Category(
    key="extras",
    title="其它可清理项",
    description="诊断报告、设备备份、Docker、Time Machine 快照、邮件附件、旧下载等。",
    icon="✨",
)

_MIN = 1024 * 1024


def _path_item(name, path, note, recommend, group, risk=RISK_MODERATE):
    if not os.path.exists(path) or os.path.islink(path):
        return None
    size = dir_size(path)
    if size < _MIN:
        return None
    return ScanItem(
        category=CATEGORY.key, name=name, group=group, path=path,
        size=size, mtime=path_mtime(path), note=note, recommend=recommend,
        risk=risk,
    )


def _scan_node_modules(max_depth: int = 4, lang: str = "zh") -> list[ScanItem]:
    """有限深度查找散落的 node_modules（不递归进 node_modules 内部）。"""
    items: list[ScanItem] = []
    roots = [HOME]
    base_depth = HOME.rstrip("/").count("/")
    for cur, dirs, _ in os.walk(HOME, topdown=True, onerror=lambda e: None):
        depth = cur.rstrip("/").count("/") - base_depth
        if depth >= max_depth:
            dirs[:] = []
            continue
        if "node_modules" in dirs:
            path = os.path.join(cur, "node_modules")
            if not os.path.islink(path):
                size = dir_size(path)
                if size >= 20 * 1024 * 1024:
                    rel = cur.replace(HOME, "~")
                    items.append(ScanItem(
                        category=CATEGORY.key,
                        name=tr(lang, "extras.node_modules.name",
                                project=os.path.basename(cur) or rel),
                        group=tr(lang, "group.node_modules"),
                        path=path,
                        size=size,
                        mtime=path_mtime(path),
                    note=tr(lang, "extras.node_modules.note", path=rel),
                    recommend=False,
                    risk=RISK_MODERATE,
                ))
        # 裁剪：不进入隐藏目录、不进入 node_modules、Library
        dirs[:] = [d for d in dirs
                   if d not in ("node_modules", "Library", ".Trash")
                   and not d.startswith(".")]
        if len(items) > 60:
            break
    items.sort(key=lambda x: x.size, reverse=True)
    return items[:40]


_OLD_DOWNLOAD_DAYS = 90
_OLD_DOWNLOAD_MIN = 10 * 1024 * 1024  # 10MB 以下的旧下载不单列，避免噪音


def _scan_mail_attachments(lang: str = "zh") -> list[ScanItem]:
    """邮件下载的附件缓存（Apple Mail / Outlook）。属个人数据，标记高风险。"""
    items: list[ScanItem] = []
    candidates = [
        os.path.join(HOME, "Library", "Containers", "com.apple.mail",
                     "Data", "Library", "Mail Downloads"),
        os.path.join(HOME, "Library", "Containers",
                     "com.microsoft.Outlook", "Data", "Library", "Caches"),
    ]
    for path in candidates:
        it = _path_item(tr(lang, "extras.mail_attachments.name"), path,
                        tr(lang, "extras.mail_attachments.note"), False,
                        group=tr(lang, "group.mail"), risk=RISK_RISKY)
        if it:
            items.append(it)
    return items


def _scan_old_downloads(lang: str = "zh", max_items: int = 40) -> list[ScanItem]:
    """~/Downloads 顶层中超过 90 天、≥10MB 的旧文件（个人数据，高风险）。"""
    items: list[ScanItem] = []
    downloads = os.path.join(HOME, "Downloads")
    cutoff = time.time() - _OLD_DOWNLOAD_DAYS * 86400
    for entry in safe_listdir(downloads):
        if entry.startswith("."):
            continue
        path = os.path.join(downloads, entry)
        if os.path.islink(path):
            continue
        try:
            st = os.lstat(path)
        except OSError:
            continue
        if st.st_mtime > cutoff:
            continue
        size = dir_size(path) if os.path.isdir(path) else actual_size(st)
        if size < _OLD_DOWNLOAD_MIN:
            continue
        age_days = int((time.time() - st.st_mtime) / 86400)
        items.append(ScanItem(
            category=CATEGORY.key,
            name=entry,
            group=tr(lang, "group.old_downloads"),
            path=path,
            size=size,
            mtime=st.st_mtime,
            note=tr(lang, "extras.old_download.note", days=age_days),
            recommend=False,
            risk=RISK_RISKY,
        ))
    items.sort(key=lambda x: x.size, reverse=True)
    return items[:max_items]


def scan(lang: str = "zh") -> list[ScanItem]:
    items: list[ScanItem] = []

    # 废纸篓本身的文件：逐项移动到（已在）废纸篓没有意义，而「清空废纸篓」是
    # 不可逆操作，不适合作为一键命令项（评审反馈），因此这里不再收录。

    # 诊断报告 / 崩溃日志（可安全删除，自动重建）
    for name, path in [
        ("extras.diagnostic_reports.name", os.path.join(HOME, "Library", "Logs", "DiagnosticReports")),
        ("extras.crash_reporter.name", os.path.join(HOME, "Library", "Application Support", "CrashReporter")),
    ]:
        it = _path_item(tr(lang, name), path, tr(lang, "extras.logs.note"), True,
                        group=tr(lang, "group.logs"), risk=RISK_SAFE)
        if it:
            items.append(it)

    # iOS / iPhone 设备备份（通常很大，但很重要，默认不勾）
    backup = os.path.join(HOME, "Library", "Application Support", "MobileSync", "Backup")
    for entry in safe_listdir(backup):
        path = os.path.join(backup, entry)
        if os.path.isdir(path) and not os.path.islink(path):
            sz = dir_size(path)
            if sz >= _MIN:
                items.append(ScanItem(
                    category=CATEGORY.key,
                    name=tr(lang, "extras.ios_backup.name", id=entry[:12]),
                    group=tr(lang, "group.device_backups"), path=path,
                    size=sz, mtime=path_mtime(path),
                    note=tr(lang, "extras.ios_backup.note"), recommend=False,
                    risk=RISK_RISKY,
                ))

    # Homebrew 残留清理（安全）
    if shutil.which("brew"):
        items.append(ScanItem(
            category=CATEGORY.key, name=tr(lang, "extras.brew_cleanup.name"),
            group=tr(lang, "group.homebrew"), action=ACTION_RUN,
            command="brew cleanup -s 2>&1 | tail -5",
            size=0, note=tr(lang, "extras.brew_cleanup.note"), recommend=True,
            risk=RISK_SAFE,
        ))

    # Docker 镜像/容器
    if shutil.which("docker"):
        items.append(ScanItem(
            category=CATEGORY.key, name=tr(lang, "extras.docker_prune.name"),
            group=tr(lang, "group.docker"), action=ACTION_RUN,
            command="docker system prune -af 2>&1 | tail -8",
            size=0, note=tr(lang, "extras.docker_prune.note"), recommend=False,
            risk=RISK_MODERATE,
        ))

    # Time Machine 本地快照
    if shutil.which("tmutil"):
        try:
            out = subprocess.run(["tmutil", "listlocalsnapshots", "/"],
                                 capture_output=True, text=True, timeout=30)
            snaps = [l for l in out.stdout.splitlines() if "com.apple.TimeMachine" in l]
        except Exception:
            snaps = []
        if snaps:
            items.append(ScanItem(
                category=CATEGORY.key,
                name=tr(lang, "extras.tm_snapshots.name", count=len(snaps)),
                group=tr(lang, "group.time_machine"), action=ACTION_MANUAL,
                command="sudo tmutil thinlocalsnapshots / 999999999999 4",
                size=0, needs_sudo=True,
                note=tr(lang, "extras.tm_snapshots.note"), recommend=False,
                risk=RISK_RISKY,
            ))

    # 散落的 node_modules
    items.extend(_scan_node_modules(lang=lang))

    # 邮件附件缓存 + 旧 Downloads（高风险，默认不勾、默认隐藏）
    items.extend(_scan_mail_attachments(lang))
    items.extend(_scan_old_downloads(lang))

    items.sort(key=lambda x: x.size, reverse=True)
    return items
