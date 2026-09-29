"""블루프린트 그래프 주석 박스를 클립보드 붙여넣기로 만드는 도우미.

Unreal MCP에는 주석 박스(EdGraphNode_Comment)의 텍스트, 위치, 크기를 정하는 툴이 없다.
대신 블루프린트 에디터가 클립보드의 T3D 텍스트를 붙여넣을 수 있으므로, 이 스크립트가 T3D를 만들어 클립보드에 넣는다.
붙여넣기는 "붙여넣은 노드들의 평균 위치"를 붙여넣기 지점 L로 옮기므로, 균형추(reroute knot)를 하나 섞어
평균이 정확히 L이 되게 하면 모든 주석이 지정한 절대 좌표에 놓인다 (docs/mcp/probe-bp-core.md 레시피 A).

순서
  1. python Tools/graph_comments.py calib
     -> (0,0) knot 하나를 클립보드에 넣는다. 그래프를 클릭(SlateInspector)하고 Ctrl+V,
        get_node_infos로 K2Node_Knot_Cal의 위치를 읽으면 그게 L이다. 그 knot은 delete_node로 지운다.
  2. python Tools/graph_comments.py paste spec.json --L 48,416
     -> 주석들 + 균형추 knot을 클립보드에 넣고, knot이 놓여야 할 좌표를 출력한다.
        같은 곳을 클릭하고 Ctrl+V → knot 위치가 출력값(±16)인지 확인 → knot을 delete_node로 지운다.

spec.json 형식 (둘 중 하나, 섞어도 된다)
  [
    {"text": "입력 처리", "x": 0, "y": 0, "w": 900, "h": 400, "color": [0.1, 0.4, 0.9], "font": 18},
    {"text": "피해 적용", "nodes": [[x, y], [x, y, w, h], ...], "pad": 48, "color": [0.9, 0.5, 0.1]}
  ]
  "nodes"를 주면 노드 좌표(get_node_infos의 position)로 상자를 계산한다. 노드 크기를 모르면 w=320, h=180으로 가정한다.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

TITLE_BAR = 64          # 주석 제목 줄 높이만큼 위로 여유
DEFAULT_NODE_W = 320
DEFAULT_NODE_H = 180
DEFAULT_PAD = 48
GRID = 16


def snap(v):
    return int(round(v / GRID)) * GRID


def box_from_nodes(nodes, pad):
    xs0, ys0, xs1, ys1 = [], [], [], []
    for n in nodes:
        x, y = n[0], n[1]
        w = n[2] if len(n) > 2 else DEFAULT_NODE_W
        h = n[3] if len(n) > 3 else DEFAULT_NODE_H
        xs0.append(x)
        ys0.append(y)
        xs1.append(x + w)
        ys1.append(y + h)
    x0 = min(xs0) - pad
    y0 = min(ys0) - pad - TITLE_BAR
    x1 = max(xs1) + pad
    y1 = max(ys1) + pad
    return snap(x0), snap(y0), snap(x1 - x0), snap(y1 - y0)


def escape(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


def comment_block(i, c):
    if "nodes" in c:
        x, y, w, h = box_from_nodes(c["nodes"], c.get("pad", DEFAULT_PAD))
    else:
        x, y, w, h = snap(c["x"]), snap(c["y"]), snap(c["w"]), snap(c["h"])
    r, g, b = (c.get("color") or [1.0, 1.0, 1.0])[:3]
    font = int(c.get("font", 18))
    block = (
        f'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="EdGraphNode_Comment_SC{i}"\n'
        f"   CommentColor=(R={r:.6f},G={g:.6f},B={b:.6f},A=1.000000)\n"
        f"   FontSize={font}\n"
        f"   bCommentBubbleVisible_InDetailsPanel=False\n"
        f"   NodePosX={x}\n"
        f"   NodePosY={y}\n"
        f"   NodeWidth={w}\n"
        f"   NodeHeight={h}\n"
        f'   NodeComment="{escape(c["text"])}"\n'
        f"End Object\n"
    )
    return block, (x, y)


def knot_block(name, x, y):
    return (
        f'Begin Object Class=/Script/BlueprintGraph.K2Node_Knot Name="{name}"\n'
        f"   NodePosX={x}\n"
        f"   NodePosY={y}\n"
        f"End Object\n"
    )


def set_clipboard(text):
    fd, path = tempfile.mkstemp(suffix=".t3d")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    cmd = f"Set-Clipboard -Value (Get-Content -Raw -Encoding UTF8 '{path}')"
    subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=True)
    return path


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("calib")
    p = sub.add_parser("paste")
    p.add_argument("spec")
    p.add_argument("--L", required=True, help="calibrated paste location x,y")
    args = ap.parse_args()

    if args.cmd == "calib":
        path = set_clipboard(knot_block("K2Node_Knot_Cal", 0, 0))
        print(json.dumps({"clipboard": "calibration knot K2Node_Knot_Cal", "file": path}))
        return

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    lx, ly = (float(v) for v in args.L.split(","))
    blocks, positions = [], []
    for i, c in enumerate(spec):
        block, pos = comment_block(i, c)
        blocks.append(block)
        positions.append(pos)
    n = len(positions)
    kx = snap((n + 1) * lx - sum(p[0] for p in positions))
    ky = snap((n + 1) * ly - sum(p[1] for p in positions))
    blocks.append(knot_block("K2Node_Knot_Counterweight", kx, ky))
    path = set_clipboard("".join(blocks))
    print(json.dumps({
        "comments": [{"text": c["text"], "pos": positions[i]} for i, c in enumerate(spec)],
        "counterweight_knot": "K2Node_Knot_Counterweight",
        "expected_knot_pos": [kx, ky],
        "file": path,
    }, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
