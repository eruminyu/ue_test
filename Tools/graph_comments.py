"""블루프린트 그래프 주석 박스를 클립보드 붙여넣기로 만드는 도우미.

Unreal MCP에는 주석 박스(EdGraphNode_Comment)의 텍스트, 위치, 크기를 정하는 툴이 없다.
대신 블루프린트 에디터가 클립보드의 T3D 텍스트를 붙여넣을 수 있으므로, 이 스크립트가 T3D를 만들어 클립보드에 넣는다.
붙여넣기는 "붙여넣은 노드들의 평균 위치"를 붙여넣기 지점 L로 옮기므로, 균형추(reroute knot)를 하나 섞어
평균이 정확히 L이 되게 하면 모든 주석이 지정한 절대 좌표에 놓인다 (docs/mcp/probe-bp-core.md 레시피 A).
전체 절차는 docs/comment-pass-recipe.md.

보통은 한 명령으로 (Git Bash면 먼저 export MSYS_NO_PATHCONV=1, /Game 경로가 C:/Program Files/Git/Game으로 바뀌는 것 방지)
  python Tools/graph_comments.py preview spec.json --layout x.layout.json      # 박스 좌표·검사만 (에디터 안 건드림)
  python Tools/graph_comments.py ui-run spec.json /Game/P/BP_X.BP_X:Graph --window w116 --layout x.layout.json --shot out.png
     -> 그래프 탭 열기(없으면 My Blueprint 더블클릭) → 워터마크 찾기 → 보정 → 붙여넣기 → 붙여넣은 것 Ctrl+C로 검증
        → 균형추 삭제 → 선택 해제(더미 knot 붙여넣고 삭제) → Home → 스크린샷. 검사 문제가 있으면 멈춘다(--force로 무시).
  python Tools/graph_comments.py ui-shot /Game/P/BP_X.BP_X:Graph out.png --window w116     # 스크린샷만 다시
  python Tools/graph_comments.py ui-close BP_X --window w116                               # 저장 뒤 에셋 탭 닫기
  python Tools/graph_comments.py ui-find w116                                              # 탭·My Blueprint 항목·워터마크 ref
수동 단계용
  calib / paste spec.json --L x,y / verify(클립보드의 주석 나열) / shot out.png
주의: 그래프 패널 포커스는 워터마크 '오른쪽 클릭 + Escape'로 준다. 왼쪽 클릭은 워터마크 밑의 노드 위젯(체크박스 등)을 눌러
      핀 기본값을 바꿀 수 있다(CanMove의 Return bool이 실제로 뒤집혔다).

spec.json 형식 (리스트, 순서대로 붙여넣는다. 바깥 박스를 먼저 쓰면 뒤에 오는 안쪽 박스가 위에 그려진다)
  [
    {"text": "■ 입력 처리\\n설명", "x": 0, "y": 0, "w": 900, "h": 400, "color": "event", "font": 18},
    {"text": "■ 피해 적용\\n설명", "names": ["K2Node_CallFunction_3", ...], "color": "damage"},
    {"text": "■ 함수 헤더", "all": true, "color": "setup"},            # 레이아웃의 모든 노드 + 다른 박스를 감싼다
    {"text": "...", "nodes": [[x, y], [x, y, w, h]], "pad": 48}         # 옛 형식: 좌표 직접
  ]
  "names"와 "all"은 --layout(graph_layout.py layout 결과)의 rects(노드 추정 크기)를 쓴다.
  "wrap": [0, 2] 을 주면 그 인덱스의 박스들도 감싼다(중첩). "all"은 자동으로 모든 박스를 감싼다.
  color: 이름(event 파랑, logic 주황, damage 빨강, ui 초록, setup 회색) 또는 [r, g, b].
  names에는 graph_layout.py rows 출력의 "제목#번호"(예: "Branch#3")를 써도 된다. exec 노드만 적으면 그 노드와 함께 배치된
  순수 노드(layout owner)가 자동으로 들어간다("pure": false로 끔). "maxw": 0 이면 제목 때문에 박스를 넓히지 않는다(줄바꿈).
  "bubble": 축소 시 제목 말풍선. 기본은 다른 박스에 감싸이지 않은 최상위 박스만 True.
"""

import argparse
import base64
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_NODE_W = 320
DEFAULT_NODE_H = 180
DEFAULT_PAD = 40
GRID = 16
TAG = int(time.time()) % 100000   # 붙여넣는 주석 이름에 붙여 같은 그래프에 다시 붙여도 이름이 겹치지 않게 한다
COLORS = {
    "event": (0.1, 0.3, 0.7),
    "logic": (0.8, 0.45, 0.1),
    "damage": (0.7, 0.15, 0.15),
    "ui": (0.15, 0.55, 0.25),
    "setup": (0.35, 0.35, 0.35),
}


def snap(v):
    return int(round(v / GRID)) * GRID


MAX_TITLE_W = 1600   # 제목이 한 줄에 들어가도록 박스를 넓히는 한도


def text_px(line, font):
    """제목 줄의 대략적인 픽셀 폭 (한글·기호 = font, 영문·숫자 = 0.75 font. 0.58은 실측보다 20% 좁아 자동 줄바꿈을 놓쳤다)."""
    return sum(font * (1.0 if ord(ch) > 0x2000 else 0.75) for ch in line)


def title_height(text, font, width=None):
    """제목 줄 높이. 박스 폭이 주어지면 자동 줄바꿈된 줄 수까지 센다."""
    lines = 0
    for line in text.split("\n"):
        lines += max(1, math.ceil(text_px(line, font) / max(1, width - 40))) if width else 1
    return int(lines * (font * 1.45) + 18)


def title_min_width(text, font):
    return min(MAX_TITLE_W, max(text_px(line, font) for line in text.split("\n")) + 48)


def union(rects):
    x0 = min(r[0] for r in rects)
    y0 = min(r[1] for r in rects)
    x1 = max(r[0] + r[2] for r in rects)
    y1 = max(r[1] + r[3] for r in rects)
    return x0, y0, x1, y1


def resolve_short(spec, layout):
    """names에 "제목#번호"(graph_layout.py rows 출력 형식)를 쓰면 실제 노드 이름으로 바꾼다."""
    titles = (layout or {}).get("titles", {})
    for i, c in enumerate(spec):
        out = []
        for nm in c.get("names", []):
            if "#" in nm:
                t, num = nm.rsplit("#", 1)
                hits = [n for n, tt in titles.items() if tt == t and n.rsplit("_", 1)[-1] == num]
                if len(hits) != 1:
                    raise SystemExit(f"spec[{i}]: cannot resolve {nm}: {hits}")
                out.append(hits[0])
            else:
                out.append(nm)
        c["names"] = out


def expand_names(spec, layout):
    """names에 적은 exec 노드와 함께 배치된 순수 노드(layout owner)를 자동으로 넣는다 ("pure": false면 끔)."""
    owner = (layout or {}).get("owner", {})
    for c in spec:
        names = list(c.get("names", []))
        if c.get("pure", True):
            for p, o in owner.items():
                if o in names and p not in names:
                    names.append(p)
        c["_names"] = names


def resolve_boxes(spec, layout):
    rects = (layout or {}).get("rects", {})
    resolve_short(spec, layout)
    expand_names(spec, layout)
    boxes = [None] * len(spec)
    # 안쪽(직접 지정)부터, wrap/all은 나중에
    order = sorted(range(len(spec)), key=lambda i: (1 if (spec[i].get("all") or spec[i].get("wrap")) else 0,
                                                    len(spec[i].get("wrap", []))))
    for i in order:
        c = spec[i]
        font = int(c.get("font", 18))
        pad = c.get("pad", DEFAULT_PAD)
        th = title_height(c["text"], font)
        inner = []
        if "x" in c:
            boxes[i] = (snap(c["x"]), snap(c["y"]), snap(c["w"]), snap(c["h"]))
            continue
        if "nodes" in c:
            for n in c["nodes"]:
                inner.append((n[0], n[1], n[2] if len(n) > 2 else DEFAULT_NODE_W, n[3] if len(n) > 3 else DEFAULT_NODE_H))
        for nm in c["_names"]:
            if nm not in rects:
                raise SystemExit(f"unknown node name in spec[{i}]: {nm}")
            inner.append(tuple(rects[nm]))
        if c.get("all"):
            inner += [tuple(r) for r in rects.values()]
            wrap = [j for j in range(len(spec)) if j != i and not spec[j].get("all")]
        else:
            wrap = c.get("wrap", [])
        for j in wrap:
            if boxes[j] is None:
                raise SystemExit(f"spec[{i}] wraps spec[{j}] which is not resolved yet")
            inner.append(boxes[j])
        x0, y0, x1, y1 = union(inner)
        x0 -= pad
        x1 += pad
        x1 = max(x1, x0 + min(title_min_width(c["text"], font), c.get("maxw", MAX_TITLE_W)))   # 제목이 되도록 한 줄에 들어가게 넓힌다
        th = title_height(c["text"], font, x1 - x0)
        c["_th"] = th
        y0 -= pad + th
        y1 += pad
        bx, by = math.floor(x0 / GRID) * GRID, math.floor(y0 / GRID) * GRID
        boxes[i] = (bx, by, math.ceil((x1 - bx) / GRID) * GRID, math.ceil((y1 - by) / GRID) * GRID)
    for i, c in enumerate(spec):
        if "bubble" not in c:
            nested = any((j != i and (spec[j].get("all") or i in spec[j].get("wrap", []))) for j in range(len(spec)))
            c["bubble"] = not nested
    return boxes


def check(spec, boxes, layout):
    """노드가 자기 박스 밖으로 나가거나, 중첩이 아닌 박스끼리 겹치거나, 박스가 남의 노드를 덮는지 검사."""
    rects = (layout or {}).get("rects", {})
    problems = []

    def inside(r, b):
        return r[0] >= b[0] and r[1] >= b[1] and r[0] + r[2] <= b[0] + b[2] and r[1] + r[3] <= b[1] + b[3]

    def inter(a, b):
        return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]

    for i, c in enumerate(spec):
        for nm in c["_names"]:
            if not inside(rects[nm], boxes[i]):
                problems.append(f"node {nm} not inside box {i}")
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            if inter(a, b) and not inside(a, b) and not inside(b, a):
                problems.append(f"boxes {i} and {j} overlap")
    # 바깥 박스의 제목 줄이 안쪽 박스를 덮는지
    for i, c in enumerate(spec):
        inner = [j for j in range(len(spec)) if j != i and not spec[j].get("all")] if c.get("all") else c.get("wrap", [])
        th = c.get("_th", 0)
        for j in inner:
            if boxes[j][1] < boxes[i][1] + th + 8:
                problems.append(f"title bar of box {i} covers box {j}")
    # 제목 줄이 다른 블록의 노드를 덮는지 (박스 i의 노드가 아닌데 박스 i 제목 영역에 걸린 노드)
    for i, c in enumerate(spec):
        if c.get("all"):
            continue
        own = set(c["_names"])
        for j in c.get("wrap", []):
            own |= set(spec[j]["_names"])
        th = c.get("_th", title_height(c["text"], int(c.get("font", 18))))
        tb = (boxes[i][0], boxes[i][1], boxes[i][2], th + 8)
        for nm, r in rects.items():
            if nm not in own and inter(r, boxes[i]):
                problems.append(f"box {i} covers foreign node {nm}" + (" (title bar)" if inter(r, tb) else ""))
    return problems


def escape(text):
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def color_of(c):
    col = c.get("color") or [1.0, 1.0, 1.0]
    if isinstance(col, str):
        col = COLORS[col]
    return col[:3]


def comment_block(i, c, box):
    """bubble: 축소(zoom out)했을 때 제목을 크게 보여 주는 말풍선. 바깥(최상위) 박스만 켠다(안쪽까지 켜면 서로 겹친다)."""
    x, y, w, h = box
    r, g, b = color_of(c)
    font = int(c.get("font", 18))
    bub = "True" if c.get("bubble", True) else "False"
    return (
        f'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="EdGraphNode_Comment_SC{TAG}_{i}"\n'
        f"   CommentColor=(R={r:.6f},G={g:.6f},B={b:.6f},A=1.000000)\n"
        f"   FontSize={font}\n"
        f"   bCommentBubbleVisible_InDetailsPanel={bub}\n"
        f"   bCommentBubbleVisible={bub}\n"
        f"   NodePosX={x}\n"
        f"   NodePosY={y}\n"
        f"   NodeWidth={w}\n"
        f"   NodeHeight={h}\n"
        f'   NodeComment="{escape(c["text"])}"\n'
        f"End Object\n"
    )


def knot_block(name, x, y):
    return (
        f'Begin Object Class=/Script/BlueprintGraph.K2Node_Knot Name="{name}"\n'
        f"   NodePosX={x}\n"
        f"   NodePosY={y}\n"
        f"End Object\n"
    )


# Windows 클립보드는 모든 에디터가 공유한다. 에디터 두 대에서 주석 작업을 동시에 하면 한쪽의 T3D가
# 다른 쪽에 붙여넣어질 수 있으므로, 클립보드를 쓰는 명령은 프로세스 사이 잠금(원자적 mkdir)을 잡고 실행한다.
# ui-* 명령은 붙여넣기·확인까지 한 프로세스 안에서 끝나므로 잠금이 전 과정을 감싼다.
# calib/paste/verify처럼 사람이 중간에 Ctrl+V를 누르는 수동 흐름은 잠금이 사이를 감싸지 못하니 병렬 작업 중에는 쓰지 않는다.
CLIPBOARD_COMMANDS = {"calib", "paste", "verify", "ui-calib", "ui-shot", "ui-run", "ui-paste"}
CLIPBOARD_LOCK = os.path.join(tempfile.gettempdir(), "soulcombat_clipboard.lock")
CLIPBOARD_LOCK_STALE_SEC = 300


def acquire_clipboard_lock(timeout_sec=1200):
    import atexit
    import shutil
    start = time.time()
    while True:
        try:
            os.mkdir(CLIPBOARD_LOCK)
            atexit.register(lambda: shutil.rmtree(CLIPBOARD_LOCK, ignore_errors=True))
            return
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(CLIPBOARD_LOCK) > CLIPBOARD_LOCK_STALE_SEC:
                    shutil.rmtree(CLIPBOARD_LOCK, ignore_errors=True)  # 죽은 프로세스가 남긴 잠금
                    continue
            except OSError:
                continue
            if time.time() - start > timeout_sec:
                raise SystemExit(f"clipboard lock busy for {timeout_sec}s: {CLIPBOARD_LOCK}")
            time.sleep(0.5)


def set_clipboard(text):
    fd, path = tempfile.mkstemp(suffix=".t3d")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    cmd = f"Set-Clipboard -Value (Get-Content -Raw -Encoding UTF8 '{path}')"
    subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=True)
    return path


def get_clipboard():
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-Clipboard -Raw"],
                       capture_output=True, text=True, encoding="utf-8")
    return r.stdout


def parse_t3d(text):
    """클립보드 T3D에서 최상위 오브젝트(Begin Object ~ End Object, 들여쓰기 0)를 읽는다."""
    objs = []
    cur = None
    for line in text.splitlines():
        if line.startswith("Begin Object"):
            m = re.search(r'Class=(\S+) Name="([^"]+)"', line)
            cur = {"class": m.group(1).split(".")[-1] if m else "?", "name": m.group(2) if m else "?"}
        elif line.startswith("End Object"):
            if cur:
                objs.append(cur)
            cur = None
        elif cur is not None:
            m = re.match(r"\s{3}(NodePosX|NodePosY|NodeWidth|NodeHeight)=(-?\d+)", line)
            if m:
                cur[m.group(1)] = int(m.group(2))
            m = re.match(r'\s{3}NodeComment="(.*)"$', line)
            if m:
                cur["NodeComment"] = m.group(1).replace("\\n", "\n").replace('\\"', '"')
    return objs


# ---------------------------------------------------------------- UI automation over Tools/mcp_http.py

SI = "SlateInspectorToolset.SlateInspectorToolset"
PT = "editor_toolset.toolsets.programmatic.ProgrammaticToolset"

UI_SCRIPT = r"""
import json
SI = "SlateInspectorToolset.SlateInspectorToolset."
BT = "editor_toolset.toolsets.blueprint.BlueprintTools."
def ui(t, a):
    return execute_tool(SI + t, json.dumps(a))["returnValue"]
def bt(t, a):
    return execute_tool(BT + t, json.dumps(a))["returnValue"]
def run():
    G = "__G__"
    knot = {"refPath": G + ".__KNOT__"}
    # 그래프 패널에 키보드 포커스 주기: 워터마크를 '오른쪽' 클릭(컨텍스트 메뉴) → Escape.
    # 왼쪽 클릭은 워터마크 밑에 노드가 있으면 그 노드의 체크박스·입력칸을 눌러 핀 값을 바꿀 수 있다(실제로 bool 기본값이 뒤집혔다).
    ui("Click", {"ref": "__ANCHOR__", "button": "right"})
    ui("PressKey", {"key": "Escape"})
    ui("PressKey", {"key": "Ctrl+V"})
    if __COPY__:
        ui("PressKey", {"key": "Ctrl+C"})   # 붙여넣은 것(주석 + 균형추)만 선택된 상태 → 그대로 복사해 검증
    info = bt("get_node_infos", {"nodes": [knot]})
    pos = info[0]["position"]
    bt("delete_node", {"node": knot})
    return {"knot": [pos["x"], pos["y"]]}
"""


def mcp(toolset, tool, args, port=8000):
    fd, argp = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(args, f)
    fd, outp = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    cmd = [sys.executable, os.path.join(HERE, "mcp_http.py"), "--port", str(port), "--out", outp,
           "call", toolset, tool, "@" + argp]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    with open(outp, encoding="utf-8") as f:
        text = f.read()
    os.remove(argp)
    os.remove(outp)
    if r.returncode != 0:
        raise SystemExit("MCP error: " + (text or r.stdout + r.stderr)[-3000:])
    return json.loads(text)["returnValue"]


def ui_paste_and_read(graph_ref, anchor, knot, copy, port):
    script = (UI_SCRIPT.replace("__G__", graph_ref).replace("__ANCHOR__", anchor)
              .replace("__KNOT__", knot).replace("__COPY__", "True" if copy else "False"))
    return json.loads(mcp(PT, "execute_tool_script", {"script": script}, port))


def ui_find(window_ref, port):
    """BP 창 스냅샷에서 그래프 탭, My Blueprint 항목, 워터마크(빈 곳 앵커) ref를 찾는다."""
    tree = mcp(SI, "Snapshot", {"ref": window_ref, "maxDepth": 40}, port)
    found = {"tabs": {}, "items": {}, "watermark": [], "zoom": None}
    for line in tree.splitlines():
        m = re.match(r'\s*(tab|listitem|text) "([^"]*)" \[.*?\] \[ref=(\w+)\]', line)
        if not m:
            continue
        kind, label, ref = m.groups()
        if kind == "tab":
            found["tabs"][label] = ref
        elif kind == "listitem":
            found["items"][label] = ref
        elif label == "BLUEPRINT":
            found["watermark"].append(ref)
        elif label.startswith("Zoom"):
            found["zoom"] = label
    return found



def put_paste_on_clipboard(spec, boxes, lx, ly):
    blocks = [comment_block(i, c, boxes[i]) for i, c in enumerate(spec)]
    n = len(boxes)
    kx = snap((n + 1) * lx - sum(b[0] for b in boxes))
    ky = snap((n + 1) * ly - sum(b[1] for b in boxes))
    blocks.append(knot_block("K2Node_Knot_Counterweight", kx, ky))
    return kx, ky, set_clipboard("".join(blocks))


def ui_paste_verify(graph_ref, anchor, boxes, kx, ky, port):
    res = ui_paste_and_read(graph_ref, anchor, "K2Node_Knot_Counterweight", True, port)
    objs = parse_t3d(get_clipboard())
    got = {o["name"]: o for o in objs if o["class"] == "EdGraphNode_Comment"}
    mism = []
    for i, b in enumerate(boxes):
        o = got.get(f"EdGraphNode_Comment_SC{TAG}_{i}")
        g = o and [o.get("NodePosX"), o.get("NodePosY"), o.get("NodeWidth"), o.get("NodeHeight")]
        if g != list(b):
            mism.append({"i": i, "want": b, "got": g})
    return {"knot": res["knot"], "expected_knot": [kx, ky], "knot_ok": abs(res["knot"][0] - kx) <= 16 and abs(res["knot"][1] - ky) <= 16,
            "comments_pasted": len(got), "objects_pasted": len(objs), "mismatch": mism}


def ui_run(window, graph_ref, spec, boxes, shot, port, fit_all=False):
    """그래프 탭 열기 → 워터마크 찾기 → 보정 → 붙여넣기·확인 → Home → 스크린샷을 한 번에."""
    graph = graph_ref.split(":")[-1]
    anchor = open_graph(window, graph, port)
    set_clipboard(knot_block("K2Node_Knot_Cal", 0, 0))
    lx, ly = ui_paste_and_read(graph_ref, anchor, "K2Node_Knot_Cal", False, port)["knot"]
    kx, ky, _ = put_paste_on_clipboard(spec, boxes, lx, ly)
    out = {"graph": graph, "anchor": anchor, "L": [lx, ly]}
    out.update(ui_paste_verify(graph_ref, anchor, boxes, kx, ky, port))
    if shot:
        out["shot"] = fit_and_shot(graph_ref, anchor, shot, port, fit_all)
    return out


def open_graph(window, graph, port):
    """그래프 탭을 앞으로(없으면 My Blueprint에서 더블클릭해 연다) 하고 그 패널의 워터마크 ref를 돌려준다."""
    f = ui_find(window, port)
    if graph in f["tabs"]:
        ok = mcp(SI, "Click", {"ref": f["tabs"][graph]}, port)
    elif graph in f["items"]:
        ok = mcp(SI, "Click", {"ref": f["items"][graph], "doubleClick": True}, port)
    else:
        raise SystemExit(f"graph {graph} not found in tabs/My Blueprint: {list(f['tabs'])} {list(f['items'])}")
    if not ok:
        raise SystemExit("click on graph tab/item returned false (stale ref?)")
    f = ui_find(window, port)
    if len(f["watermark"]) != 1:
        raise SystemExit(f"expected one BLUEPRINT watermark, got {f['watermark']}")
    return f["watermark"][0]


def close_asset_tab(window, asset_name, port):
    """BP 에디터 창의 에셋 탭(제목 = 에셋 이름) 닫기 버튼을 누른다. 저장한 뒤에 부른다."""
    tree = mcp(SI, "Snapshot", {"ref": window, "maxDepth": 40}, port)
    lines = tree.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r'(\s*)tab "([^"]*)"', line)
        if m and m.group(2) == asset_name:
            ind = len(m.group(1))
            for nxt in lines[i + 1:]:
                if len(nxt) - len(nxt.lstrip()) <= ind:
                    break
                b = re.match(r'\s*button \[.*?\] \[ref=(\w+)\]', nxt)
                if b:
                    return mcp(SI, "Click", {"ref": b.group(1)}, port)
    raise SystemExit(f"asset tab {asset_name} with a close button not found (is it the active tab?)")


def fit_and_shot(graph_ref, anchor, shot, port, fit_all=False):
    """선택 해제 → Home(전체 맞춤, 애니메이션이 있어 기다림) → 스크린샷.
    Escape로는 선택이 안 풀리고, 빈 곳 왼쪽 클릭은 노드 위젯을 누를 위험이 있다.
    그래서 더미 knot을 붙여넣어(선택이 그것으로 바뀜) 바로 delete_node → 선택이 비게 한다.
    fit_all: 선택이 빈 Home은 노드만 맞추고(주석 제목이 위로 잘림) 줌 1:1에서 안 움직이기도 한다.
    그래서 Ctrl+A(주석 포함 전체 선택) → Home → 3초 → 더미 knot으로 선택만 풀고(뷰 유지) Home 없이 찍는다."""
    if fit_all:
        mcp(SI, "Click", {"ref": anchor, "button": "right"}, port)
        mcp(SI, "PressKey", {"key": "Escape"}, port)
        mcp(SI, "PressKey", {"key": "Ctrl+A"}, port)
        mcp(SI, "PressKey", {"key": "Home"}, port)
        time.sleep(3)
    set_clipboard(knot_block("K2Node_Knot_Desel", 0, 0))
    ui_paste_and_read(graph_ref, anchor, "K2Node_Knot_Desel", False, port)
    if not fit_all:
        mcp(SI, "PressKey", {"key": "Home"}, port)
        time.sleep(1.5)
    return save_shot(shot, port)


def save_shot(path, port, ref=""):
    data = mcp(SI, "Screenshot", {"ref": ref}, port)["data"]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as f:
        f.write(base64.b64decode(data))
    return path


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("calib")
    for name in ("paste", "preview"):
        p = sub.add_parser(name)
        p.add_argument("spec")
        p.add_argument("--layout")
        if name == "paste":
            p.add_argument("--L", required=True, help="calibrated paste location x,y")
    sub.add_parser("verify")
    f = sub.add_parser("ui-find")
    f.add_argument("window_ref")
    f.add_argument("--port", type=int, default=8000)
    uc = sub.add_parser("ui-calib")
    uc.add_argument("graph_ref", help="예: /Game/X/BP_X.BP_X:EventGraph")
    uc.add_argument("anchor", help="워터마크 text ref (ui-find)")
    uc.add_argument("--port", type=int, default=8000)
    uz = sub.add_parser("ui-close", help="에셋 에디터 탭 닫기 (저장 후)")
    uz.add_argument("asset_name")
    uz.add_argument("--window", required=True)
    uz.add_argument("--port", type=int, default=8000)
    us = sub.add_parser("ui-shot", help="그래프를 열고 선택 해제·전체 맞춤 후 스크린샷만")
    us.add_argument("graph_ref", help="예: /Game/X/BP_X.BP_X:EventGraph")
    us.add_argument("out")
    us.add_argument("--window", required=True)
    us.add_argument("--port", type=int, default=8000)
    us.add_argument("--fit-all", action="store_true", help="Ctrl+A → Home으로 주석까지 맞춘 뒤 찍기")
    ur = sub.add_parser("ui-run", help="탭 열기부터 스크린샷까지 한 그래프를 한 번에")
    ur.add_argument("spec")
    ur.add_argument("graph_ref")
    ur.add_argument("--window", required=True, help="BP 에디터 창 ref (Snapshot ref='' maxDepth 1)")
    ur.add_argument("--layout")
    ur.add_argument("--shot", help="스크린샷 PNG 경로")
    ur.add_argument("--port", type=int, default=8000)
    ur.add_argument("--force", action="store_true")
    ur.add_argument("--fit-all", action="store_true", help="Ctrl+A → Home으로 주석까지 맞춘 뒤 찍기")
    up = sub.add_parser("ui-paste")
    up.add_argument("spec")
    up.add_argument("graph_ref")
    up.add_argument("anchor")
    up.add_argument("--L", required=True)
    up.add_argument("--layout")
    up.add_argument("--port", type=int, default=8000)
    up.add_argument("--force", action="store_true")
    s = sub.add_parser("shot")
    s.add_argument("out")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--ref", default="")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.cmd in CLIPBOARD_COMMANDS:
        acquire_clipboard_lock()

    if args.cmd == "calib":
        path = set_clipboard(knot_block("K2Node_Knot_Cal", 0, 0))
        print(json.dumps({"clipboard": "calibration knot K2Node_Knot_Cal", "file": path}))
        return 0

    if args.cmd == "ui-find":
        print(json.dumps(ui_find(args.window_ref, args.port), ensure_ascii=False))
        return 0

    if args.cmd == "ui-calib":
        set_clipboard(knot_block("K2Node_Knot_Cal", 0, 0))
        res = ui_paste_and_read(args.graph_ref, args.anchor, "K2Node_Knot_Cal", False, args.port)
        print(json.dumps({"L": res["knot"]}))
        return 0

    if args.cmd == "ui-close":
        print(json.dumps({"closed": close_asset_tab(args.window, args.asset_name, args.port)}))
        return 0

    if args.cmd == "ui-shot":
        anchor = open_graph(args.window, args.graph_ref.split(":")[-1], args.port)
        print(json.dumps({"png": fit_and_shot(args.graph_ref, anchor, args.out, args.port, args.fit_all)}))
        return 0

    if args.cmd == "verify":
        objs = parse_t3d(get_clipboard())
        comments = [o for o in objs if o["class"] == "EdGraphNode_Comment"]
        knots = [o for o in objs if o["class"] == "K2Node_Knot"]
        for o in comments:
            print(json.dumps({"name": o["name"], "pos": [o.get("NodePosX", 0), o.get("NodePosY", 0)],
                              "size": [o.get("NodeWidth"), o.get("NodeHeight")],
                              "title": o.get("NodeComment", "").split("\n")[0]}, ensure_ascii=False))
        print(json.dumps({"objects": len(objs), "comments": len(comments), "knots": [k["name"] for k in knots]}))
        return 0

    if args.cmd == "shot":
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        cmd = [sys.executable, os.path.join(HERE, "mcp_http.py"), "--port", str(args.port), "--out",
               args.out + ".b64.txt", "call", "SlateInspectorToolset.SlateInspectorToolset", "Screenshot",
               json.dumps({"ref": args.ref})]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            print(r.stdout[-1000:], r.stderr[-1000:])
            return 1
        with open(args.out + ".b64.txt", encoding="utf-8") as f:
            data = json.loads(f.read())["returnValue"]["data"]
        with open(args.out, "wb") as f:
            f.write(base64.b64decode(data))
        os.remove(args.out + ".b64.txt")
        print(json.dumps({"png": args.out, "bytes": os.path.getsize(args.out)}))
        return 0

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    layout = None
    if args.layout:
        with open(args.layout, encoding="utf-8") as f:
            layout = json.load(f)
    boxes = resolve_boxes(spec, layout)
    problems = check(spec, boxes, layout)
    report = [{"i": i, "title": c["text"].split("\n")[0], "box": boxes[i]} for i, c in enumerate(spec)]

    if args.cmd == "preview":
        print(json.dumps({"comments": report, "problems": problems}, ensure_ascii=False))
        return 0

    if args.cmd == "ui-run":
        if problems and not args.force:
            print(json.dumps({"problems": problems, "note": "fix spec/layout or pass --force"}, ensure_ascii=False))
            return 1
        print(json.dumps(ui_run(args.window, args.graph_ref, spec, boxes, args.shot, args.port, args.fit_all), ensure_ascii=False))
        return 0
    lx, ly = (float(v) for v in args.L.split(","))
    kx, ky, path = put_paste_on_clipboard(spec, boxes, lx, ly)
    if args.cmd == "ui-paste":
        if problems and not args.force:
            print(json.dumps({"problems": problems, "note": "fix spec/layout or pass --force"}, ensure_ascii=False))
            return 1
        print(json.dumps(ui_paste_verify(args.graph_ref, args.anchor, boxes, kx, ky, args.port), ensure_ascii=False))
        return 0
    print(json.dumps({"comments": report, "problems": problems,
                      "counterweight_knot": "K2Node_Knot_Counterweight",
                      "expected_knot_pos": [kx, ky], "file": path}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
