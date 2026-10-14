#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mcp/barkeeper.py — HomeBarLedger 的 MCP server（stdio，零依赖，Python 3.8+）
哲学取自 barkeeper(900 token 极简) + HomeStock（库存是台账不是事实）：
  不替 agent 做匹配判断——list_inventory + list_recipes 给原料，
  "能调什么"由你的 agent 自己交叉比对（它的模糊匹配比我们任何规则都聪明）。
注册到 Claude Code / 任何 MCP 客户端:
  {"mcpServers": {"home-bar": {"command": "python3", "args": ["mcp/barkeeper.py"]}}}
数据文件: 同目录上级 data/bar_data.json（或 $BAR_DATA 环境变量覆盖）
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("BAR_DATA", os.path.join(ROOT, "data", "bar_data.json"))

TOOLS = {
    "list_inventory": "酒柜+辅料+基底全量台账（在架/待购状态含在内）",
    "list_recipes": "全部配方（name/spirits/need/ratio/style/level，不含 verdict 点评以省 token）",
    "get_recipe": "单条配方完整内容（含 verdict 专业点评）",
    "add_item": "入一瓶新的（name/type/stock 必填）",
    "set_stock": "改库存状态（在架/已喝完/待购）",
}


def load():
    return json.load(open(DB, encoding="utf-8"))


def call(name, args):
    d = load()
    if name == "list_inventory":
        rows = [{"name": i["name"], "cat": i.get("cat") or i.get("type"),
                 "stock": i.get("stock", "?"), "abv": i.get("abv")} for i in d["items"]]
        rows += [{"name": m["name"], "cat": "mixer", "stock": m.get("stock", "?")} for m in d.get("mixers", [])]
        return json.dumps(rows, ensure_ascii=False)
    if name == "list_recipes":
        return json.dumps([{k: r[k] for k in ("name", "spirits", "need", "ratio", "level")
                            if k in r} for r in d["recipes"]], ensure_ascii=False)
    if name == "get_recipe":
        hit = next((r for r in d["recipes"] if r["name"] == args["name"]), None)
        return json.dumps(hit or {"error": "not found"}, ensure_ascii=False)
    if name == "add_item":
        d["items"].append(args)
    elif name == "set_stock":
        for coll in ("items", "mixers"):
            for it in d.get(coll, []):
                if it["name"] == args["name"]:
                    it["stock"] = args["stock"]
    else:
        return json.dumps({"error": f"unknown tool {name}"})
    d["updated"] = __import__("datetime").date.today().isoformat()
    tmp = DB + ".tmp"
    json.dump(d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, DB)  # 原子写，agent 崩了也不留半成品
    return json.dumps({"ok": True, "db": DB})


def main():
    """newline-delimited JSON-RPC (MCP stdio 简化握手)"""
    for line in sys.stdin:
        try:
            req = json.loads(line)
        except Exception:
            continue
        m = req.get("method", "")
        rid = req.get("id")
        if m == "initialize":
            res = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                   "serverInfo": {"name": "home-bar-ledger", "version": "0.1.0"}}
        elif m == "tools/list":
            res = {"tools": [{"name": k, "description": v,
                              "inputSchema": {"type": "object"}} for k, v in TOOLS.items()]}
        elif m == "tools/call":
            a = req.get("params", {})
            res = {"content": [{"type": "text", "text": call(a.get("name"), a.get("arguments", {}))}]}
        elif m == "notifications/initialized" or not m.startswith("notifications"):
            res = {} if m.startswith("notifications") else {"error": "method not found"}
        else:
            continue
        out = {"jsonrpc": "2.0", "id": rid}
        out["error"] = res if "error" in res else None
        if "error" not in res:
            out["result"] = res
        out = {k: v for k, v in out.items() if v is not None}
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
