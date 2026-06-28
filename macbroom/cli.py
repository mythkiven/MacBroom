"""MacBroom CLI —— 启动本地服务，或在终端直接扫描出报告。

用法：
    macbroom                      # 默认 127.0.0.1:37700，启动 Web UI 并打开浏览器
    macbroom --port 40000
    macbroom --no-open            # 不自动打开浏览器
    python -m macbroom            # 等价调用

    macbroom scan                 # 在终端扫描并打印汇总（不启动服务）
    macbroom scan --json          # 输出 JSON，便于脚本 / CI 消费
    macbroom scan --lang en
    macbroom scan --category caches,login_items

仅依赖 Python 3 标准库。
"""

from __future__ import annotations

import argparse
import json
import threading
import webbrowser

from macbroom.core import audit
from macbroom.core.fsutil import human_size
from macbroom.core.i18n import normalize_lang
from macbroom.core.server import serve
from macbroom.scanners import categories as list_categories, scan_category

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 37700  # 已在端口登记表登记


_LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def _run_serve(args: argparse.Namespace) -> None:
    if args.host not in _LOOPBACK_HOSTS:
        print(
            f"⚠️  警告：绑定到 {args.host} 会把扫描/删除接口暴露到本机以外，"
            "同一网络内的其他设备可访问页面、拿到 CSRF token 并发起删除。\n"
            "    仅在可信网络且确有需要时使用；默认请用 127.0.0.1。"
        )
    if not args.no_open:
        url = f"http://{args.host}:{args.port}"
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    serve(args.host, args.port)


def _run_scan(args: argparse.Namespace) -> None:
    lang = normalize_lang(args.lang)
    cats = list_categories(lang)
    title_by_key = {c.key: c.title for c in cats}
    icon_by_key = {c.key: c.icon for c in cats}

    if args.category:
        keys = [k.strip() for k in args.category.split(",") if k.strip()]
    else:
        keys = [c.key for c in cats]

    results: list[tuple[str, list]] = []
    for key in keys:
        results.append((key, scan_category(key, lang)))

    all_items = [it for _, items in results for it in items]
    audit.record("cli_scan", categories=keys, count=len(all_items))

    if args.json:
        print(json.dumps([it.to_dict() for it in all_items],
                         ensure_ascii=False, indent=2))
        return

    grand = 0
    for key, items in results:
        size = sum(it.size or 0 for it in items)
        grand += size
        icon = icon_by_key.get(key, "•")
        title = title_by_key.get(key, key)
        print(f"{icon}  {title}: {len(items)} items · {human_size(size)}")
    print("-" * 40)
    print(f"Total reclaimable: {human_size(grand)} across {len(all_items)} items")
    print("Tip: run `macbroom` for the visual UI, or add --json for machine output.")


def _resolve_version() -> str:
    """已安装时以包元数据（pyproject 版本）为准，源码运行回退到 __version__。"""
    try:
        from importlib.metadata import PackageNotFoundError, version
        try:
            return version("macbroom")
        except PackageNotFoundError:
            pass
    except Exception:
        pass
    from macbroom import __version__
    return __version__


def main() -> None:
    parser = argparse.ArgumentParser(description="MacBroom - open-source macOS cleaner")
    parser.add_argument("--version", action="version",
                        version=f"macbroom {_resolve_version()}")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")

    sub = parser.add_subparsers(dest="cmd")
    p_scan = sub.add_parser("scan", help="在终端扫描并输出报告，不启动服务")
    p_scan.add_argument("--json", action="store_true", help="以 JSON 输出，便于脚本消费")
    p_scan.add_argument("--lang", default="zh", help="zh 或 en")
    p_scan.add_argument("--category", default="",
                        help="只扫描指定分类，逗号分隔，如 caches,login_items")

    p_doctor = sub.add_parser("doctor", help="环境预检：Python/macOS/完全磁盘访问/端口等")
    p_doctor.add_argument("--json", action="store_true", help="JSON 输出")
    p_doctor.add_argument("--lang", default="zh", help="zh 或 en")
    p_doctor.add_argument("--port", type=int, default=DEFAULT_PORT,
                          help="待检测的 Web UI 端口（默认 37700）")

    args = parser.parse_args()
    if args.cmd == "scan":
        _run_scan(args)
    elif args.cmd == "doctor":
        from macbroom.doctor import format_report, run_checks
        checks = run_checks(getattr(args, "port", DEFAULT_PORT))
        if args.json:
            print(json.dumps(checks, ensure_ascii=False, indent=2))
        else:
            print(format_report(checks, normalize_lang(args.lang)))
        if not all(c["ok"] for c in checks):
            raise SystemExit(1)
    else:
        _run_serve(args)


if __name__ == "__main__":
    main()
