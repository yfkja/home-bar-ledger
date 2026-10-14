#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""serve.py — HomeBarLedger 零依赖服务器（Python 3.8+ 标准库，无 pip）
用法:  python3 serve.py [--port 8788] [--dir data]
启动即做数据契约校验（借鉴 jev-ultrafast：DONE≠成功，数据不合法拒绝服务而不是页面白屏）。
"""
import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(ROOT, "static")
REQUIRED_LISTS = {"items": ["name", "type", "stock"],
                  "recipes": ["name", "spirits", "need", "ratio", "style", "level"],
                  "mixers": ["name", "need", "stock"]}


def data_path(args):
    return os.path.join(args.dir, "bar_data.json")


def load_data(args):
    p = data_path(args)
    if not os.path.exists(p):
        sys.exit(f"❌ 找不到 {p}\n   首次使用: cp data.example.json {p}")
    d = json.load(open(p, encoding="utf-8"))
    for key, req in REQUIRED_LISTS.items():
        for i, row in enumerate(d.get(key, [])):
            missing = [f for f in req if row.get(f) in (None, "")]
            if missing:
                hint = "  ← recipes 缺 level 会让配方页白屏，已改为启动报错" if key == "recipes" else ""
                sys.exit("❌ 数据契约失败: %s[%d]「%s」缺字段 %s%s"
                         % (key, i, row.get("name", "?"), missing, hint))
    return d


class H(BaseHTTPRequestHandler):
    args = None  # injected

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(self.path.split("?")[0]).replace("\\", "/")  # 先解码 %2e 等转义，再判路径
        if path == "/":
            path = "/static/index.html"
        if path.startswith("/static/"):
            # 防路径穿越：normpath 后必须仍在 ROOT 内（os.path.join 遇绝对路径会丢弃前缀）
            f = os.path.normpath(os.path.join(ROOT, path.lstrip("/")))
            if not f.startswith(ROOT + os.sep):
                return self._send(403, b"forbidden", "text/plain")
            if os.path.isfile(f):
                return self._send(200, open(f, "rb").read(),
                                  "text/html" if f.endswith(".html") else "application/json")
        if path == "/api/data":
            return self._send(200, json.dumps(load_data(self.args), ensure_ascii=False).encode(),
                              "application/json")
        self._send(404, b"not found", "text/plain")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8788)
    ap.add_argument("--dir", default=os.path.join(ROOT, "data"), help="bar_data.json 所在目录")
    ap.add_argument("--check", action="store_true", help="只跑数据契约校验后退出（agent 改完必跑）")
    ap.add_argument("--lan", action="store_true",
                    help="监听 0.0.0.0 允许局域网访问（默认只绑 127.0.0.1；本工具无鉴权，请只在可信局域网开启）")
    args = ap.parse_args()
    os.makedirs(args.dir, exist_ok=True)
    d = load_data(args)  # 启动即校验
    if args.check:
        print("✅ 数据契约通过: items=%d recipes=%d mixers=%d"
              % (len(d["items"]), len(d["recipes"]), len(d.get("mixers", []))))
        sys.exit(0)
    H.args = args
    host = "0.0.0.0" if args.lan else "127.0.0.1"
    print("✅ 数据契约通过: items=%d recipes=%d mixers=%d"
          % (len(d["items"]), len(d["recipes"]), len(d.get("mixers", []))))
    print("🍸 HomeBarLedger → http://127.0.0.1:%d/  (监听 %s)" % (args.port, host))
    ThreadingHTTPServer((host, args.port), H).serve_forever()


if __name__ == "__main__":
    main()
