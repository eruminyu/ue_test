# 그래프 정리·주석 패스 레시피 (9단계)

블루프린트 그래프를 사람이 읽기 좋게 다시 배치하고, 기능 블록마다 한국어 주석 박스를 붙이는 절차다.
파일럿(BP_DungeonDoor, AC_CombatComponent, GA_Player_BasicAttack, 13개 그래프)에서 확인했다. 로직은 바꾸지 않는다.
노드 위치만 바꾸고, 주석은 클립보드 붙여넣기(T3D)로 넣는다. 끝에서 덤프를 비교해 로직이 같은지 확인한다.

도구
- `Tools/graph_layout.py`: 그래프 덤프(dump), 자동 배치 계산(layout), 행 목록(rows), 적용(apply), 로직 비교(same-logic)
- `Tools/graph_comments.py`: 주석 박스 계산·검사(preview), 한 그래프 전체 자동 실행(ui-run), 스크린샷(ui-shot), 탭 닫기(ui-close)
- 두 도구 모두 `Tools/mcp_http.py`로 8000번 에디터 MCP를 HTTP로 부른다. 결과가 큰 호출(덤프, 스냅샷, 스크린샷)을 파일로 받아
  컨텍스트를 아낀다. **호출은 순서대로 하나씩만**. 도구가 도는 동안 다른 MCP 호출을 하지 않는다.
- 작업 예시(spec)는 `docs/comment-specs/` (`breaks.json`에 쓴 `--breaks` 값). 스크린샷은 `docs/screenshots/graphs/<BP>__<Graph>.png`.

## 0. 준비 (세션마다 한 번)

```bash
cd <repo root>
export MSYS_NO_PATHCONV=1      # Git Bash: 안 하면 /Game/... 인자가 C:/Program Files/Git/Game/...으로 바뀐다
S=<scratchpad>/cp; mkdir -p $S
```
- ProgrammaticToolset `get_execution_environment`를 세션에서 한 번 불러 둔다(스크립트 실행 전 요구).
- BP 에디터 창 ref: `EditorAppToolset OpenEditorForAsset` 뒤 `SlateInspectorToolset Snapshot {"ref":"","maxDepth":4}`에서
  `window "<BP 이름>" [ref=w116]`. 에셋 에디터는 모두 **같은 창**(탭)으로 열리고, 창 ref는 에셋을 바꿔도 그대로였다(w116).
  창 제목이 방금 연 에셋 이름으로 바뀐다(`Windows {"action":"list"}`로 확인).

## 1. BP 하나 처리 순서

```bash
BP=/Game/SoulCombat/Components/AC_CombatComponent; N=AC_CombatComponent
python Tools/graph_layout.py dump $BP --out $S/$N.json            # 모든 그래프, ~3초. 원본 로직 기록(나중에 비교)
# 그래프마다 (G = EventGraph, 함수 이름 ...)
python Tools/graph_layout.py layout $S/$N.json $G --out $S/${N}_$G.layout.json [--breaks "Title#N,..."]
python Tools/graph_layout.py rows $S/${N}_$G.layout.json          # 행별 "제목#번호@x" → 블록 나누기, spec 작성
#   spec 작성: $S/${N}_$G.spec.json (아래 2절)
python Tools/graph_comments.py preview $S/${N}_$G.spec.json --layout $S/${N}_$G.layout.json   # problems: [] 이어야 함
python Tools/graph_layout.py apply $S/${N}_$G.layout.json         # set_node_position 일괄, ~2초
```
그다음 에디터:
1. MCP `EditorAppToolset OpenEditorForAsset {"assetPath":"<BP>"}` (직접 호출).
2. 그래프마다
   `python Tools/graph_comments.py ui-run $S/${N}_$G.spec.json $BP.$N:$G --window w116 --layout $S/${N}_$G.layout.json --shot docs/screenshots/graphs/${N}__$G.png`
   - 그래프 ref 형식: `/Game/SoulCombat/Components/AC_CombatComponent.AC_CombatComponent:ApplyHit`.
   - 결과 JSON에서 `knot_ok: true`, `mismatch: []`, `comments_pasted` = spec 박스 수 확인. 하나라도 아니면 멈추고 본다.
   - 스크린샷 PNG를 반드시 열어 본다(Read). 겹침·잘림이 있으면 5절(되돌리기)로 지우고 고친다.
3. MCP `BlueprintTools compile_blueprint {"blueprint":..,"warnings_as_errors":true}` → `null`이면 성공.
4. MCP `AssetTools save_assets {"asset_paths":["<BP>"]}` (경로 명시).
5. `python Tools/graph_comments.py ui-close $N --window w116` (저장 뒤. 에셋 탭의 닫기 버튼).
6. 로직 비교: `python Tools/graph_layout.py dump $BP --out $S/${N}_after.json` →
   `python Tools/graph_layout.py same-logic $S/$N.json $S/${N}_after.json` → 모든 그래프 `"same"`.
   DIFFERENT가 나오면 노드별 핀 값/연결을 비교해 원래 값으로 되돌린다(`set_pin_value`, `connect_pins`), 다시 저장.
7. `AssetTools is_dirty` false 확인.

빈 그래프(Entry 노드 하나뿐인 ConstructionScript, 디스패처 시그니처 그래프 OnX)는 건너뛴다.

## 2. 블록 나누기와 spec 작성 규칙

- **EventGraph**: 이벤트 체인마다 바깥 박스(파랑 event, `"names": [], "wrap": [안쪽 박스 번호...]`, `"pad": 56`) +
  안쪽 기능 블록 박스들. 체인이 작으면(노드 10개 안팎) 바깥 박스 하나만.
- **함수 그래프**: 함수 전체를 감싸는 헤더 박스 하나(`"all": true`, `"pad": 48~56`) — 제목은 `■ 함수(입력들) → 출력`,
  설명에 목적·입력·출력. 노드가 20개 넘거나 단계가 뚜렷하면 안쪽 블록을 추가.
- 블록 경계에 `--breaks "<블록 첫 노드>"`를 주고 layout을 다시 돌린다(그 노드 앞 가로 +320, 블록의 순수 노드가 블록 시작보다
  왼쪽으로 못 나감). 이름은 `rows` 출력의 `제목#번호` 그대로.
- spec의 `names`에는 **exec 노드만** 적으면 된다(`제목#번호` 형식 가능). 함께 배치된 순수 노드는 layout의 owner로 자동 포함.
  이벤트 노드 왼쪽에 순수 노드가 놓이는 경우가 많으니 이벤트 노드는 첫 블록에 넣는다(안 넣으면 "covers foreign node").
- 텍스트: `"■ 제목\n설명 1~2문장"`. 설명은 수치·태그·함수 이름을 그대로 쓴다. **덤프의 핀 값으로 사실을 확인하고 쓴다**
  (추측으로 "ASC가 없으면 false"라고 썼다가 실제 Return 값이 true여서 고쳤다). 긴 줄은 `\n`으로 직접 나눈다.
- 색: 이벤트/진입 `event`(0.1,0.3,0.7), 판단·흐름 `logic`(0.8,0.45,0.1), 피해·GAS 효과 `damage`(0.7,0.15,0.15),
  UI·피드백 `ui`(0.15,0.55,0.25), 설정·초기화 `setup`(0.35,0.35,0.35). 글자 18(기본).
- preview의 problems가 비어야 붙인다(ui-run도 problems가 있으면 멈춘다). 자주 나온 것과 해결:
  - `boxes i and j overlap`: 제목이 길어 박스가 넓어진 경우 → `"maxw": 0`(넓히지 않고 줄바꿈) 또는 문장 줄이기.
    블록 둘이 가로로 붙어 있으면 `--breaks`. 한 박스가 아래 행까지 넓게 먹으면 블록을 둘로 쪼갠다(예: 피니시 몽타주 / 피니시 종료).
  - `box i covers foreign node X`: X를 그 블록에 넣거나, 블록 경계를 X 앞으로 옮긴다.
  - `title bar of box i covers box j`: 바깥 박스 `pad`를 키운다(56 → 72).

spec 예 (`docs/comment-specs/AC_CombatComponent__ApplyHit.spec.json`):
```json
[
 {"text": "■ ApplyHit(Target, Coefficient, Knockback, Launch) → bGuarded\n대상 한 명에게 타격 하나를 적용한다: ...", "all": true, "color": "setup", "pad": 56},
 {"text": "■ 유효성 검사\n대상 ASC와 내 ASC가 모두 있어야 진행한다. 없으면 false 반환.", "names": ["IsValid#2", "IsValid#3", "ReturnNode#6", "ReturnNode#7"], "color": "logic"},
 {"text": "■ 가드 판정과 피해 적용 (GAS)\n...", "names": ["IsBlockedByGuard#22", "GetAttackPower#23", "AssignTagSetByCallerMagnitude#28", "ApplyGameplayEffectSpecToTarget#29"], "color": "damage"}
]
```
(layout: `--breaks "IsBlockedByGuard#22,Sequence#1"`)

## 3. ui-run이 하는 일 (수동으로 할 때도 이 순서)

1. `Snapshot {"ref":"w116","maxDepth":40}`에서 `tab "<그래프>"`가 있으면 Click, 없으면 My Blueprint의 `listitem "<그래프>"`를
   `Click {"doubleClick":true}`. **listitem ref는 스냅샷마다 번호가 바뀐다**(li36 → li51 → li66). 찾은 직후 바로 누른다.
2. 다시 스냅샷해서 그 패널의 워터마크 `text "BLUEPRINT"` ref(보이는 패널 것 하나만 나온다)를 앵커로 쓴다.
3. 보정: 클립보드에 (0,0) knot `K2Node_Knot_Cal` → ProgrammaticToolset 스크립트 한 번에
   `Click {"ref":<앵커>,"button":"right"}` → `PressKey Escape` → `PressKey Ctrl+V` → `get_node_infos` 위치 = L → `delete_node`.
4. 붙여넣기: 주석 T3D + 균형추 knot(좌표 = (N+1)·L − Σ주석 좌표) → 같은 스크립트 모양으로 `오른쪽 클릭 → Escape → Ctrl+V →
   Ctrl+C`(붙여넣은 것만 선택된 상태라 그대로 복사) → 균형추 위치 확인(±16, 실제로는 매번 정확히 일치) → `delete_node`.
   로컬에서 `Get-Clipboard`의 `EdGraphNode_Comment` 블록 NodePosX/Y/Width/Height를 spec과 비교.
5. 선택 해제: 더미 knot `K2Node_Knot_Desel`을 같은 방법으로 붙여넣고 `delete_node`(선택이 지워진 노드뿐이라 비게 된다).
6. `PressKey Home` → **1.5초 기다림**(전체 맞춤이 애니메이션이라 바로 찍으면 1:1 중간 화면이 찍힌다) → `Screenshot {"ref":""}`
   → base64를 PNG 파일로 디코드.

## 4. 함정 (파일럿에서 실제로 겪은 것)

- **워터마크 왼쪽 클릭 금지**: 그래프가 패널을 꽉 채우면 워터마크 밑에 노드가 있다. CanMove에서 왼쪽 클릭이 Return 노드의
  bool 체크박스를 눌러 기본값이 true → false로 바뀌었다(same-logic으로 발견, `set_pin_value`로 복구). 포커스는
  **오른쪽 클릭 + Escape**로 준다(컨텍스트 메뉴 창이 떴다 닫히고 포커스는 그래프 패널에 남는다. 이 상태에서 Ctrl+V가 된다).
  그래프 탭 클릭만으로는 포커스가 안 가서 Ctrl+V가 무시됐다.
- **Escape로는 선택이 안 풀린다.** 더미 knot 붙여넣기 → delete_node로 푼다.
- **Home 직후 스크린샷은 애니메이션 중간**: 1.5초 기다린다. 선택된 게 있으면 Home이 선택 영역에 맞춘다.
- **체인을 세로로만 쌓으면 Home이 최소 줌(-12)에서도 다 안 들어간다**(BasicAttack 106노드, 높이 ~8400). layout이 기본으로
  열을 나눈다(목표 높이 = 면적의 제곱근). 열 간격 800(주석 박스 여백 + 제목 폭 때문에 480은 박스가 겹쳤다).
- **축소 시 제목 말풍선**: 주석 박스는 축소하면 제목을 큰 말풍선으로 띄운다(`bCommentBubbleVisible`). 안쪽 박스까지 켜면
  말풍선끼리 겹쳐 읽을 수 없다. 도구가 최상위 박스만 켜고 안쪽 박스는 `bCommentBubbleVisible=False`로 붙인다.
  이미 붙인 주석은 ObjectTools `set_properties {"instance":{"refPath":"<그래프 ref>.EdGraphNode_Comment_X"},"values":"{\"bCommentBubbleVisible_InDetailsPanel\":false}"}`
  로 끌 수 있다(PostEditChange가 bCommentBubbleVisible도 맞춘다). 같은 방법으로 `commentColor`, `fontSize`도 바뀐다.
  텍스트·위치·크기는 못 바꾼다.
- **붙인 주석 되돌리기**: 붙여넣은 직후라면 그래프 포커스 상태에서 `PressKey Ctrl+Z` 한 번이 붙여넣기 전체(주석 + 균형추)를
  되돌린다(MCP delete_node는 되돌리기 기록에 따로 안 남았다). 노드 위치·연결·핀 값은 그대로였다(same-logic 확인).
  시간이 지난 뒤 주석 하나만 지우기: 읽을 수 있는 줌에서 스냅샷하면 주석 제목이 `text "■ ..."`로 나온다 → 그 ref를 왼쪽
  클릭(주석만 선택) → `PressKey Delete` → find_nodes로 노드 수가 그대로인지 확인. 그다음 고친 spec으로 다시 ui-run
  (주석 이름에 실행마다 다른 TAG가 붙어 이름이 겹치지 않는다).
- **Snapshot maxDepth**: 4~6이면 창 아래 이미지 3개만 나온다. 탭·버튼을 보려면 40.
- **노드 크기 추정**: 실측 대비 폭은 비슷, 핀 많은 노드 높이는 약 10% 크다(높이 = 64 + 26·행으로 올림). 변수 Get/Set은 따로
  작게 잡는다. arrange_nodes는 쓰지 않는다(높이를 몰라 겹치고 순수 노드를 흩뜨린다, 쿡북 참조).
- `find_nodes`/`get_node_infos`(덤프)는 그래프를 바꾸지 않는다. read_graph_dsl은 쓰지 않는다(Assign 노드 그래프에서 스트레이 이벤트 생성).
- 에셋 탭이 여러 개 열려 있으면(`GetOpenAssets`) 다른 에이전트가 연 것이다. 내가 연 것만 저장 뒤 `ui-close`로 닫는다.
  더티한 다른 에셋 탭은 건드리지 않는다.

## 5. 걸린 시간 (파일럿 측정)

| 대상 | 그래프 | 노드 | 시간 | 메모 |
| --- | --- | --- | --- | --- |
| BP_DungeonDoor | EventGraph 1 | 33 | 약 11분 | 도구를 만들며 처음 수동으로 진행 |
| AC_CombatComponent | 함수 10 + EventGraph | 209 | 약 20분 | 도구 개선 포함. ui-run 자동화 뒤 함수 9개 붙이기·스크린샷 71초(그래프당 약 8초) |
| GA_Player_BasicAttack | EventGraph 1 | 106 | 약 5분 | 덤프→spec→붙이기 2분 20초, 열 나누기 재배치(Ctrl+Z로 되돌린 뒤 다시 붙이기) 포함 |

도구 시간: 덤프 3초(BP 전체), layout·preview 1초 미만, apply 2초, ui-run 8~11초, 컴파일·저장·닫기 합쳐 5초.
나머지는 spec을 쓰는 시간이다: 헤더 박스만 쓰는 작은 함수 약 1분, 블록 4~6개짜리 큰 그래프 3~5분(preview 1~2회 반복 포함).
**BP 하나 평균 3~6분**으로 잡으면 남은 약 40개 BP는 3~4시간이다. 그래프 수가 많은 BP(컨트롤러, 방 로직)는 10분 이상.

## 추가: 위젯 BP와 작은 창 (두 번째 에디터 작업에서 확인)

- 위젯 블루프린트의 그래프 모드 워터마크는 `WIDGET BLUEPRINT`다. `graph_comments.py`의 `ui_find`/`open_graph`가 이제 둘 다 인식한다.
- 에디터 창이 작아 워터마크 밑에 노드가 깔리면 오른쪽 클릭이 노드로 가고 Ctrl+V가 무시된다(보정 knot이 안 생김). 이때는 `GC_ANCHOR=zoom`을 주면 그래프 패널 오른쪽 위의 `Zoom ...` 글자를 앵커로 쓴다(워터마크를 못 찾을 때도 자동으로 이쪽을 쓴다).
  ```
  GC_ANCHOR=zoom python Tools/graph_comments.py ui-run <spec> <graph_ref> --window <창 ref> --layout <layout> --shot <png> --port 8001 --fit-all
  ```
- 위젯 BP 에디터가 Designer 모드로 열리면 먼저 SlateInspector로 'Graph'를 눌러 그래프 모드로 바꾼다. 자세한 기록은 `docs/parallel/ui-cookbook.md`.
