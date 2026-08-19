#!/usr/bin/env python3
"""
mcp_call.py —— 直连一个 streamable-http MCP 端点，列工具 / 调工具。

用途：mcp-builder 建完新 MCP 并 publish 后，用 mcp_server_url_get 拿到新 MCP 的
接入地址（mcpURL，形如 https://[pre-]mcp-gw.dingtalk.com/server/<code>?key=<key>），
需要连上去真实调用一次验证。但 Claude Code 等 agent 无法在会话中途动态添加 MCP，
所以用本脚本直接对端点发 JSON-RPC，等价于「装上这个 MCP 后调用它」。

只用标准库，无第三方依赖。URL 里的 ?key= 是用户身份凭证——只经命令行入参传递，
本脚本不写任何文件、不落盘。

用法：
    python3 mcp_call.py list "<mcpURL>"
    python3 mcp_call.py call "<mcpURL>" <tool_name> '<json_args>'

示例：
    python3 mcp_call.py list "https://pre-mcp-gw.dingtalk.com/server/xxx?key=yyy"
    python3 mcp_call.py call "https://pre-mcp-gw.dingtalk.com/server/xxx?key=yyy" \
        search_city '{"city_name":"北京"}'

退出码：0=成功，1=调用/解析失败，2=用法错误。
"""
import sys
import json
import urllib.request
import urllib.error


def rpc(url, method, params, req_id=1):
    """对 MCP 端点发一条 JSON-RPC 请求，返回解析后的 dict。"""
    body = json.dumps({
        "jsonrpc": "2.0", "id": req_id, "method": method, "params": params,
    }).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        # 有的网关只在 Accept 含 SSE 时才响应
        "Accept": "application/json, text/event-stream",
    })
    try:
        raw = urllib.request.urlopen(req, timeout=30).read().decode()
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode()[:800]}
    except Exception as e:  # noqa: BLE001
        return {"_error": str(e)}
    # streamable-http 可能回 SSE（event:/data: 前缀），剥出 data 行
    txt = raw.strip()
    if txt.startswith("event:") or "\ndata:" in txt or txt.startswith("data:"):
        for line in txt.splitlines():
            if line.startswith("data:"):
                txt = line[len("data:"):].strip()
                break
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return {"_unparsed": txt[:800]}


def do_list(url):
    d = rpc(url, "tools/list", {})
    tools = d.get("result", {}).get("tools")
    if tools is None:
        print(json.dumps(d, ensure_ascii=False, indent=1))
        return 1
    print(f"工具数: {len(tools)}")
    for t in tools:
        print(f"  - {t['name']}: {(t.get('description') or '')[:60]}")
    return 0


def do_call(url, name, args_json):
    try:
        args = json.loads(args_json) if args_json else {}
    except json.JSONDecodeError as e:
        print(f"入参不是合法 JSON: {e}", file=sys.stderr)
        return 2
    d = rpc(url, "tools/call", {"name": name, "arguments": args})
    result = d.get("result", {})
    # 优先打印 structuredContent（业务数据），退回原始
    payload = result.get("structuredContent", result if result else d)
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    # isError 或缺 result 视为失败
    if d.get("_error") or d.get("_http_error") or result.get("isError"):
        return 1
    return 0


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    action, url = argv[1], argv[2]
    if action == "list":
        return do_list(url)
    if action == "call":
        if len(argv) < 4:
            print("用法: mcp_call.py call <url> <tool_name> '<json_args>'", file=sys.stderr)
            return 2
        name = argv[3]
        args_json = argv[4] if len(argv) > 4 else "{}"
        return do_call(url, name, args_json)
    print(f"未知动作: {action}（应为 list / call）", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
