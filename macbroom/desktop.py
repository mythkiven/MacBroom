"""MacBroom 原生桌面壳：把本地 Web UI 装进一个原生 macOS 窗口。

双击 .app 即用：
- 后台线程启动本地 HTTP 服务（复用 core.server 的 Handler），端口由系统动态分配；
- 主线程跑 Cocoa 事件循环，原生窗口用 WKWebView 加载 http://127.0.0.1:<port>/；
- 关闭窗口即退出并停掉服务。

仅在打包为 .app（或显式运行）时使用，依赖 PyObjC（pyobjc-framework-Cocoa / WebKit）。
CLI / pip 的零依赖使用方式不导入本模块，二者互不影响。
"""

from __future__ import annotations

import threading
from http.server import ThreadingHTTPServer

from Cocoa import (
    NSApplication,
    NSApplicationActivationPolicyRegular,
    NSBackingStoreBuffered,
    NSMakeRect,
    NSMenu,
    NSMenuItem,
    NSObject,
    NSSize,
    NSViewHeightSizable,
    NSViewWidthSizable,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSURL, NSURLRequest
from WebKit import WKWebView, WKWebViewConfiguration

from macbroom.core.server import Handler

HOST = "127.0.0.1"
_APP_NAME = "MacBroom"
_WINDOW_W, _WINDOW_H = 1100, 760
_MIN_W, _MIN_H = 880, 600

# Cocoa 对象需要的跨回调引用都挂在这里（避免被 GC，且回避 PyObjC ivar 细节）。
_STATE: dict = {}


def _start_server() -> tuple[ThreadingHTTPServer, int]:
    """后台线程起本地服务，端口交给系统动态分配，避免与 CLI 版固定端口冲突。"""
    httpd = ThreadingHTTPServer((HOST, 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        port = _STATE["port"]
        rect = NSMakeRect(0, 0, _WINDOW_W, _WINDOW_H)
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
            | NSWindowStyleMaskResizable
        )
        window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, NSBackingStoreBuffered, False
        )
        window.setTitle_(_APP_NAME)
        window.setContentMinSize_(NSSize(_MIN_W, _MIN_H))
        window.center()

        config = WKWebViewConfiguration.alloc().init()
        webview = WKWebView.alloc().initWithFrame_configuration_(rect, config)
        webview.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)

        url = NSURL.URLWithString_(f"http://{HOST}:{port}/")
        webview.loadRequest_(NSURLRequest.requestWithURL_(url))

        window.setContentView_(webview)
        window.makeKeyAndOrderFront_(None)

        _STATE["window"] = window
        _STATE["webview"] = webview

    def applicationShouldTerminateAfterLastWindowClosed_(self, app):
        return True

    def applicationWillTerminate_(self, notification):
        httpd = _STATE.get("httpd")
        if httpd is not None:
            httpd.shutdown()


def _build_menu(app) -> None:
    """最小可用菜单：关于 / 退出 + 标准编辑项（让 WKWebView 内可复制粘贴）。"""
    main_menu = NSMenu.alloc().init()

    app_item = NSMenuItem.alloc().init()
    main_menu.addItem_(app_item)
    app_menu = NSMenu.alloc().init()
    app_menu.addItem_(
        NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"About {_APP_NAME}", "orderFrontStandardAboutPanel:", ""
        )
    )
    app_menu.addItem_(NSMenuItem.separatorItem())
    app_menu.addItem_(
        NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"Quit {_APP_NAME}", "terminate:", "q"
        )
    )
    app_item.setSubmenu_(app_menu)

    edit_item = NSMenuItem.alloc().init()
    main_menu.addItem_(edit_item)
    edit_menu = NSMenu.alloc().initWithTitle_("Edit")
    for title, selector, key in (
        ("Cut", "cut:", "x"),
        ("Copy", "copy:", "c"),
        ("Paste", "paste:", "v"),
        ("Select All", "selectAll:", "a"),
    ):
        edit_menu.addItem_(
            NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, selector, key)
        )
    edit_item.setSubmenu_(edit_menu)

    app.setMainMenu_(main_menu)


def main() -> None:
    httpd, port = _start_server()
    _STATE["httpd"] = httpd
    _STATE["port"] = port

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    delegate = AppDelegate.alloc().init()
    _STATE["delegate"] = delegate  # 持有引用，防止被回收
    app.setDelegate_(delegate)
    _build_menu(app)
    app.activateIgnoringOtherApps_(True)
    app.run()


if __name__ == "__main__":
    main()
