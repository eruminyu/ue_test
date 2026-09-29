# UI 쿡북 (UMG 위젯 블루프린트, UE 5.8.2 MCP)

4단계 UI 위젯을 만들며 확인한 레시피와 함정이다. 표기: `UMG` = `UMGToolSet.UMGToolSet`, `BT` = BlueprintTools, `OT` = ObjectTools, `AT` = AssetTools. `OT set_properties`의 `values`는 JSON **문자열**이다(아래는 읽기 쉽게 객체로 적었다). 두 번째 에디터는 `python Tools/mcp_http.py --port 8001 call <toolset> <tool> '<json>'`으로 불렀다.

## 위젯 트리

- 생성: `UMG CreateWidgetBlueprint {"folderPath":"/Game/SoulCombat/UI","assetName":"WBP_AttributeBar","parentClass":{"refPath":"/Script/UMG.UserWidget"}}` → `{"refPath":"/Game/SoulCombat/UI/WBP_AttributeBar.WBP_AttributeBar"}`. 폴더가 없으면 만들어 준다. 새 WBP는 위젯 0개(루트 없음).
- 루트: `UMG AddWidget {"widgetBlueprint":W,"widgetClass":{"refPath":"/Script/UMG.SizeBox"},"widgetDisplayName":"RootSize"}` (parentWidget 생략 = 루트).
- 자식: `"parentWidget":{"refPath":"<WBP>:WidgetTree.<부모 이름>"}`. 반환값에 위젯 ref `<WBP>:WidgetTree.<이름>`과 슬롯 ref `<WBP>:WidgetTree.<부모>.<슬롯클래스>_<n>`(예: `RootSize.SizeBoxSlot_0`, `RootOverlay.OverlaySlot_1`, `TextRow.HorizontalBoxSlot_2`)가 온다. n은 부모 안의 추가 순서.
- `bIsVariable` 기본값: ProgressBar는 true, TextBlock/Border/SizeBox/Overlay/HorizontalBox/Spacer는 false. 그래프에서 쓸 위젯은 `UMG ToggleWidgetAsVariable {"widgetBlueprint":W,"widget":{"refPath":"<WBP>:WidgetTree.LabelText"},"bIsVariable":true}` → `null`.
- 위젯 변수 노드 ID: `Variables|<WBP 이름>|Get<위젯 이름>` (예: `Variables|WBP_AttributeBar|GetBar`).

## 위젯·슬롯 프로퍼티 (OT, 실제 이름)

- SizeBox: `widthOverride`, `heightOverride`, `bOverride_WidthOverride`, `bOverride_HeightOverride` → `{"widthOverride":300,"heightOverride":22,"bOverride_WidthOverride":true,"bOverride_HeightOverride":true}`.
- 모든 위젯: `visibility`(`Visible`/`Collapsed`/`Hidden`/`HitTestInvisible`/`SelfHitTestInvisible`), `renderOpacity`.
- SizeBoxSlot / OverlaySlot: `padding{left,top,right,bottom}`, `horizontalAlignment`(`HAlign_Fill/Left/Center/Right`), `verticalAlignment`(`VAlign_*`). **OverlaySlot 기본값은 Left/Top**(SizeBoxSlot은 Fill/Fill) → 배경 바는 `{"horizontalAlignment":"HAlign_Fill","verticalAlignment":"VAlign_Fill"}`로 바꿔야 한다.
- HorizontalBoxSlot / VerticalBoxSlot: `size{value,sizeRule}`(`Automatic`/`Fill`), `padding`, 정렬. Spacer 채우기: `{"size":{"value":1,"sizeRule":"Fill"}}`.
- TextBlock: `text`, `colorAndOpacity{specifiedColor{r,g,b,a},colorUseRule}`, `font{fontObject,typefaceFontName,size,...}`(기본 Roboto Bold 24), `shadowOffset{x,y}`(기본 1,1), `shadowColorAndOpacity`(기본 a 0 = 그림자 없음), `justification`(`Left/Center/Right`), `margin`.
  - **부분 구조체는 병합된다**: `{"font":{"size":12}}`만 넘겨도 fontObject·typeface가 유지됐다(get_properties로 확인).
  - 그림자 켜기: `{"shadowColorAndOpacity":{"r":0,"g":0,"b":0,"a":0.7}}`.
- ProgressBar: `percent`, `barFillType`(`LeftToRight`, ..., `BottomToTop`), `barFillStyle`, `fillColorAndOpacity`, `widgetStyle{backgroundImage,fillImage,marqueeImage}`(각각 SlateBrush, `tintColor{specifiedColor,colorUseRule}`). 배경 어둡게: `{"widgetStyle":{"backgroundImage":{"tintColor":{"specifiedColor":{"r":0.02,"g":0.02,"b":0.02,"a":0.75},"colorUseRule":"UseColor_Specified"}}}}` (나머지 브러시 필드 유지).
- 확인: `UMG GetWidgetDescription {"widgetBlueprint":W}` → 기본값과 다른 프로퍼티만 한 줄씩 나온다.

## 그래프 (위젯 BP)

- 새 WBP EventGraph에는 `EventPreConstruct`, `EventConstruct`, `EventTick` 노드가 이미 있다. DSL 머리: `(event UserInterface|EventConstruct ...)`, `(event UserInterface|EventTick (MyGeometry InDeltaTime) ...)`. 쓰지 않는 PreConstruct는 `delete_node`.
- 노드 ID (WBP 그래프에서 find_node_types로 확인):
  - `Progress|SetPercent :self bar :InPercent x`, `Progress|SetFillColorandOpacity :self bar :InColor c` (함수 호출. `Class|ProgressBar|SetPercent`는 프로퍼티 Set 노드라 출력 `Output_Get`이 붙는다)
  - `Widget|SetText(Text) :self textBlock :InText t`, `Widget|SetVisibility :self w :InVisibility "Collapsed"`(enum 문자열)
  - `Ability|GetAbilitySystemComponent :Actor a` (AbilitySystemBlueprintLibrary), `Ability|Attribute|GetFloatAttributefromAbilitySystemComponent :AbilitySystem asc :Attribute attr` → `(bind (found value) ...)`
  - `Math|Float|SafeDivide a b`(b=0이면 0), `Math|Float|Round`(→ int), `Math|Float|Max(Float)`, `Utilities|Time|GetGameTimeinSeconds`
  - 문자열: `Utilities|String|ToString(Integer)`, `Utilities|String|ToString(Text)`, `Utilities|String|Append a b`, `Utilities|Text|ToText(String)`, `Utilities|Text|ToText(Float) :MinimumFractionalDigits 1 :MaximumFractionalDigits 1`
- 멤버 변수 노드 ID는 카테고리를 따른다: `Variables|AttributeBar|Config|GetAttribute`, `Variables|AttributeBar|State|GetBoundASC`. bool `bShowNumbers` → `GetShowNumbers`/`SetShowNumbers`(읽을 때는 `|GetbShowNumbers`로 나온다).
- 자기 함수 호출 `(CallFunction|Refresh)`는 `read_graph_dsl`에서 `(ControlActor|Refresh)`로 읽힌다. 실제 노드는 self 대상 `|Refresh`다(`get_node_infos`로 확인). 읽은 DSL을 그대로 다시 쓰지 않는다.
- **함정: FormatText 인자 핀**: `(Utilities|Text|FormatText :Format "{0} / {1}" :0 a :1 b)` → `Unknown input pin "0" on Utilities|Text|FormatText. Input pins: ['Format']` (노드는 남지 않았다). 형식 문자열로 생기는 인자 핀은 DSL로 못 만든다. 대신 `(Utilities|Text|ToText(String) (Utilities|String|Append (Utilities|String|Append curStr " / ") maxStr))`.
- 변수 기본값(CDO): `compile_blueprint` 뒤 `OT set_properties {"instance":W,"values":...}`. GameplayAttribute: `{"Attribute":{"attributeName":"Health","attribute":"/Script/SoulCombat.SCAttributeSet:Health","attributeOwner":{"refPath":"/Script/SoulCombat.SCAttributeSet"}}}`. 다시 컴파일해도 값이 유지됐다.
- 컴파일: `UMG CompileWidgetBlueprint` → `true`, 그다음 `BT compile_blueprint {"warnings_as_errors":true}` → `null`(경고 없음). `LogsToolset GetLogEntries {"pattern":"WBP_X.*(Warning|Error)","category":""}` → `[]`.
- 정리: 함수 그래프는 `find_nodes` 전체로 `arrange_nodes`, EventGraph는 `find_nodes(entry_points_only=true)`의 이벤트마다 `get_connected_subgraph` → `arrange_nodes`.

## 스킬 슬롯 쿨타임 노드 (WBP_SkillSlot)

- `GameplayEffects|GetActiveEffectswithAllTags :self asc :Tags (GameplayTags|MakeGameplayTagContainerfromTag tag)` — **실행 노드**(exec 있음). 출력 `ReturnValue`(ActiveGameplayEffectHandle 배열).
- `Ability|GameplayEffect|GetActiveGameplayEffectRemainingDuration :ActiveHandle h`, `...TotalDuration :ActiveHandle h` — 둘 다 실행 노드, float(single) 반환.
- `(bind h (Utilities|Array|Get(acopy) effects 0))` — 인덱스 0은 핀 기본값으로 들어갔다(리터럴 노드 없음). 와일드카드 출력이 핸들 타입으로 바로 잡혔다.
- Border 색: `Appearance|SetBrushColor :self border :InBrushColor c`. Border 프로퍼티 이름은 `brushColor`, `background`(SlateBrush), `padding`(기본 4,2,4,2), `contentColorAndOpacity`.
- 두 갈래 처리(쿨타임 + 자원 부족)는 `(Utilities|FlowControl|Sequence (:then_0 ...) (:then_1 ...))`로 나눴다. then_0 안의 `(if ... (else ...))` 뒤에 문장을 두지 않기 위해서다.
- `(select (and (> cost 0.0) (< cur cost)) NoCostColor NormalColor)` → Select 노드(LinearColor)로 잘 연결됐다.
- `read_graph_dsl`은 Sequence를 생략하고, 반복 사용된 순수 노드 결과를 함수 맨 앞으로 끌어올려 `_output`처럼 보여 준다(검토용). 실제 연결은 `get_node_infos`의 연결 수로 확인했다.

## 위젯 안에 다른 WBP 넣기 (WBP_BossHealthBar)

- `UMG AddWidget {"widgetBlueprint":W,"widgetClass":{"refPath":"/Game/SoulCombat/UI/WBP_AttributeBar.WBP_AttributeBar_C"},"widgetDisplayName":"HealthBar","parentWidget":{"refPath":"<WBP>:WidgetTree.HealthBarSize"}}` → `bIsVariable` 기본 true.
- **인스턴스별 값 설정이 된다**: `OT list_properties <WBP>:WidgetTree.HealthBar`에 자식 WBP의 인스턴스 편집 변수(`attribute`, `maxAttribute`, `label`, `fillColor`, `bShowNumbers`)가 보이고, `OT set_properties {"FillColor":{"r":0.45,"g":0.03,"b":0.03,"a":1},"Label":""}` → true, 컴파일 후에도 유지(`GetWidgetDescription`에 `FillColor:(R=0.45...)`). → WBP_PlayerHUD에서 바·슬롯 설정을 디자이너 값으로 넣을 수 있다(Construct의 Setup 호출은 선택).
- 자식 WBP 크기 바꾸기: 자식 루트 SizeBox의 override는 원하는 크기(desired size)만 정한다. 바깥에 SizeBox(800×24)를 두고 그 안에 넣으면 그 크기로 그려진다.
- 자식 WBP 함수 호출 노드 ID: `Class|WBPAttributeBar|Setup`, `Class|WBPAttributeBar|BindtoActor` (WBP 이름의 `_`가 빠진다). `:self hb`로 대상 지정.
- GameplayAttribute 핀 리터럴이 DSL에서 그대로 들어간다(확인): `:InAttribute "(AttributeName=\"Health\",Attribute=/Script/SoulCombat.SCAttributeSet:Health,AttributeOwner=/Script/CoreUObject.Class'/Script/SoulCombat.SCAttributeSet')"`. Text 빈 문자열 `:InLabel ""`도 된다.
- 자기 자신 표시: `(Widget|SetVisibility :self self :InVisibility "HitTestInvisible")`.
- **함정**: TextBlock을 `ToggleWidgetAsVariable`로 변수화하지 않으면 DSL이 `AssertionError: The node could not be created / Variables|WBP_BossHealthBar|GetBossNameText does not exist`로 실패한다(노드는 남지 않음). 변수화 후 `CompileWidgetBlueprint`를 한 번 해야 노드 ID가 생긴다.
- 그래프 로직이 없는 이벤트(PreConstruct/Construct/Tick 기본 노드)는 연결 0인 채로 남으므로 `delete_node`로 지운다.
- 에디터가 Text를 `NSLOCTEXT("", "<키>", "보스")`로 저장한다(한글 기본값 정상).

## 위젯 자체 기본 숨김, 지연 숨김 (WBP_RoomBanner)

- 위젯 자신의 기본 가시성: `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/UI/WBP_RoomBanner.WBP_RoomBanner"},"values":{"visibility":"Collapsed"}}` → true. UserWidget CDO 기본값은 `SelfHitTestInvisible`. 컴파일·저장 뒤에도 `Collapsed`로 읽혔다.
- 함수 안에서는 지연 노드를 못 쓴다 → 커스텀 이벤트 `BT add_event {"blueprint":W,"event_name":"HideLater"}` → 함수에서 `(CallFunction|HideLater)`로 부르고, 이벤트 본문 `(event Custom|HideLater (Utilities|FlowControl|RetriggerableDelay :Duration (Variables|Banner|State|GetPendingDuration)) (Widget|SetVisibility :self self :InVisibility "Collapsed"))`.
- RetriggerableDelay는 다시 호출되면 남은 시간을 처음부터 센다 → 새 배너가 이전 배너의 숨김 타이머를 덮는다(BannerId 비교 불필요).

## 남은 시간 문자열 (WBP_EventTimer)

- `(bind remaining (Math|Float|Max(Float) :A 0.0 :B (- endTime (Utilities|Time|GetGameTimeinSeconds))))` → `ToText(Float) :MinimumFractionalDigits 1 :MaximumFractionalDigits 1` → `ToString(Text)` → `Append "남은 시간 "` … `"초"` → `ToText(String)`. DSL 한글 문자열 리터럴이 그대로 들어간다(인자 파일은 UTF-8 JSON).
- bool 멤버 `bRunning`(카테고리 EventTimer|State) → DSL `Variables|EventTimer|State|GetRunning`/`SetRunning`(b 제거).
- 도구 쪽 주의: Windows 기본 코드페이지(cp949)에서 한글이 든 결과 파일을 `open()`하면 UnicodeDecodeError → 항상 `encoding='utf-8'`, 클라이언트 실행 시 `PYTHONIOENCODING=utf-8`.

## Border 여백 (WBP_InteractPrompt)

- Border의 `padding` 프로퍼티와 슬롯 `<WBP>:WidgetTree.RootBorder.BorderSlot_0`의 `padding`은 따로 저장된다. Border에 `{"padding":{...}}`를 넣어도 BorderSlot은 기본값(4,2,4,2)으로 남았다 → **BorderSlot_0에도 같은 값을 넣는다**(`GetWidgetDescription`에서 자식 줄의 `slot:(Padding:...)`로 확인).
- Border 배경색은 `brushColor`(기본 흰색 a1). 어두운 반투명: `{"brushColor":{"r":0.02,"g":0.02,"b":0.03,"a":0.7}}`.

## 마무리 점검

- 저장 후에도 `is_dirty`가 다시 true가 되는 경우가 있었다(WBP_RoomBanner, 원인 불명). 끝에 폴더 전체를 `find_assets` → `is_dirty`로 한 번 더 돌리고, dirty면 `compile_blueprint` → `save_assets`(경로 명시) → `is_dirty` false 확인.
