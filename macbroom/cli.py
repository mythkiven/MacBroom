"""MacBroom CLI —— 解析参数并启动本地服务。

用法：
    macbroom                      # 默认 127.0.0.1:37700，自动开浏览器
    macbroom --port 40000
    macbroom --no-open            # 不自动打开浏览器
    python -m macbroom            # 等价调用

仅依赖 Python 3 标准库。
"""

from __future__ import annotations

import argparse
import threading
import webbrowser

from macbroom.core.server import serve

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 37700  # 已在端口登记表登记


def main() -> None:
    parser = argparse.ArgumentParser(description="MacBroom - macOS 清理工具")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    if not args.no_open:
        url = f"http://{args.host}:{args.port}"
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    serve(args.host, args.port)


if __name__ == "__main__":
    main()
