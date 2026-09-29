"""graph_layout.py layout 결과(JSON)의 이벤트 체인들을 '블록' 단위로 다시 쌓는다(주석 패스 9단계).
자동 배치(wrap)는 체인을 면적 기준 열로만 나눠서 의미가 같은 체인(예: 전투 입력 7개)이 흩어진다.
이 스크립트는 사람이 정한 묶음대로 체인을 열에 세로로 쌓고, 블록끼리는 간격(기본 480)을 둔다. 체인 안 상대 위치는 그대로.

  python Tools/graph_arrange.py <layout.json> <arrange.json> <out.layout.json>
arrange.json:
  {"vgap": 96, "cgap": 192, "blocks": [
     {"x": 0, "y": 0, "cols": [["K2Node_Event_0", "K2Node_Event_2"]], "vgap": 352},
     {"x": {"right_of": 0, "gap": 480}, "y": 0, "cols": [[...], [...]], "cgap": 352},
     {"x": 0, "y": {"below": 0, "gap": 480}, "cols": [[...]]}]}
  - 체인 이름은 layout 결과 chains[].root (rows 출력의 '-- K2Node_...' 줄). 모든 체인을 한 번씩 넣어야 한다.
  - 한 블록 안에 주석 박스를 둘 이상 둘 체인 사이는 vgap/cgap을 352 이상으로(박스 제목·여백 자리).
결과는 preview → apply에 그대로 쓴다. 예: docs/comment-specs/BP_SCPlayerController__EventGraph.arrange.json
"""
import json,sys
L=json.load(open(sys.argv[1],encoding="utf-8")); A=json.load(open(sys.argv[2],encoding="utf-8"))
vg=A.get("vgap",96); cg=A.get("cgap",192)
ch={c["root"]:c["nodes"] for c in L["chains"]}
def bbox(ns):
    rs=[L["rects"][n] for n in ns]
    return min(r[0] for r in rs),min(r[1] for r in rs),max(r[0]+r[2] for r in rs),max(r[1]+r[3] for r in rs)
snap=lambda v:int(round(v/16.0))*16
bb=[]; used=set()
for b in A["blocks"]:
    def res(v,axis):
        if isinstance(v,(int,float)): return v
        j=v.get("right_of",v.get("below")); g=v.get("gap",480)
        if "right_of" in v: return bb[j][2]+g if axis=="x" else bb[j][1]
        return bb[j][3]+g if axis=="y" else bb[j][0]
    bx=res(b["x"],"x"); by=res(b["y"],"y")
    cx=bx; maxx=bx; maxy=by; vg=b.get("vgap",A.get("vgap",96)); cg=b.get("cgap",A.get("cgap",192))
    for col in b["cols"]:
        cy=by; colw=0
        for root in col:
            ns=ch[root]; used.add(root)
            x0,y0,x1,y1=bbox(ns); dx=snap(cx-x0); dy=snap(cy-y0)
            for n in ns:
                L["pos"][n]=[L["pos"][n][0]+dx,L["pos"][n][1]+dy]
                r=L["rects"][n]; L["rects"][n]=[r[0]+dx,r[1]+dy,r[2],r[3]]
            cy=snap(cy+(y1-y0)+vg); colw=max(colw,x1-x0)
            maxy=max(maxy,y0+dy+(y1-y0))
        cx=snap(cx+colw+cg); maxx=max(maxx,cx-cg)
    bb.append((bx,by,maxx,maxy))
missing=[c for c in ch if c not in used]
if missing: raise SystemExit("unplaced chains: %s"%missing)
json.dump(L,open(sys.argv[3],"w",encoding="utf-8"),ensure_ascii=False,indent=0)
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph_layout
print(json.dumps({"blocks":bb,"overlaps":graph_layout.overlaps(L["rects"])}))
