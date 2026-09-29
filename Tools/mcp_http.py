"""Unreal MCP 서버를 HTTP(JSON-RPC)로 직접 부르는 작은 클라이언트.

Claude Code 세션의 MCP 연결은 8000번 에디터 하나에만 붙어 있다. 두 번째 에디터(병렬 작업용, 예: 8001번)는
이 스크립트로 부른다. 에디터 하나에는 한 번에 한 호출만 보낸다(동시 호출은 응답이 섞인다).

사용법
  python Tools/mcp_http.py --port 8001 list
  python Tools/mcp_http.py --port 8001 describe editor_toolset.toolsets.blueprint.BlueprintTools
  python Tools/mcp_http.py --port 8001 call <toolset_name> <tool_name> '<arguments JSON>'
  python Tools/mcp_http.py --port 8001 call <toolset_name> <tool_name> @args.json     (인자를 파일에서 읽기)
  --out result.txt 를 붙이면 결과를 파일로 쓰고 앞부분만 출력한다(큰 결과용).

종료 코드: 0 성공, 1 툴 에러(isError 또는 JSON-RPC error), 2 연결 실패.
"""

import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request

PROTOCOL_VERSION = "2025-03-26"


def session_file(port):
    return os.path.join(tempfile.gettempdir(), f"unreal_mcp_session_{port}.txt")


def post(port, payload, session_id=None, timeout=600):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"http://127.0.0.1:{port}/mcp", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    if session_id:
        req.add_header("Mcp-Session-Id", session_id)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        sid = resp.headers.get("Mcp-Session-Id")
        body = resp.read().decode("utf-8", errors="replace")
        ctype = resp.headers.get("Content-Type", "")
    if not body.strip():
        return None, sid
    if "text/event-stream" in ctype or body.lstrip().startswith(("event:", "data:")):
        # SSE: 마지막 data 줄의 JSON이 응답이다.
        msgs = [line[5:].strip() for line in body.splitlines() if line.startswith("data:")]
        for m in reversed(msgs):
            if m:
                return json.loads(m), sid
        return None, sid
    return json.loads(body), sid


def initialize(port):
    msg, sid = post(port, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                   "clientInfo": {"name": "soulcombat-mcp-http", "version": "1"}},
    })
    try:
        post(port, {"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
    except urllib.error.HTTPError:
        pass
    with open(session_file(port), "w") as f:
        f.write(sid or "")
    return sid


def get_session(port):
    path = session_file(port)
    if os.path.exists(path):
        with open(path) as f:
            sid = f.read().strip()
        return sid or None
    return initialize(port)


def call_tool(port, name, arguments):
    payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
               "params": {"name": name, "arguments": arguments}}
    sid = get_session(port)
    try:
        msg, _ = post(port, payload, sid)
    except urllib.error.HTTPError as e:
        if e.code in (400, 404):  # 세션 만료: 다시 초기화
            sid = initialize(port)
            msg, _ = post(port, payload, sid)
        else:
            raise
    return msg


def render(msg):
    if msg is None:
        return "", False
    if "error" in msg:
        return json.dumps(msg["error"], ensure_ascii=False, indent=1), True
    result = msg.get("result", {})
    parts = []
    for c in result.get("content", []):
        if c.get("type") == "text":
            parts.append(c.get("text", ""))
        else:
            parts.append(json.dumps(c, ensure_ascii=False)[:2000])
    return "\n".join(parts), bool(result.get("isError"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8001)
    ap.add_argument("--out", help="write the full result to this file and print only the first 4000 chars")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    d = sub.add_parser("describe")
    d.add_argument("toolset")
    c = sub.add_parser("call")
    c.add_argument("toolset")
    c.add_argument("tool")
    c.add_argument("args", nargs="?", default="{}")
    a = ap.parse_args()

    try:
        if a.cmd == "list":
            msg = call_tool(a.port, "list_toolsets", {})
        elif a.cmd == "describe":
            msg = call_tool(a.port, "describe_toolset", {"toolset_name": a.toolset})
        else:
            raw = a.args
            if raw.startswith("@"):
                with open(raw[1:], encoding="utf-8") as f:
                    raw = f.read()
            msg = call_tool(a.port, "call_tool", {"toolset_name": a.toolset, "tool_name": a.tool,
                                                   "arguments": json.loads(raw)})
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        print(f"CONNECTION ERROR: {e}", file=sys.stderr)
        return 2

    text, is_error = render(msg)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(text[:4000] + (f"\n... ({len(text)} chars, full result in {a.out})" if len(text) > 4000 else ""))
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(text)
    return 1 if is_error else 0


if __name__ == "__main__":
    sys.exit(main())
