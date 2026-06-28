"""本地 HTTP 服务：提供 Web UI 与扫描/删除 API。

安全设计：
- 仅监听 127.0.0.1。
- 校验 Host 头，拒绝 DNS rebinding（恶意站点把域名解析到本机端口）。
- 删除接口要求自定义请求头携带 CSRF token：浏览器对带自定义头的跨域请求
  会触发 CORS 预检，而本服务不返回任何 CORS 头，预检失败 → 外部网页无法
  调用删除接口。
- 删除接口只接受「本次扫描产出过的 id」，且删除前复核路径，拒绝任意路径删除。
"""

from __future__ import annotations

import json
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from macbroom.core import audit
from macbroom.core.i18n import normalize_lang
from macbroom.core.model import ACTION_MANUAL, ACTION_RUN, ACTION_TRASH, ScanItem
from macbroom.core.trash import run_safe_command, trash_path

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")

# 本进程的 CSRF token；随机生成，注入页面，删除接口据此校验。
CSRF_TOKEN = secrets.token_urlsafe(24)
CSRF_HEADER = "X-MacBroom-Token"

# 本次会话扫描过的项：id -> ScanItem。删除接口据此校验。
# 同时记录 category -> set(id)，重扫时先剔除旧项，避免无限累积陈旧数据。
_LAST_SCAN: dict[str, ScanItem] = {}
_CAT_IDS: dict[str, set[str]] = {}
_LOCK = threading.Lock()

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "MacBroom"

    def log_message(self, fmt, *args):  # 静默默认访问日志
        pass

    # ---- 安全校验 ----
    def _host_ok(self) -> bool:
        # 绑定到非 loopback（如 0.0.0.0，用户显式开了局域网访问）时放行 Host 校验；
        # 默认仅监听 127.0.0.1，则强制 Host 必须是 loopback，防 DNS rebinding。
        bound = self.server.server_address[0]
        if bound not in ("127.0.0.1", "localhost", "::1"):
            return True
        host = (self.headers.get("Host") or "").split(":")[0].strip().lower()
        return host in ("127.0.0.1", "localhost", "")

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, rel):
        path = os.path.normpath(os.path.join(WEB_DIR, rel))
        # 防目录穿越：归一化后必须仍在 WEB_DIR 内。
        if not path.startswith(WEB_DIR + os.sep) and path != WEB_DIR:
            return self.send_error(403)
        if not os.path.isfile(path):
            return self.send_error(404)
        with open(path, "rb") as f:
            body = f.read()
        ext = os.path.splitext(path)[1]
        if ext == ".html":
            # 注入 CSRF token，供前端在删除请求里回带。
            body = body.replace(b"__CSRF_TOKEN__", CSRF_TOKEN.encode("utf-8"))
        self.send_response(200)
        self.send_header("Content-Type", _CONTENT_TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._host_ok():
            return self.send_error(403, "invalid host")
        parsed = urlparse(self.path)
        route = parsed.path
        qs = parse_qs(parsed.query)
        lang = self._request_lang(qs)

        if route == "/" or route == "/index.html":
            return self._send_file("index.html")
        if route in ("/style.css", "/app.js"):
            return self._send_file(route.lstrip("/"))

        if route == "/api/categories":
            from macbroom.scanners import categories
            return self._send_json([{
                "key": c.key, "title": c.title, "description": c.description,
                "icon": c.icon, "danger": c.danger,
            } for c in categories(lang)])

        if route == "/api/scan":
            key = (qs.get("key") or [""])[0]
            return self._handle_scan(key, lang)

        self.send_error(404)

    def do_POST(self):
        if not self._host_ok():
            return self.send_error(403, "invalid host")
        parsed = urlparse(self.path)
        if parsed.path != "/api/delete":
            return self.send_error(404)
        if self.headers.get(CSRF_HEADER) != CSRF_TOKEN:
            return self._send_json({"error": "missing or invalid CSRF token"}, 403)
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send_json({"error": "invalid json"}, 400)
        return self._handle_delete(payload.get("ids", []))

    def _request_lang(self, qs: dict) -> str:
        lang = (qs.get("lang") or [""])[0]
        return normalize_lang(lang or self.headers.get("Accept-Language", ""))

    def _handle_scan(self, key, lang):
        from macbroom.scanners import scan_category
        items = scan_category(key, lang)
        with _LOCK:
            # 重扫先清掉该分类上一轮的陈旧 id，避免 _LAST_SCAN 无限膨胀。
            for old_id in _CAT_IDS.get(key, set()):
                _LAST_SCAN.pop(old_id, None)
            _CAT_IDS[key] = {it.id for it in items}
            for it in items:
                _LAST_SCAN[it.id] = it
        total = sum(i.size for i in items)
        audit.record("scan", category=key, count=len(items), total_size=total)
        return self._send_json({
            "key": key,
            "total_size": total,
            "count": len(items),
            "items": [i.to_dict() for i in items],
        })

    def _handle_delete(self, ids):
        results = []
        for item_id in ids:
            with _LOCK:
                item = _LAST_SCAN.get(item_id)
            if item is None:
                results.append({"id": item_id, "ok": False,
                                "error": "未知或已过期的项，请重新扫描"})
                continue

            if item.action == ACTION_TRASH:
                r = trash_path(item.path or "")
                results.append({"id": item_id, "name": item.name, **r})
            elif item.action == ACTION_RUN:
                r = run_safe_command(item.command or "")
                results.append({"id": item_id, "name": item.name,
                                "ok": r["ok"], "error": r.get("error", ""),
                                "command": item.command})
            elif item.action == ACTION_MANUAL:
                results.append({"id": item_id, "name": item.name, "ok": False,
                                "needs_sudo": item.needs_sudo,
                                "command": item.command,
                                "error": "需手动执行（权限/风险）"})
            else:
                results.append({"id": item_id, "ok": False, "error": "未知动作"})

            last = results[-1]
            audit.record(
                "delete", id=item_id, name=item.name, action=item.action,
                path=item.path, size=item.size, ok=bool(last.get("ok")),
                error=last.get("error", ""),
            )
            if last.get("ok"):
                with _LOCK:
                    _LAST_SCAN.pop(item_id, None)
                    for s in _CAT_IDS.values():
                        s.discard(item_id)
        return self._send_json({"results": results})


def serve(host: str, port: int):
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"MacBroom 已启动 →  http://{host}:{port}")
    print(f"审计日志：{audit.log_path()}")
    print("按 Ctrl+C 停止")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        httpd.shutdown()
