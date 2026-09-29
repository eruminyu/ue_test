"""블루프린트 그래프 자동 배치 도우미 (주석 패스용).

Unreal MCP의 arrange_nodes는 노드 높이를 모르고 순수 노드를 흩뜨리므로, 노드 정보를 덤프해서
이 스크립트가 행/열 배치를 계산하고 set_node_position으로 적용한다. 로직(핀, 연결)은 건드리지 않는다.
MCP는 Tools/mcp_http.py(HTTP, 기본 8000번 에디터)로 부른다. 한 번에 한 호출만 보내므로 다른 MCP 호출과 겹치지 않게 한다.

사용법 (저장소 루트에서. Git Bash면 먼저 export MSYS_NO_PATHCONV=1 — /Game/... 경로가 C:/Program Files/Git/Game/...으로 바뀐다)
  python Tools/graph_layout.py dump /Game/SoulCombat/Dungeon/BP_DungeonDoor --out door.json [--graphs EventGraph,Foo]
      -> 그래프별 노드(이름, type_id, 위치, 핀 이름/타입/연결/값)를 JSON으로 저장 (ProgrammaticToolset 1회, 그래프를 바꾸지 않음)
  python Tools/graph_layout.py check door.json EventGraph          -> 현재 위치 기준 추정 크기 겹침 검사
  python Tools/graph_layout.py layout door.json EventGraph --out door_eg.layout.json [--breaks "Branch#3,WaitDelay#2"] [--no-wrap]
      -> 새 위치 계산 + 체인 목록 + 겹침 검사. --breaks: 이 노드 앞에서 주석 블록을 나눈다(가로 BLOCK_GAP 추가,
         그 블록의 순수 노드가 블록 시작보다 왼쪽으로 못 나감). 이름은 전체 이름 또는 rows 출력의 "제목#번호".
  python Tools/graph_layout.py rows door_eg.layout.json            -> 체인/행별 "제목#번호@x" 목록 (블록 나누기·주석 spec 작성용)
  python Tools/graph_layout.py apply door_eg.layout.json           -> set_node_position 일괄 적용 (ProgrammaticToolset 1회)
  python Tools/graph_layout.py same-logic before.json after.json   -> 두 덤프의 노드·연결·핀 값이 같은지(위치만 바뀌었는지)

배치 규칙
  - 루트 = 들어오는 exec 연결이 없는 exec 노드(이벤트, 함수 Entry). 원래 y 순서대로 한 체인씩 띠로 쌓고(간격 CHAIN_GAP),
    전체가 너무 길면 오른쪽 새 열로 넘긴다(목표 높이 = 면적의 제곱근, 열 간격 COLUMN_GAP). Home(전체 맞춤)이 최소 줌에서 잘리지 않게.
  - exec 흐름은 왼쪽 -> 오른쪽. 첫 번째 exec 출력은 같은 행, 나머지 출력(then_1, Completed, OnBlendOut ...)은 새 행.
    Branch/IsValid/Cast/Switch는 가장 긴 가지를 같은 행에 둔다(조기 반환이 본 흐름을 끊지 않게).
  - 새 행은 이미 놓인 행과 가로로 겹치지 않는 가장 위 자리(부모 행 아래)에 놓는다 → 조기 반환 노드가 출처 근처에 온다.
  - 순수(데이터) 노드는 처음 소비하는 exec 노드의 왼쪽 아래(데이터 줄)에 깊이별 열로 놓고, 겹치면 아래로 내린다.
    어느 exec 노드와 함께 놓였는지(owner)를 layout JSON에 남겨 주석 블록이 자동으로 포함한다.
  - 노드 크기는 추정(실측 대비 폭 ±20%): 일반 = max(200, 60 + 8*제목, 7*(긴 입력 핀 + 긴 출력 핀) + 90 + 값 위젯 폭) × (64 + 26*핀 행),
    변수 Get = max(120, 8*이름 + 60) × 48, 변수 Set = max(150, 7*(핀 이름) + 70 + 위젯) × (44 + 24*행). 숨은 핀 WorldContextObject/LatentInfo 제외.
"""

import argparse
import json
import os
import subprocess
import sys

sys.setrecursionlimit(10000)

HERE = os.path.dirname(os.path.abspath(__file__))
BT = "editor_toolset.toolsets.blueprint.BlueprintTools"
PT = "editor_toolset.toolsets.programmatic.ProgrammaticToolset"

GAP_X = 100          # exec 노드 사이 가로 간격
ROW_GAP = 160        # 한 체인 안 행 사이 세로 간격 (안쪽 주석 박스 제목 줄이 들어갈 자리)
LANE_GAP = 50        # exec 노드 아래 데이터 줄까지 간격
PURE_GAP_X = 60      # 데이터 노드 열 사이 간격
PURE_GAP_Y = 30      # 데이터 노드 세로 간격
BAND_GAP_X = 120     # 같은 높이에 나란히 놓이는 두 행 사이 최소 가로 간격
BLOCK_GAP = 320      # --breaks로 지정한 노드 앞 추가 가로 간격(주석 블록 경계)
COLUMN_GAP = 800     # --wrap 때 체인 열 사이 가로 간격 (주석 박스 여백 + 제목 때문에 넓어지는 폭)
CHAIN_GAP = 560      # 이벤트 체인(띠) 사이 세로 간격 (바깥 주석 박스 + 축소 시 보이는 제목 말풍선 자리)
HIDDEN_PINS = {"WorldContextObject", "__WorldContext", "LatentInfo"}

DUMP_SCRIPT = r'''
import json
BT = "editor_toolset.toolsets.blueprint.BlueprintTools."
def call(t, a):
    return execute_tool(BT + t, json.dumps(a))["returnValue"]
def short(r):
    return r["refPath"].split(".")[-1]
def run():
    out = {}
    for g in call("list_graphs", {"blueprint": {"refPath": "__BP__"}}):
        gname = g["refPath"].split(":")[-1]
        if __ONLY__ and gname not in __ONLY__:
            continue
        nodes = call("find_nodes", {"graph": g, "title": "", "entry_points_only": False})
        if not nodes:
            out[gname] = []
            continue
        infos = call("get_node_infos", {"nodes": nodes})
        rows = []
        for inf in infos:
            ins = [[p["name"], p["type_id"], [[short(c["node"]), c["index_id"]] for c in p["connected_pins"]], p["value"][:40]] for p in inf["input_pins"]]
            outs = [[p["name"], p["type_id"], [[short(c["node"]), c["index_id"]] for c in p["connected_pins"]]] for p in inf["output_pins"]]
            rows.append({"n": short(inf["node"]), "t": inf["type_id"], "x": inf["position"]["x"], "y": inf["position"]["y"], "i": ins, "o": outs})
        out[gname] = rows
    return out
'''

APPLY_SCRIPT = r'''
import json
POS = __POS__
G = "__G__"
def run():
    n = 0
    for name, p in POS.items():
        execute_tool("editor_toolset.toolsets.blueprint.BlueprintTools.set_node_position",
                     json.dumps({"node": {"refPath": G + "." + name}, "pos": {"x": p[0], "y": p[1]}}))
        n += 1
    return {"moved": n}
'''


def mcp_call(toolset, tool, args, port=8000):
    """Tools/mcp_http.py로 한 번 호출하고 텍스트 결과를 돌려준다."""
    tmp = os.path.join(os.environ.get("TEMP", "."), "graph_layout_args.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(args, f)
    outp = os.path.join(os.environ.get("TEMP", "."), "graph_layout_out.txt")
    cmd = [sys.executable, os.path.join(HERE, "mcp_http.py"), "--port", str(port), "--out", outp,
           "call", toolset, tool, "@" + tmp]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(r.stdout[-2000:] + r.stderr[-2000:])
    with open(outp, encoding="utf-8") as f:
        return f.read()


def bp_ref(path):
    if "." not in path.split("/")[-1]:
        path = path + "." + path.split("/")[-1]
    return path


# ---------------------------------------------------------------- node size estimate

def title_of(node):
    t = node["t"].split("|")[-1]
    return t or node["n"]


def is_exec_pin(p):
    return p[1] == "Exec"


def widget_width(ptype):
    t = ptype
    if "Vector" in t or "Rotator" in t:
        return 210
    if "Transform" in t:
        return 260
    if "Gameplay Tag" in t or "Class Reference" in t or "Attribute" in t:
        return 170
    if any(k in t for k in ("Montage", "Anim", "Material", "Texture", "Sound", "Niagara", "Curve", "Data Table", "Data Asset")):
        return 170
    if "String" in t or "Name" in t or "Text" in t:
        return 110
    if "Float" in t or "Integer" in t or "Byte" in t or "double" in t or "Enum" in t:
        return 70
    if "Boolean" in t:
        return 30
    return 20


def node_size(node):
    ins = [p for p in node["i"] if p[0] not in HIDDEN_PINS]
    outs = [p for p in node["o"] if p[0] not in HIDDEN_PINS]
    title = title_of(node)
    vget = node["n"].startswith("K2Node_VariableGet")
    vset = node["n"].startswith("K2Node_VariableSet")
    knot = node["n"].startswith("K2Node_Knot")
    if knot:
        return 48, 32
    in_len = max([len(p[0]) for p in ins] + [0])
    out_len = max([len(p[0]) for p in outs] + [0])
    wid = max([widget_width(p[1]) for p in ins if not p[2] and not is_exec_pin(p)] + [0])
    rows = max(len(ins), len(outs), 1)
    if vget:   # 제목 없는 작은 노드: [변수 이름 o]
        return int(max(120, 8 * out_len + 60)), 48
    if vset:   # 제목 "SET", 핀 이름 + 값 위젯
        return int(max(150, 7 * (in_len + out_len) + 70 + wid)), int(44 + 24 * rows)
    w = max(200, 60 + 8 * len(title), 7 * (in_len + out_len) + 90 + wid)
    h = 64 + 26 * rows   # 실측: 핀 많은 노드(SphereOverlapActors 6행 ≈ 230)는 60+24*행보다 약 10% 크다
    return int(w), int(h)


# ---------------------------------------------------------------- graph helpers

def build(nodes):
    by = {n["n"]: n for n in nodes}
    execn = set()
    for n in nodes:
        if any(is_exec_pin(p) for p in n["i"] + n["o"]):
            execn.add(n["n"])
    exec_in = {k: 0 for k in by}
    for n in nodes:
        for p in n["o"]:
            if is_exec_pin(p):
                for c in p[2]:
                    if c[0] in exec_in:
                        exec_in[c[0]] += 1
    return by, execn, exec_in


def is_branch_like(node):
    """가지 중 가장 긴 쪽을 같은 행에 둘 노드(조건 분기). Sequence, 루프, 태스크는 핀 순서를 지킨다."""
    t = node["t"]
    return t.endswith("|Branch") or "IsValid" in t or "CastTo" in t or "Switch" in t


def providers(node, by, execn):
    """node의 입력 핀에 연결된 순수 노드들(핀 순서)."""
    res = []
    for p in node["i"]:
        if is_exec_pin(p):
            continue
        for c in p[2]:
            if c[0] in by and c[0] not in execn and c[0] not in res:
                res.append(c[0])
    return res


def overlaps(rects, margin=0):
    items = list(rects.items())
    bad = []
    for i in range(len(items)):
        a, (ax, ay, aw, ah) = items[i]
        for j in range(i + 1, len(items)):
            b, (bx, by_, bw, bh) = items[j]
            if ax < bx + bw + margin and bx < ax + aw + margin and ay < by_ + bh + margin and by_ < ay + ah + margin:
                bad.append((a, b))
    return bad


# ---------------------------------------------------------------- layout

def layout_graph(nodes, breaks=(), wrap=True):
    breaks = set(breaks)
    by, execn, exec_in = build(nodes)
    size = {n["n"]: node_size(n) for n in nodes}
    roots = [n for n in nodes if n["n"] in execn and exec_in[n["n"]] == 0]
    roots.sort(key=lambda n: (n["y"], n["x"]))
    placed = {}
    owner = {}    # 순수 노드 -> 함께 배치된 exec 노드 (주석 블록에 자동 포함)
    chains = []
    cur_y = 0

    for root in roots:
        if root["n"] in placed:
            continue
        rows = []          # 각 행: exec 노드 목록 [(name, x)]
        rel = {}           # name -> (x, row) for exec
        pure = {}          # name -> (x, row, dy) for pure

        parent_row = []

        def new_row(parent=None):
            rows.append([])
            parent_row.append(parent)
            return len(rows) - 1

        # exec 흐름 배치 (재귀, 노드 수 수백 개 이하라 충분)
        def reach(start):
            """start에서 exec로 닿는, 아직 안 놓인 노드 수 (가장 긴 가지를 같은 행에 두기 위해)."""
            seen = {start}
            stack = [start]
            while stack:
                k = stack.pop()
                for p in by[k]["o"]:
                    if is_exec_pin(p):
                        for c in p[2]:
                            if c[0] in by and c[0] not in seen and c[0] not in rel and c[0] not in placed:
                                seen.add(c[0])
                                stack.append(c[0])
            return len(seen)

        bstart = {}   # exec 노드 -> 속한 블록의 시작 x (--breaks 기준). 순수 노드 묶음이 이보다 왼쪽으로 못 나간다

        def place_rec(nm, xx, rr, bs=-10 ** 9):
            if nm in rel or nm in placed:
                return
            rel[nm] = (xx, rr)
            bstart[nm] = bs
            rows[rr].append(nm)
            targets = []
            for p in by[nm]["o"]:
                if not is_exec_pin(p):
                    continue
                for c in p[2]:
                    t = c[0]
                    if t in by and t not in rel and t not in placed and t not in targets:
                        targets.append(t)
            if len(targets) > 1 and is_branch_like(by[nm]):
                main = max(targets, key=reach)   # 동률이면 핀 순서가 앞선 것
                targets.remove(main)
                targets.insert(0, main)
            for i, t in enumerate(targets):
                if t in rel or t in placed:
                    continue
                nx = xx + size[nm][0] + GAP_X + (BLOCK_GAP if t in breaks else 0)
                place_rec(t, nx, rr if i == 0 else new_row(rr), nx if t in breaks else bs)

        r0 = new_row()
        place_rec(root["n"], 0, r0)

        # 순수 노드: 행별 데이터 줄
        row_pure_rects = {r: [] for r in range(len(rows))}
        for r, members in enumerate(rows):
            for nm in sorted(members, key=lambda k: rel[k][0]):
                ex_x = rel[nm][0]
                # 깊이별 열 수집
                cols = []
                frontier = [p for p in providers(by[nm], by, execn) if p not in pure and p not in placed]
                seen = set(frontier)
                while frontier:
                    cols.append(frontier)
                    nxt = []
                    for q in frontier:
                        for p in providers(by[q], by, execn):
                            if p not in seen and p not in pure and p not in placed:
                                seen.add(p)
                                nxt.append(p)
                    frontier = nxt
                if not cols:
                    continue
                right = ex_x + min(size[nm][0], 240)
                colx = []
                x = right
                for col in cols:
                    cw = max(size[q][0] for q in col)
                    x = x - cw
                    colx.append((x, cw))
                    x -= PURE_GAP_X
                shift = max(0, bstart[nm] - x - PURE_GAP_X)   # 블록 시작보다 왼쪽이면 오른쪽으로
                colx = [(cx + shift, cw) for (cx, cw) in colx]
                group = []
                for col, (cx, cw) in zip(cols, colx):
                    yy = 0
                    for q in col:
                        w, h = size[q]
                        group.append([q, cx + (cw - w), yy, w, h])
                        yy += h + PURE_GAP_Y
                # 겹치면 그룹 전체를 아래로
                dy = 0
                for _ in range(200):
                    hit = None
                    for g in group:
                        for (px, py, pw, ph) in row_pure_rects[r]:
                            gx, gy, gw, gh = g[1], g[2] + dy, g[3], g[4]
                            if gx < px + pw + 40 and px < gx + gw + 40 and gy < py + ph + PURE_GAP_Y and py < gy + gh + PURE_GAP_Y:
                                hit = py + ph + PURE_GAP_Y - g[2]
                                break
                        if hit is not None:
                            break
                    if hit is None:
                        break
                    dy = max(dy + 16, hit)
                for g in group:
                    owner[g[0]] = nm
                    pure[g[0]] = (g[1], r, g[2] + dy)
                    row_pure_rects[r].append((g[1], g[2] + dy, g[3], g[4]))

        # 행 y 계산: 행마다 (exec 줄 + 데이터 줄) 사각형을 하나의 덩어리로 보고, 할당 순서대로
        # 이미 놓인 행과 가로로 겹치지 않는 가장 위 자리(부모 행보다 아래)에 놓는다 (조기 반환 행이 출처 근처로 올라온다).
        row_y = []
        boxes = []   # (x0, x1, y0, y1)
        for r, members in enumerate(rows):
            eh = max([size[m][1] for m in members] + [0])
            ph = max([py + ph_ for (_, py, _, ph_) in row_pure_rects[r]] + [0])
            height = eh + (LANE_GAP + ph if ph else 0)
            xs = [rel[m][0] for m in members] + [px for (px, _, _, _) in row_pure_rects[r]]
            xe = [rel[m][0] + size[m][0] for m in members] + [px + pw for (px, _, pw, _) in row_pure_rects[r]]
            x0, x1 = min(xs), max(xe)
            y = cur_y
            if parent_row[r] is not None:
                y = max(y, row_y[parent_row[r]] + 1)
            moved = True
            while moved:
                moved = False
                for (bx0, bx1, by0, by1) in boxes:
                    if x0 < bx1 + BAND_GAP_X and bx0 < x1 + BAND_GAP_X and y < by1 + ROW_GAP and by0 < y + height + ROW_GAP:
                        y = by1 + ROW_GAP
                        moved = True
            row_y.append(y)
            boxes.append((x0, x1, y, y + height))
        chain_nodes = []
        for nm, (xx, rr) in rel.items():
            placed[nm] = (xx, row_y[rr])
            chain_nodes.append(nm)
        for nm, (xx, rr, dy) in pure.items():
            eh = max(size[m][1] for m in rows[rr])
            placed[nm] = (xx, row_y[rr] + eh + LANE_GAP + dy)
            chain_nodes.append(nm)
        # 체인 왼쪽 끝을 0에 맞춘다
        minx = min(placed[n][0] for n in chain_nodes)
        for n in chain_nodes:
            placed[n] = (placed[n][0] - minx, placed[n][1])
        bottom = max(placed[n][1] + size[n][1] for n in chain_nodes)
        chains.append({"root": root["n"], "root_type": root["t"], "rows": len(rows), "nodes": chain_nodes,
                       "top": cur_y, "bottom": bottom})
        cur_y = bottom + CHAIN_GAP

    # 어디에도 안 붙은 노드(연결 없는 순수 노드 등)는 맨 아래 한 줄
    rest = [n["n"] for n in nodes if n["n"] not in placed]
    if rest:
        x = 0
        for nm in rest:
            placed[nm] = (x, cur_y)
            x += size[nm][0] + GAP_X
        chains.append({"root": None, "root_type": "unplaced", "rows": 1, "nodes": rest, "top": cur_y,
                       "bottom": cur_y + max(size[n][1] for n in rest)})

    if wrap and len(chains) > 1:
        wrap_columns(chains, placed, size)

    snapped = {k: (int(round(v[0] / 16.0)) * 16, int(round(v[1] / 16.0)) * 16) for k, v in placed.items()}
    rects = {k: (snapped[k][0], snapped[k][1], size[k][0], size[k][1]) for k in snapped}
    return snapped, rects, chains, owner


def wrap_columns(chains, placed, size):
    """체인(띠)을 세로로만 쌓으면 그래프가 너무 길어져 전체 맞춤(Home)에서도 안 들어온다.
    전체 면적의 제곱근(가장 높은 체인 이상)을 목표 높이로 두고, 넘치면 오른쪽 새 열에 이어 쌓는다."""
    info = []
    for c in chains:
        xs = [placed[n][0] for n in c["nodes"]]
        xe = [placed[n][0] + size[n][0] for n in c["nodes"]]
        ys = [placed[n][1] for n in c["nodes"]]
        ye = [placed[n][1] + size[n][1] for n in c["nodes"]]
        info.append((min(xs), max(xe), min(ys), max(ye)))
    area = sum((x1 - x0) * (y1 - y0) for x0, x1, y0, y1 in info)
    target = max(max(y1 - y0 for _, _, y0, y1 in info), area ** 0.5)
    col_x, col_w, y = 0, 0, 0
    for c, (x0, x1, y0, y1) in zip(chains, info):
        h = y1 - y0
        if y > 0 and y + h > target:
            col_x += col_w + COLUMN_GAP
            col_w, y = 0, 0
        dx, dy = col_x - x0, y - y0
        for n in c["nodes"]:
            placed[n] = (placed[n][0] + dx, placed[n][1] + dy)
        c["top"], c["bottom"], c["left"] = y, y + h, col_x
        col_w = max(col_w, x1 - x0)
        y += h + CHAIN_GAP


def current_rects(nodes):
    return {n["n"]: (n["x"], n["y"]) + node_size(n) for n in nodes}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump")
    d.add_argument("bp")
    d.add_argument("--graphs", default="", help="쉼표로 구분한 그래프 이름만")
    d.add_argument("--out", required=True)
    c = sub.add_parser("check")
    c.add_argument("dump")
    c.add_argument("graph")
    l = sub.add_parser("layout")
    l.add_argument("dump")
    l.add_argument("graph")
    l.add_argument("--out", required=True)
    l.add_argument("--no-wrap", action="store_true", help="체인을 한 열로만 쌓는다(기본: 너무 길면 여러 열)")
    l.add_argument("--breaks", default="", help="쉼표로 구분한 노드 이름: 이 노드 앞에서 블록을 나눠 가로 간격을 더 준다")
    v_ = sub.add_parser("same-logic", help="두 덤프의 연결·핀 값이 같은지 (위치만 바뀌었는지) 확인")
    v_.add_argument("before")
    v_.add_argument("after")
    r_ = sub.add_parser("rows", help="레이아웃 결과를 체인/행별 제목으로 출력 (블록 나누기용)")
    r_.add_argument("layout")
    a_ = sub.add_parser("apply")
    a_.add_argument("layout")
    args = ap.parse_args()

    if args.cmd == "dump":
        ref = bp_ref(args.bp)
        only = [g for g in args.graphs.split(",") if g]
        script = DUMP_SCRIPT.replace("__BP__", ref).replace("__ONLY__", json.dumps(only))
        text = mcp_call(PT, "execute_tool_script", {"script": script}, args.port)
        data = json.loads(json.loads(text)["returnValue"])
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"bp": ref, "graphs": data}, f, ensure_ascii=False, indent=0)
        print(json.dumps({g: len(v) for g, v in data.items()}))
        return 0

    if args.cmd == "same-logic":
        a = json.load(open(args.before, encoding="utf-8"))["graphs"]
        b = json.load(open(args.after, encoding="utf-8"))["graphs"]
        res = {}
        for g in a:
            def sig(nodes):
                return sorted((n["n"], n["t"], tuple(p[0] + "=" + p[3] for p in n["i"]),
                               tuple(sorted((p[0], c[0], c[1]) for p in n["o"] for c in p[2]))) for n in nodes)
            bg = b.get(g, [])   # 남은 보정·균형추 knot도 차이로 잡힌다
            res[g] = "same" if sig(a[g]) == sig(bg) else "DIFFERENT"
        print(json.dumps(res))
        return 0 if all(v == "same" for v in res.values()) else 1

    with open(getattr(args, "dump", None) or args.layout, encoding="utf-8") as f:
        data = json.load(f)

    if args.cmd == "check":
        nodes = data["graphs"][args.graph]
        bad = overlaps(current_rects(nodes))
        print(json.dumps({"nodes": len(nodes), "overlaps": bad}))
        return 0

    if args.cmd == "layout":
        nodes = data["graphs"][args.graph]
        brk = []
        for b in [b for b in args.breaks.split(",") if b]:
            if "#" in b:   # rows 출력 형식 "제목#번호"
                t, num = b.rsplit("#", 1)
                hits = [n["n"] for n in nodes if title_of(n) == t and n["n"].rsplit("_", 1)[-1] == num]
                if len(hits) != 1:
                    raise SystemExit(f"cannot resolve break {b}: {hits}")
                b = hits[0]
            brk.append(b)
        pos, rects, chains, owner = layout_graph(nodes, brk, not args.no_wrap)
        bad = overlaps(rects)
        out = {"bp": data["bp"], "graph": args.graph,
               "graph_ref": data["bp"] + ":" + args.graph,
               "pos": pos, "rects": rects, "chains": chains,
               "titles": {n["n"]: title_of(n) for n in nodes}, "breaks": args.breaks, "owner": owner}
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=0)
        print(json.dumps({"nodes": len(nodes), "overlaps": bad,
                          "chains": [{"root": c["root"], "type": c["root_type"], "n": len(c["nodes"]),
                                      "rows": c["rows"], "y": [c["top"], c["bottom"]]} for c in chains]},
                         ensure_ascii=False))
        return 0

    if args.cmd == "rows":
        for c in data["chains"]:
            print("--", c["root"], c["root_type"], "rows", c["rows"], "y", c["top"], c["bottom"])
            rows = {}
            for n in c["nodes"]:
                rows.setdefault(data["rects"][n][1], []).append(n)
            for y in sorted(rows):
                items = sorted(rows[y], key=lambda k: data["rects"][k][0])
                print("  y%-5d" % y, " | ".join("%s#%s@%d" % (data["titles"][n], n.rsplit("_", 1)[-1], data["rects"][n][0]) for n in items))
        return 0

    if args.cmd == "apply":
        script = APPLY_SCRIPT.replace("__POS__", json.dumps(data["pos"])).replace("__G__", data["graph_ref"])
        print(mcp_call(PT, "execute_tool_script", {"script": script}, args.port))
        return 0


if __name__ == "__main__":
    sys.exit(main())
