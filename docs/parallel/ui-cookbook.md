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

## 버튼 클릭 이벤트 (WBP_DungeonEntry, WBP_DungeonClear)

- **가장 간단한 방법(확인)**: 버튼은 `AddWidget` 때 `bIsVariable` 기본 true다. `UMG BindToEventProperty {"widgetBlueprint":W,"eventName":"OnClicked","propertyName":"EnterButton","propertyClass":{"refPath":"/Script/UMG.Button"}}` → `true`. EventGraph에 `K2Node_ComponentBoundEvent_0`(type_id `AddEvent|OnClicked(EnterButton)`, 연결 없음)이 생긴다.
- 본문은 DSL 머리 `(event OnClicked(EnterButton) (Default|CallOnConfirmed))`로 쓴다 → 기존 바운드 이벤트 노드에 그대로 이어진다(새 이벤트 안 생김). `read_graph_dsl`도 같은 머리로 읽힌다. Event Construct에서 `AssignOnClicked`를 쓸 필요가 없었다.
- 디스패처 방송: `add_event_dispatcher` → 컴파일 → `(Default|CallOnConfirmed)` (파라미터 없음).
- Button 프로퍼티: `widgetStyle{normal,hovered,pressed,disabled(SlateBrush),normalForeground...,normalPadding,pressedPadding}`, `colorAndOpacity`, `backgroundColor`, `clickMethod`, `isFocusable`. 기본 normal 틴트는 회색(0.5) 둥근 상자라 글자는 어두운색(0.05)이 잘 보인다. ButtonSlot 기본값: padding 4/2/4/2, 정렬 Center/Center.

## 전체 화면 반투명 창

- 루트 Border(`brushColor` 검정 a0.6, `padding` 0) + `BorderSlot_0`의 `horizontalAlignment:"HAlign_Center"`, `verticalAlignment:"VAlign_Center"`, `padding` 0 → 내용이 화면 가운데. Border 자체의 `horizontalAlignment`/`verticalAlignment`도 같이 넣었다(슬롯과 별도 저장).
- 최소 너비: SizeBox `{"minDesiredWidth":600,"bOverride_MinDesiredWidth":true}`.
- TextBlock 자동 줄바꿈: `{"autoWrapText":true}`(그 밖에 `wrapTextAt`, `wrappingPolicy`, `textOverflowPolicy`).

## 카운트다운 (WBP_DungeonClear)

- 노드 ID: `Utilities|FlowControl|Delay :Duration 1.0`(EventGraph에서만), 정수 최대 `Math|Integer|Max(Integer) :A 0 :B x`(`Math|Integer|Max`는 `does not exist`).
- 커스텀 이벤트가 자기 자신을 다시 부르는 반복(`(event Custom|CountdownStep (Utilities|FlowControl|Delay :Duration 1.0) ... (CallFunction|CountdownStep))`)이 DSL로 만들어지고 경고 없이 컴파일된다. 함수(Setup)에서도 `(CallFunction|CountdownStep)`으로 시작한다.
- **함정: 순수 노드 재평가**. `(bind remaining (- (GetCountdown) 1))` 후 `(SetCountdown remaining)`과 `(if (<= remaining 0) ...)`에 같이 쓰면, 비교 쪽이 Set 뒤에 순수 노드를 다시 계산해 `Countdown-2`를 비교한다(한 칸 일찍 끝남). `bind`는 노드를 하나로 묶을 뿐 값을 저장하지 않는다. Set 뒤에는 변수를 다시 읽는다: `(if (<= (Variables|DungeonClear|State|GetCountdown) 0) ...)`.
- 한 번만 방송: `(fn RequestReturn () (if (not (Variables|DungeonClear|State|GetRequested)) (Variables|DungeonClear|State|SetRequested true) (Default|CallOnReturnRequested)))`. bool `bRequested`는 `GetRequested`/`SetRequested`로 쓰고, 읽으면 `|GetbRequested`로 나온다.

## HUD 캔버스 (WBP_PlayerHUD)

- CanvasPanelSlot(`<WBP>:WidgetTree.RootCanvas.CanvasPanelSlot_<n>`) 프로퍼티: `layoutData{offsets{left,top,right,bottom},anchors{minimum{x,y},maximum{x,y}},alignment{x,y}}`, `bAutoSize`, `zOrder`. 점 앵커일 때 offsets의 left/top = 위치, right/bottom = 크기. 기본값 `offsets(0,0,100,30)`, 앵커 (0,0).
  - 왼쪽 아래: `{"layoutData":{"offsets":{"left":40,"top":-40,"right":360,"bottom":100},"anchors":{"minimum":{"x":0,"y":1},"maximum":{"x":0,"y":1}},"alignment":{"x":0,"y":1}}}`
  - 내용 크기 따르기: `"bAutoSize":true`(offsets의 right/bottom 무시).
- 중첩 WBP 추가: `AddWidget`의 `widgetClass`에 `/Game/SoulCombat/UI/WBP_SkillSlot.WBP_SkillSlot_C` → `bIsVariable` 기본 true. CDO visibility가 Collapsed인 WBP(RoomBanner, EventTimer)는 인스턴스도 Collapsed로 시작한다(다른 것은 SelfHitTestInvisible).
- **중첩 위젯 인스턴스 값으로 설정(확인)**: `OT set_properties <WBP>:WidgetTree.SlotDash {"keyLabel":"Shift","skillName":"대시","cooldownTag":{"tagName":"Cooldown.Dash"},"costAttribute":{"attributeName":"Stamina","attribute":"/Script/SoulCombat.SCAttributeSet:Stamina","attributeOwner":{"refPath":"/Script/SoulCombat.SCAttributeSet"}},"cost":25}` → true. 컴파일·저장 뒤 is_dirty false이고 `GetWidgetDescription`에 남는다. 단 GetWidgetDescription은 **클래스 기본값과 다른 값만** 보여 주므로(HPBar는 Label만, SlotSkill1은 SkillName·Cost만) 전체 확인은 `OT get_properties`로 한다. 자식 Construct가 ApplyAppearance로 값을 적용하므로 HUD Construct의 Setup 호출은 생략했다.
- 속성 이름 확인: `GASToolsets.AttributeSetToolset ListAttributes {"className":"SCAttributeSet"}`(U 접두사 붙이면 `not found`).
- 자식 WBP 함수 노드 ID(밑줄 빠짐): `Class|WBPRoomBanner|ShowBanner :self rb :Title :Subtitle :Duration`, `Class|WBPBossHealthBar|ShowFor :Boss :BossName`, `Class|WBPBossHealthBar|HideBar`, `Class|WBPEventTimer|StartTimer :Objective :Seconds`, `Class|WBPEventTimer|SetProgress :Progress`, `Class|WBPEventTimer|StopTimer`, `Class|WBPInteractPrompt|SetPrompt :Key :Action`, `Class|WBPSkillSlot|BindtoActor :Actor`. HUD 위젯 변수 게터: `Variables|WBP_PlayerHUD|GetHPBar`.
- **함정**: `read_graph_dsl`이 자식 함수 호출 이름을 틀리게 읽는다. 슬롯의 BindtoActor가 `Class|WBPAttributeBar|BindtoActor`로, SetPrompt가 `Class|AssetExportTask|SetPrompt`로 나왔다. 실제 대상은 `get_node_infos`의 self 핀 타입(`WBP Skill Slot Object Reference`, `WBP Interact Prompt Object Reference`)으로 확인했다.
- 오브젝트 파라미터: `add_object_function_param {"graph":G,"param_name":"Pawn","object_class":{"refPath":"/Script/Engine.Pawn"},"input_param":true}`. Pawn을 자식의 `Actor` 핀에 바로 넘겨도 된다.

## 배치와 저장 점검 메모

- 기본 이벤트를 지운 EventGraph에 `arrange_nodes`를 돌리면 체인이 y 약 1100~1950으로 밀려났다(WBP_DungeonEntry, WBP_DungeonClear). 작은 그래프는 `set_node_position`으로 직접 놓았다: 실행 노드는 y 0 한 줄, x 300 간격, 순수 노드는 소비 노드 아래(y 150~280). 함수 그래프도 arrange 결과에서 FunctionEntry가 오른쪽(x 1350)으로 가는 경우가 있어 같은 방식으로 고쳤다.
- `AT save_assets` 인자는 `{"asset_paths":["/Game/SoulCombat/UI/WBP_X"]}`(문자열 패키지 경로). `{"assets":[ref]}`는 스키마 오류.
- 폴더 전체 is_dirty 점검 스크립트에서 python `print`로 만든 목록에 `\r`이 붙어 인자 JSON이 깨졌다(`Invalid control character`). `tr -d '\r'`로 지운 뒤 돌린다.

## 검증 뒤 수정 (색 보정, 저장 상태)

- **함정: 자식 WBP 변수 기본값(CDO)을 바꿔도 이미 배치된 중첩 인스턴스에는 에디터 안에서 퍼지지 않았다.** `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/UI/WBP_SkillSlot.WBP_SkillSlot"},"values":"{\"NoCostColor\":{\"r\":0.01,\"g\":0.01,\"b\":0.012,\"a\":0.95}}"}` → true, WBP_SkillSlot 컴파일 뒤에도 `OT get_properties <HUD>:WidgetTree.SlotDash ["noCostColor"]`는 옛 값 (0.45, 0.05, 0.05, 0.8)이었다. 인스턴스마다 같은 값을 `set_properties`로 넣고(SlotDash, SlotSkill1~3) HUD를 컴파일한 뒤 다시 읽어 확인했다. CDO 변수 이름은 `NoCostColor`, 인스턴스 쪽 이름은 `noCostColor`로 읽혔다(둘 다 get_properties에 통함).
- 중첩 위젯 한 개의 값만 고치기: `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/UI/WBP_PlayerHUD.WBP_PlayerHUD:WidgetTree.StaminaBar"},"values":"{\"fillColor\":{\"r\":1.0,\"g\":0.85,\"b\":0.1,\"a\":1}}"}` → true, HUD 컴파일 뒤 유지.
- `read_graph_dsl`과 `CompileWidgetBlueprint`/`compile_blueprint`만 해도 WBP가 dirty가 된다(읽기 전용 검증 뒤 9개 모두 is_dirty true). 검증 뒤에는 `UMG CompileWidgetBlueprint` → `BT compile_blueprint {"warnings_as_errors":true}` → `AT save_assets {"asset_paths":[9개 경로]}` → `AT is_dirty` false 확인까지 한다.
- 로그 툴셋 전체 이름은 `EditorToolset.LogsToolset`이다(`LogsToolset`만 쓰면 `Toolset 'LogsToolset' not found`). `GetLogEntries {"pattern":"WBP_.*(Warning|Error)","category":"","maxEntries":50}` → `[]`.

## 5단계 몬스터 1/2 (에디터 B): 적 BP, AI 컨트롤러, 몬스터 GA

같은 병렬 워크플로의 기록 위치라서 UI 문서에 이어 적는다. 표기: `AcT` = `editor_toolset.toolsets.actor.ActorTools`, `APP` = `EditorToolset.EditorAppToolset`, `SI` = `SlateInspectorToolset.SlateInspectorToolset`, `PT` = ProgrammaticToolset.

### 몬스터 GA (GA_ActionBase 자식, 그래프 없음)

- `BT create {"folder_path":"/Game/SoulCombat/GAS/Abilities","asset_name":"GA_Enemy_Melee","asset_type":{"refPath":"/Game/SoulCombat/GAS/Abilities/GA_ActionBase.GA_ActionBase_C"}}` → `compile_blueprint` → EventGraph의 기본 `K2Node_Event_0`(ActivateAbility), `K2Node_CallParentFunction_0`, `K2Node_Event_1`(OnEndAbility)을 `delete_node` → 부모 흐름만 돈다.
- CDO 한 번에: `OT set_properties` values `{"abilityTags":{"gameplayTags":[{"tagName":"Ability.Enemy.Attack.Melee"}]},"activationBlockedTags":{"gameplayTags":[{"tagName":"State.Dead"},{"tagName":"State.HitStun"}]},"activationOwnedTags":{"gameplayTags":[{"tagName":"State.Attacking"}]},"cooldownGameplayEffectClass":"/Game/SoulCombat/GAS/Effects/GE_Cooldown_Enemy_Melee.GE_Cooldown_Enemy_Melee_C","Montage":"/Game/Variant_Combat/Anims/AM_ComboAttack.AM_ComboAttack","StartSection":"Melee01","PlayRate":0.8,"HitTime":0.45,"Coefficient":1.0,"Radius":130,"ForwardOffset":110,"Knockback":300,"Launch":0,"bFaceInputOnStart":false}` → true.
- 손자 GA(GA_Enemy_Melee_Boss, 부모 `GA_Enemy_Melee_C`)는 바뀌는 값만 넣으면 태그, 몽타주, bFaceInputOnStart가 부모 CDO에서 상속된다(get_properties로 확인).

### 상속 컴포넌트 값: 손자 BP는 에디터를 먼저 연다 (함정)

- `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/Characters/Enemies/BP_Enemy_Grunt.BP_Enemy_Grunt_C:Combat_GEN_VARIABLE"}, ...}` → `Parameter error: ... is not valid Object for property 'instance'`. 조부모(BP_CombatCharacterBase)의 Combat도, 부모(BP_EnemyBase)의 OverheadBar도 같은 에러였다. `get_components(자식 CDO)`는 부모 경로를 돌려준다(거기 쓰면 모든 자식이 바뀐다).
- **해결**: `APP OpenEditorForAsset {"assetPath":"/Game/SoulCombat/Characters/Enemies/BP_Enemy_Grunt"}`를 한 번 부르면 같은 `_C:Combat_GEN_VARIABLE` 경로가 해석되고 set/get이 모두 된다(에디터가 상속 컴포넌트 템플릿을 만든다). 부모 BP_EnemyBase 값(AbilitySet None, bDestroyOnDeath false)은 그대로이고, 컴파일·저장 뒤에도 자식 값이 유지됐다.
- 새 자식 BP 순서: `BT create` → `compile_blueprint` → `OpenEditorForAsset` → 기본 이벤트 4개(BeginPlay+Parent, ActorBeginOverlap, Tick) `delete_node` → CDO / `Default__X_C:CharacterMesh0` / `Default__X_C:CharMoveComp` / `X_C:Combat_GEN_VARIABLE`에 set_properties. 삭제와 설정은 PT 스크립트 하나로 돌렸다.
- 클래스 프로퍼티 비우기: `{"AIControllerClass":null}` → get은 `"None"`. `AutoPossessAI`는 `"Disabled"`, `"PlacedInWorldOrSpawned"` 문자열. 스켈레탈 메시 없애기: `CharacterMesh0`에 `{"SkeletalMeshAsset":null,"AnimClass":null}`.

### DSL이 부모 호출 노드를 지운다 (함정)

- 자식 BP의 기본 BeginPlay에는 `Parent: BeginPlay`(`K2Node_CallParentFunction_0`)가 붙어 있다. `break_pins`로 연결을 먼저 끊어 두어도 `write_graph_dsl`에 `(event EventBeginPlay ...)`를 쓰면 **부모 호출 노드가 삭제됐다**. DSL로는 다시 만들 수 없다.
- 복구(사람 개입 없음, SlateInspector): `compile_blueprint` → `APP OpenEditorForAsset` → `SI Windows {"action":"select","index":<BP 창>}` → `SI Click` EventGraph 탭 → 이벤트 노드를 빈 곳으로 옮긴다 `BT set_node_position {"node":<BeginPlay>,"pos":{"x":0,"y":-600}}`(다른 노드와 겹치면 우클릭이 다른 노드에 간다) → `SI Snapshot {"ref":<창>,"maxDepth":40}`에서 그 좌표의 제목 줄 `image`(크기 169x24)를 찾아 `SI Click {"ref":"i94","button":"right"}` → 새 창을 `Snapshot` → `text "Add Call to Parent Function"` Click → `K2Node_CallParentFunction_1`(type `|Parent:BeginPlay`)이 연결 없이 생긴다 → `break_pins`(BeginPlay then → 첫 DSL 노드), `connect_pins`(BeginPlay then index 1 → 부모 execute index 0), `connect_pins`(부모 then index 0 → 첫 DSL 노드 execute index 0).
- 화면 좌표 찾기: 그래프 줌 0.25에서 화면 x = 642 + 0.25 × 노드 x, y = 539 + 0.25 × 노드 y였다(같은 열 노드들의 위치로 역산).

### 디스패처 바인딩 이름 충돌

- 부모 BP(BP_CombatCharacterBase)에 이미 `OnDied_Event`가 있으면 자식의 `(Default|AssignOnDied :self (Variables|Default|GetCombat))`는 `OnDied_Event_0`을 만든다. 본문 DSL 머리는 `(event Custom|OnDied_Event_0 (DeadActor) ...)`, OnRespawned는 `(event Custom|OnRespawned_Event_0 (Actor) ...)`. 이 두 번째 write에서는 스트레이 이벤트가 생기지 않았다.

### 출력 없는 함수의 루프 안 return (함정)

- 출력 파라미터가 없는 함수에서 `(return)`은 Return 노드를 만들지 않고 그 실행 줄만 끝낸다. 분기 뒤라면 문제없지만 **ForLoop 본문 안에서는 다음 반복이 계속 돈다**(Think에서 공격 성공 뒤에도 루프와 Completed가 이어져 bChasing을 덮어쓴다).
- 해결: `BT create_node {"graph":<Think>,"type_id":"|AddReturnNode...","pos":{"x":14560,"y":600}}` → `K2Node_FunctionResult_0` → `connect_pins`(루프 안 마지막 노드 then → Return execute index 0).

### AI 컨트롤러 (AIController 부모)

- 새 AIController BP의 EventGraph에는 BeginPlay, Tick만 있다. OnPossess: `BT add_event {"blueprint":BP,"event_name":"ReceivePossess"}` → type `AddEvent|EventOnPossess`, 출력 `PossessedPawn`. DSL 머리 `(event EventOnPossess (PossessedPawn) ...)`.
- 함수 이름 타이머(델리게이트 핀 문제 회피): `(Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "Think" :Time (Variables|AI|GetThinkInterval) :bLooping true)`.
- 노드 ID: `Utilities|Casting|CastToBP_EnemyBase`, `Utilities|Casting|CastToBP_CombatCharacterBase`, `Class|BPEnemyBase|GetAttackTags`/`GetAttackRanges`/`GetAttackMinRanges`/`GetAggroRange`/`GetActive`(bool은 b 제거), `Class|BPCombatCharacterBase|GetCombat :self enemy`(BP_EnemyBase 참조를 바로 연결한다. read_graph_dsl은 `Class|GASCBase|GetCombat`로 틀리게 읽는다), `Class|ACCombatComponent|PressInput :self c :InputTag t`(출력 `bActivated`), `Class|ACCombatComponent|CanMove`(실행 노드, 출력 `bCanMove`), `Class|ACCombatComponent|GetIsDead`, `Class|ACCombatComponent|GetASC`, `GameplayTags|HasMatchingGameplayTag :self asc :TagToCheck "(TagName=\"State.HitStun\")"`(ASC를 인터페이스 핀에 바로 연결), `Game|GetPlayerPawn :PlayerIndex 0`, `Transformation|GetDistanceTo :self a :OtherActor b`, `Math|Rotator|FindLookatRotation :Start :Target`, `Transformation|SetActorRotation :self a :NewRotation (Math|Rotator|MakeRotator :Yaw (.yaw r))`, `Pawn|Input|AddMovementInput :self enemy :WorldDirection v :ScaleValue 1.0`, `Utilities|Array|Length`, `Utilities|Array|LastIndex`, `Utilities|Array|Get(acopy)`.
- `(for i (range (Utilities|Array|Length tags)) ...)` → ForLoop LastIndex = Length - 1(int-int 노드). 루프 뒤 문장은 Completed에 붙는다.

### WidgetComponent (머리 위 바)

- `AcT add_component {"owner":<BP>,"component_type":{"refPath":"/Script/UMG.WidgetComponent"},"name":"OverheadBar"}` → 캡슐 아래에 붙는다. 프로퍼티(OT, 소문자 시작): `{"space":"Screen","widgetClass":"/Game/SoulCombat/UI/WBP_AttributeBar.WBP_AttributeBar_C","drawSize":{"x":120,"y":12},"relativeLocation":{"x":0,"y":0,"z":120},"BodyInstance":{"collisionProfileName":"NoCollision","collisionEnabled":"NoCollision"},"bGenerateOverlapEvents":false,"CanCharacterStepUpOn":"ECB_No"}` → true. 기본값은 World, 500×500, 프로필 `UI`(Pawn 겹침)였다.
- 그래프: `(bind bar (Utilities|Casting|CastToWBP_AttributeBar :Object (UserInterface|GetUserWidgetObject :self (Variables|Default|GetOverheadBar))) (:then (Class|WBPAttributeBar|Setup :self bar :InAttribute "<Health 리터럴>" :InMaxAttribute "<MaxHealth 리터럴>" :InLabel "" :InFillColor "(R=0.450000,G=0.030000,B=0.030000,A=1.000000)" :bInShowNumbers false) (Class|WBPAttributeBar|BindtoActor :self bar :Actor self)) (:CastFailed))`. 켜고 끄기는 `Rendering|SetVisibility :self <OverheadBar> :bNewVisibility b`(SceneComponent 버전).
- 휴면 숨김은 `Rendering|SetActorHiddenInGame`만으로는 Screen 공간 위젯이 남을 수 있어서 OverheadBar 가시성도 같이 끈다.

### 스태틱 메시 추가 컴포넌트 (BP_SealCrystal)

- `AcT add_component`(StaticMeshComponent `CrystalMesh`) → 캡슐 아래. SM_ChamferCube 바운드는 (-50..50)³(피벗 중심)이라 위치 (0,0,0)이면 캡슐 중심이다. `{"StaticMesh":"/Game/LevelPrototyping/Meshes/SM_ChamferCube.SM_ChamferCube","RelativeLocation":{"x":0,"y":0,"z":0},"RelativeRotation":{"pitch":0,"yaw":45,"roll":0},"RelativeScale3D":{"x":0.8,"y":0.8,"z":1.6},"OverrideMaterials":["/Game/SoulCombat/Materials/MI_SC_Crystal.MI_SC_Crystal"],"BodyInstance":{"collisionProfileName":"NoCollision","collisionEnabled":"NoCollision"}}` → 캡슐(반높이 88)이 몸통 역할을 유지한다.

### 도구 쪽 주의

- 한글 값: 결과를 콘솔에 print하면 깨져 보인다(cp949). 실제 값은 `--out` 파일을 `encoding='utf-8'`로 읽어 `unicode_escape`로 비교해 확인했다(정상 저장). 인자 파일은 `json.dump` 기본값(ensure_ascii, `\uXXXX`)으로 쓰는 편이 안전하다.
- `GetLogEntries`의 `\[Compiler\]` 패턴을 셸 인자 JSON에 넣으면 이스케이프가 깨진다 → Python으로 인자 파일을 만든다(`json.dump({'pattern':r'\[Compiler\]','category':'','maxEntries':30}, ...)`).
- 레이아웃: Think(65노드)와 컨트롤러 EventGraph는 `arrange_nodes` 뒤 PT 스크립트로 같은 x 열을 추정 너비 + 90 간격으로 다시 벌리고, 열 안에서는 추정 높이(50 + 28 × 핀 수) + 40만큼 아래로 밀었다. BP_EnemyBase EventGraph는 arrange가 이벤트를 체인 중간에 흩어 놓아 `set_node_position`으로 직접 배치했다(BeginPlay 줄 y 0, Sequence then_1 줄 y 480, OnDied 줄 y 1000, OnRespawned 줄 y 1350).

## 5단계 몬스터 2/2 (에디터 B): 예고원, 보스 GA, 보스 BP, PIE 스모크

### 예고원 액터 (BP_TelegraphCircle)

- `StaticMeshTools get_bounds {"mesh":{"refPath":"/Game/LevelPrototyping/Meshes/SM_Cylinder.SM_Cylinder"}}` → min (-50,-50,0), max (50,50,100). **피벗이 바닥**이라 액터를 바닥 +2에 두면 원판이 바닥 위에 얹힌다. 반지름 50 → XY 배율 = 반지름 / 50, 높이 1 cm → Z 배율 0.01(계획 "높이 0.01배").
- `AcT add_component`(StaticMeshComponent `Disc`, DefaultSceneRoot 아래) → `OT set_properties {"instance":{"refPath":"...BP_TelegraphCircle_C:Disc_GEN_VARIABLE"},"values":{"StaticMesh":"/Game/LevelPrototyping/Meshes/SM_Cylinder.SM_Cylinder","RelativeScale3D":{"x":1,"y":1,"z":0.01},"OverrideMaterials":["/Game/SoulCombat/Materials/MI_SC_Telegraph.MI_SC_Telegraph"],"BodyInstance":{"collisionProfileName":"NoCollision","collisionEnabled":"NoCollision"},"bGenerateOverlapEvents":false,"CanCharacterStepUpOn":"ECB_No","CastShadow":false}}` → true.
- 주의: `get_properties ["BodyInstance.collisionProfileName"]`처럼 점 경로를 주면 `could not be read` 에러가 난다. `["BodyInstance"]` 전체를 읽고 그 안에서 찾는다.
- 노드 ID: `Transformation|SetRelativeScale3D :self (Variables|Default|GetDisc) :NewScale3D v`, `Math|Float|Lerp :A :B :Alpha`, `Math|Float|Min(Float) :A :B`, `Math|Float|SafeDivide :A :B`. Tick 머리는 `(event EventTick (DeltaSeconds) ...)`.
- 0 나눗셈 방지: `(select (> grow 0.0) (Math|Float|Min(Float) :A 1.0 :B (Math|Float|SafeDivide :A elapsed :B grow)) 1.0)`. Select는 양쪽 입력을 모두 계산하므로 `/` 대신 SafeDivide를 쓴다.

### 보스 GA (GA_SCBase 자식)

- GA_SCBase 자식을 `BT create`하면 EventGraph에 연결 없는 `ActivateAbility`(K2Node_Event_0)와 `OnEndAbility`(K2Node_Event_1)만 생긴다. Parent 노드는 없다. `(event Ability|EventActivateAbility ...)`와 `(event Ability|EventOnEndAbility (bWasCancelled) ...)`로 쓰면 기존 노드에 그대로 이어진다. 안 쓰는 OnEndAbility는 `delete_node`로 지운다.
- 캡슐 바닥 위치: `(Components|Capsule|GetScaledCapsuleHalfHeight :self (Class|Character|GetCapsuleComponent :self ch))`. 여기서 `ch = (CallFunction|GetAvatarCharacter)`(GA_SCBase 함수, 실행 노드)다.
- BP 액터 스폰과 초기화: `(bind tel (Game|SpawnActorfromClass :Class "/Game/SoulCombat/Combat/BP_TelegraphCircle.BP_TelegraphCircle_C" :SpawnTransform (Math|Transform|MakeTransform :Location loc) :CollisionHandlingOverride "AlwaysSpawn" :Owner ch))` → 노드가 `Game|SpawnActorBPTelegraphCircle`로 바뀐다. 이어서 `(Class|BPTelegraphCircle|Init :self tel :Radius r :Duration d)`. BP 타입 오브젝트 변수는 `add_object_variable ... "object_class":{"refPath":"/Game/SoulCombat/Combat/BP_TelegraphCircle.BP_TelegraphCircle_C"}`로 만들고, Set 노드에 바로 연결된다.
- 파괴: `(Utilities|IsValid t (:"Is Valid" (Actor|DestroyActor :self t) (Variables|Slam|State|SetTelegraph)) (:"Is Not Valid"))`. 슬램 체인과 OnEndAbility가 같은 함수 `DestroyTelegraph`를 부른다.
- 몽타주 섹션 루프 활용: AM_ChargedAttack의 `Charge` 섹션은 자기 자신으로 루프한다(engine-api-notes D1b). 그래서 다음 순서가 그대로 동작한다.
  1. `PlayMontageAndWait :StartSection "Charge"`
  2. `WaitDelay(TelegraphTime)`
  3. `(Ability|Animation|MontageJumptoSection :SectionName "Attack")` (인터럽트가 나지 않는다)
  4. `WaitDelay(HitDelay)` (계획대로 0.45. Attack 섹션 노티파이 시점은 0.367이지만 계획 값을 쓴다)

  몽타주가 끝나면 BlendOut/Completed 핀이 EndAbility를 부른다.
- 두 번째 몽타주(돌진): 첫 PlayMontageAndWait(윈드업)의 Completed/BlendOut/Interrupted/Cancelled 핀은 **연결하지 않는다**. AM_Dash가 시작되면 윈드업 태스크가 OnInterrupted를 동기로 낸다. 여기에 EndAbility를 걸면 돌진이 바로 끊긴다(engine-api-notes B1). 어빌리티 종료는 마지막 WaitDelay → EndAbility에서만 한다.
- 돌진: `(Ability|Tasks|ApplyRootMotionConstantForce :TaskInstanceName "Charge" :WorldDirection (Transformation|GetActorForwardVector :self av) :Strength speed :Duration dur :bIsAdditive false :VelocityOnFinishMode "ClampVelocity" :ClampVelocityOnFinish 0.0 :bEnableGravity true (:then ...))`. 힘이 끝나면 속도 0으로 멈춘다.
- 여러 시점 타격: Sequence 대신 WaitDelay를 이어 붙였다(`t0`, `t1-t0`, `t2-t1`, `EndTime-t2`). 시점 값은 float 배열 변수 `HitTimes`([0.15, 0.35, 0.55])와 `EndTime`(0.8)에 둔다. `(bind t0 (Utilities|Array|Get(acopy) times 0))`에서 인덱스는 핀 기본값으로 들어간다.
- 중복 타격 방지: `(for t targets (if (not (Utilities|Array|ContainsItem (Variables|Charge|State|GetHitActors) t)) (Utilities|Array|Add (Variables|Charge|State|GetHitActors) t) (Class|ACCombatComponent|ApplyHit :self combat :Target t ...)))`. 배열 변수 Get 출력에 Add나 Clear(`Utilities|Array|Clear`)를 연결하면 멤버 배열 자체가 바뀐다. 어빌리티 시작 시 Clear한다.
- CDO: `{"abilityTags":{...Slam},"activationBlockedTags":{State.Dead, State.HitStun},"activationOwnedTags":{State.Attacking},"cooldownGameplayEffectClass":"/Game/SoulCombat/GAS/Effects/GE_Cooldown_Boss_Slam.GE_Cooldown_Boss_Slam_C"}`와 변수 기본값을 `set_properties` 한 번으로 넣었다. instancingPolicy는 부모에서 InstancedPerActor를 상속한다.

### 보스 BP (BP_EnemyBase 자식): 부모 BeginPlay를 지우지 않고 바인딩 추가

- 새 자식 BP의 `BeginPlay` + `Parent: BeginPlay` 노드는 그대로 둔다. **BeginPlay를 DSL로 쓰면 부모 호출 노드가 지워진다**(1/2 참고). 대신 이렇게 한다.
  1. `BT add_event {"event_name":"InitEnrage"}`
  2. `(event Custom|InitEnrage (Default|AssignOnHealthChanged :self (Variables|Default|GetCombat)))`
  3. 자동으로 생긴 `OnHealthChanged_Event (NewValue MaxValue)`의 본문을 두 번째 write로 쓴다.
  4. `BT create_node {"type_id":"CallFunction|InitEnrage"}`
  5. `connect_pins`: Parent:BeginPlay `then`(index 0) → InitEnrage `execute`(index 0)

  SlateInspector 없이 끝난다. 부모 계층에 OnHealthChanged 바인딩이 없어서 이벤트 이름에 숫자가 붙지 않았고(`_Event`), 스트레이 이벤트도 생기지 않았다.
- 자기 ASC에 GE 적용: `(bind asc (Class|ACCombatComponent|GetASC :self (Variables|Default|GetCombat)))` → `(GameplayEffects|ApplyGameplayEffectToSelf :self asc :GameplayEffectClass "/Game/SoulCombat/GAS/Effects/GE_Boss_Enrage.GE_Boss_Enrage_C" :Level 1.0 :EffectContext (GameplayEffects|MakeEffectContext :self asc))`. **Level 핀 기본값이 0.0**이므로 반드시 명시한다.
- 오브젝트 인자가 있는 디스패처 방송: `add_event_dispatcher OnEnraged` + `add_object_function_param {"param_name":"Boss","object_class":{"refPath":"/Script/Engine.Actor"}}` → `(Default|CallOnEnraged :Boss self)`.
- 머티리얼 슬롯: `Default__BP_Enemy_Boss_C:CharacterMesh0`에 `{"OverrideMaterials":["/Game/SoulCombat/Materials/MI_SC_Boss_01.MI_SC_Boss_01","/Game/SoulCombat/Materials/MI_SC_Boss_02.MI_SC_Boss_02"]}`를 넣으면 슬롯 0, 1 순서대로 들어간다.
- **함정: 루트(캡슐) 배율은 레벨에 배치하면 사라진다.** `CollisionCylinder`의 `RelativeScale3D` 1.5는 CDO에 저장된다. 하지만 `SceneTools add_to_scene_from_class`(xform scale 생략 = 1)로 놓은 액터는 배율이 1이었다. PIE에서 z가 89.6(반높이 88)으로 나왔다. 루트 컴포넌트 트랜스폼을 액터 트랜스폼이 덮기 때문이다.
  - 해결: 캡슐은 배율 1로 두고 크기 자체를 키운다(`{"CapsuleHalfHeight":132,"CapsuleRadius":51}`). 메시에는 `{"RelativeScale3D":{"x":1.5,"y":1.5,"z":1.5},"RelativeLocation":{"x":0,"y":0,"z":-133.5}}`를 넣는다.
  - 이렇게 하면 배치 방식과 상관없이 1.5배가 된다(PIE z 134).
- 이미 배치한 인스턴스에는 BP를 컴파일한 뒤에도 옛 캡슐 값(88/34)이 남았다. `remove_from_scene` 후 `add_to_scene_from_class`로 다시 놓고, 인스턴스 값(`bStartDormant`)을 다시 넣는다.

### PIE 스모크 테스트

- 레벨 준비 순서:
  1. `AT duplicate {"path":"/Engine/Maps/Templates/Template_Default","new_path":"/Game/_Scratch/L_EnemySmoke"}` → 저장
  2. 현재 레벨 is_dirty가 false인지 확인 → `ST load_level`
  3. `WorldSettings_1`에 DefaultGameMode 설정
  4. `AcT set_actor_transform`으로 `PlayerStart_0`을 (0,0,100)으로 이동
  5. `ST add_to_scene_from_class`로 적 배치 → 인스턴스에 `OT set_properties {"bStartDormant":false}` → 저장
- PIE 월드 액터 경로: `/Game/_Scratch/UEDPIE_0_L_EnemySmoke.L_EnemySmoke:PersistentLevel.<액터 이름>`. 이 경로로 다음이 모두 된다.
  - ASI 툴: GetAttributeValues, GetActiveTags, GetActiveEffects, GetGrantedAbilities
  - `AcT get_actor_transform`
  - PIE 액터 인스턴스 `OT get_properties`(예: 예고원 `.Disc`의 RelativeScale3D, `Elapsed`)

  PT 스크립트 하나로 묶어서 폴링했다.
- 에디터 B가 백그라운드에 있으면 PIE가 `max tick rate 3`으로 돈다(로그: `Bringing World ... up for play (max tick rate 3)`).
  - 타이머와 WaitDelay가 3 fps 단위로 끊기지만, 전투 흐름을 확인하는 데는 문제없었다.
  - 한 PT 스크립트 안의 연속 호출도 프레임을 넘긴다. 그래서 값끼리 한 틱 어긋날 수 있다(예: 배율은 Elapsed 0.667 기준인데 Elapsed는 1.0으로 읽힘).
- 쿨다운 태그로 발동을 확인한다.
  - `GetActiveTags`에 `Cooldown.Enemy.Attack.1/.2/.3`이 나온다. 각각 보스 근접, 내려찍기, 돌진 쿨다운 GE가 주는 태그다.
  - `GetActiveEffects`에 `Default__GE_Cooldown_Boss_*_C`와 남은 시간이 나온다.
  - 예고원은 슬램 중에만 `find_actors`(클래스 BP_TelegraphCircle_C)에 잡히고, 끝나면 사라졌다.

## 5단계 검증 지적 수정 (에디터 B)

### 수치 기본값 고치기: 계획 값 우선

- 노티파이 시점(Melee01 0.467, Attack 섹션 0.367)을 쓰지 말고 계획 값을 쓴다. 검증은 계획서 숫자와 대조한다.
- GA CDO 한 값만 바꾸기: `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/GAS/Abilities/GA_Enemy_Melee.GA_Enemy_Melee"},"values":"{\"HitTime\":0.45}"}` → true. 자식 GA_Enemy_Melee_Boss는 자기 값(0.40)을 따로 넣어 두었으므로 그대로다(get_properties로 확인).
- BP 변수 기본값도 같다: `GA_Boss_Slam.GA_Boss_Slam`에 `{"HitDelay":0.45}`. `compile_blueprint` 뒤에도 값이 유지됐다(get_properties로 확인).

### 부모 컴포넌트 템플릿을 바꿔도 자식 BP에는 안 넘어간다 (함정)

- `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/Characters/Enemies/BP_EnemyBase.BP_EnemyBase_C:OverheadBar_GEN_VARIABLE"},"values":"{\"relativeLocation\":{\"x\":0,\"y\":0,\"z\":120}}"}` → 부모는 120이 됐다. 하지만 자식 4개(Grunt, TrainingDummy, SealCrystal, Boss)의 `<Child>_C:OverheadBar_GEN_VARIABLE`은 부모를 `compile_blueprint`한 뒤에도 옛 값 115였다. 자식은 에디터를 한 번 열어 상속 컴포넌트 템플릿을 갖고 있었다.
- 에디터 디테일 패널과 달리 ObjectTools 쓰기는 자식 템플릿으로 전파하지 않는다. 그대로 저장하면 자식에 115가 덮어쓴 값으로 남는다.
- 해결: 자식마다 같은 `set_properties`를 넣고, get_properties로 확인한 뒤 저장한다. 부모 컴포넌트 값을 고칠 때는 항상 자식 템플릿도 읽어 본다.

### 예고원 크기 0에서 시작

- `BP_TelegraphCircle` CDO에 `{"DiscHeightScale":0.01,"MinRadiusRatio":0.0}`, `BP_TelegraphCircle_C:Disc_GEN_VARIABLE`에 `{"RelativeScale3D":{"x":1,"y":1,"z":0.01}}`를 넣었다.
- UpdateDiscScale은 `Lerp(MinRadiusRatio, 1, 진행률)`이다. 그래서 그래프를 고치지 않아도 크기 0 → Radius로 자란다. Init이 곧바로 UpdateDiscScale을 부르므로, 템플릿 XY 1은 에디터 뷰포트 미리보기에만 쓰인다.

### 수정 뒤 저장 점검

- 검증 패스가 컴파일해서 dirty가 된 같은 단계 에셋(GA_Boss_Charge, BP_EnemyAIController)도 있다.
  1. 먼저 find_nodes + get_node_infos로 연결 0 노드를 찾는다. 스트레이 `*_Event_N`이 없는지 확인한다.
  2. 없으면 `compile_blueprint(warnings_as_errors)` → `save_assets`(경로 명시) → `is_dirty` false 순서로 끝낸다.
- NodeInfo 필드 이름: `input_pins`/`output_pins`, 각 핀의 `connected_pins`, 노드 종류 `type_id`, 위치 `position`. 연결 수는 모든 핀의 `connected_pins` 길이를 더해 센다.

### 분노 배너는 컨트롤러 UI 허브가 필요하다 (6단계 예정 항목)

- 에디터 B의 `BP_SCPlayerController`에는 입력 함수만 있고 `ShowRoomBanner`가 없다(list_graphs로 확인). 그래서 BP_Enemy_Boss에서 배너를 부를 수 없다.
- 6단계에서 컨트롤러 UI 허브가 있는 에디터가 맡아야 한다. 방법은 둘 중 하나다.
  - `BP_Room_Boss`가 보스의 `OnEnraged(Boss)`를 바인딩한다. 예: `(Default|AssignOnEnraged :self boss)` → 핸들러 `(event Custom|OnEnraged_Event (Boss) ...)`에서 `PC.ShowRoomBanner("수호자가 분노했다!", "")`.
  - 또는 BP_Enemy_Boss의 OnEnraged 호출 뒤에 `GetPlayerController(0)` → `CastToBP_SCPlayerController` → `ShowRoomBanner`를 잇는다.
- 결정(2차 수정): 5단계 결함이 아니라 **6단계 예정 항목**으로 넘긴다. 5단계 몫은 "분노 판정 + GE_Boss_Enrage 적용 + `OnEnraged(Boss)` 방송"까지다. 에디터 B에서 확인한 것:
  - `BT list_graphs {"blueprint":{"refPath":"/Game/SoulCombat/Characters/Enemies/BP_Enemy_Boss.BP_Enemy_Boss"}}` → `UserConstructionScript`, `EventGraph`, `OnEnraged`(디스패처)
  - 같은 호출을 `/Game/SoulCombat/Core/BP_SCPlayerController.BP_SCPlayerController`에 하면 입력 함수 7개와 EventGraph뿐이다. `ShowRoomBanner`는 없다.
- 6단계 작업자 주의: 바인딩을 넣은 뒤에는 그 그래프(BP_Room_Boss나 BP_Enemy_Boss EventGraph)에 `read_graph_dsl`을 쓰지 않는다. Assign 노드가 있는 그래프를 읽을 때마다 연결 없는 `OnEnraged_Event_N`/`OnHealthChanged_Event_N`이 새로 생긴다. 확인은 `find_nodes {"graph":G,"title":"","entry_points_only":true}` + `get_node_infos`로 한다. BP_Enemy_Boss의 진입 노드는 지금 3개다(`AddEvent|EventBeginPlay`, `AddEvent|Custom|InitEnrage`, `AddEvent|Custom|OnHealthChanged_Event`). 넷째가 보이면 스트레이다.

## 6단계 방 로직과 던전 게임 모드 (에디터 B)

같은 병렬 워크플로 기록이라 여기에 잇는다. 표기는 위와 같다(`AcT`, `ST` = SceneTools, `APP`, `PT`).

### 부모 방 BP (BP_DungeonRoom)

- 루트 이름 붙이기: `AcT add_component`(SceneComponent `Root`) → `AcT set_parent_component {"component":{"refPath":"...BP_DungeonRoom_C:DefaultSceneRoot_GEN_VARIABLE"},"parent":{"refPath":"...BP_DungeonRoom_C:Root_GEN_VARIABLE"}}` → `compile_blueprint`. 그 뒤 BoxComponent `RoomTrigger`, ArrowComponent `RespawnPoint`가 Root 아래로 붙는다.
- BoxComponent 기본값은 이미 `OverlapAllDynamic`(Pawn Overlap), `bGenerateOverlapEvents` true, `bHiddenInGame` true다. 그래서 크기·위치만 넣었다: `{"BoxExtent":{"x":800,"y":800,"z":250},"RelativeLocation":{"x":0,"y":0,"z":250}}`. Arrow도 `bHiddenInGame` true.
- 자기 클래스 타입 디스패처 인자: `add_event_dispatcher OnRoomCleared` → `add_object_function_param {"graph":{"refPath":"...BP_DungeonRoom:OnRoomCleared"},"param_name":"Room","object_class":{"refPath":"/Game/SoulCombat/Dungeon/BP_DungeonRoom.BP_DungeonRoom_C"},"input_param":true}` → 핀 타입 `BP Dungeon Room Object Reference`. 게임 모드 핸들러에서 캐스트 없이 `Class|BPDungeonRoom|GetIsFinalRoom :self Room`을 바로 쓴다.
- Text가 비었는지: `Utilities|Text|TextIsEmpty`(`IsEmpty`로 찾으면 String/Array 버전이 먼저 나온다). 오브젝트 비교 `(== OtherActor (Game|GetPlayerPawn :PlayerIndex 0))` → `Utilities|Equal(Object)`.
- 플레이어 전투 컴포넌트: `(Actor|GetComponentbyClass :self pawn :ComponentClass "/Game/SoulCombat/Components/AC_CombatComponent.AC_CombatComponent_C")` → `(Class|ACCombatComponent|SetRespawnTransform :self combat :NewTransform (Transformation|GetWorldTransform :self (Variables|Default|GetRespawnPoint)))`. 컴포넌트 변수 노드는 `Variables|Default|Get<컴포넌트>`.
- 출력 없는 함수 `BeginRoomLogic`(본문 `(CallFunction|ClearRoom)`)을 부모에 두면 자식이 `BT add_event {"event_name":"BeginRoomLogic"}` → `AddEvent|EventBeginRoomLogic`로 오버라이드한다. DSL 머리는 `(event EventBeginRoomLogic ...)`. 부모 `StartRoom`의 `(CallFunction|BeginRoomLogic)`은 자식 이벤트로 가상 호출된다(PIE에서 BP_Room_Mob 쪽이 돈 것으로 확인).
- 부모가 BP인 새 Actor 자식의 EventGraph에는 연결 없는 BeginPlay, ActorBeginOverlap, Tick만 있고 Parent 노드는 없다(부모가 BeginPlay를 쓰지 않으므로). 셋 다 `delete_node`.

### 방 자식: 적 배열 순회 + 핸들러 하나로 OnDied 바인딩

- 루프 안에서 적마다 `(bind combat (Class|BPCombatCharacterBase|GetCombat :self e)) (Default|AssignOnDied :self combat)`를 쓴다. Assign 노드 하나가 반복 실행되고, 자동으로 생긴 `OnDied_Event (DeadActor)` 하나가 모든 적을 받는다. 부모 계층에 `OnDied_Event`가 없어서 이름에 숫자가 붙지 않았다. 본문은 두 번째 `write_graph_dsl`로 `(event Custom|OnDied_Event (DeadActor) ...)`.
- 보스 방: `(bind eb (Utilities|Casting|CastToBP_Enemy_Boss :Object boss) (:then (Default|AssignOnEnraged :self eb)) (:CastFailed))` → `OnEnraged_Event (Boss)` 자동 생성. 같은 그래프에서 Assign 두 종류(OnDied, OnEnraged)를 write 한 번으로 만들었고 스트레이 `*_Event_N`은 생기지 않았다(read_graph_dsl을 쓰지 않았다).
- **이름 충돌 회피**: OnEnraged 인자 이름이 `Boss`라서 핸들러 이벤트 출력 핀도 `Boss`가 된다. 같은 이름의 멤버 변수를 두지 않으려고 상태 변수를 `CurrentBoss`로 지었다(`remove_variable` 후 다시 추가).
- break 없이 첫 번째 유효한 적 고르기: `(for e enemies (Utilities|IsValid e (:"Is Valid" (Utilities|IsValid (GetCurrentBoss) (:"Is Valid") (:"Is Not Valid" (SetCurrentBoss e)))) (:"Is Not Valid")))`. 오브젝트 변수를 None으로 초기화할 때는 `(Variables|Room|Boss|State|SetCurrentBoss)`(값 생략).
- 이름 선택: `(select (Utilities|Text|TextIsEmpty (GetBossNameOverride)) (Class|BPEnemyBase|GetDisplayName :self boss) (GetBossNameOverride))` → Select(Text).
- 최대 웨이브: `(SetMaxWave (Math|Integer|Max(Integer) :A (GetMaxWave) :B (Class|BPEnemyBase|GetWave :self e)))`. 다른 BP의 변수 Get(`GetWave`, `GetCombat`, `GetDisplayName`, `GetIsDead`)은 VariableGet 노드로 만들어진다.
- 함수 이름 타이머(이벤트 방): `(Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "OnTimeUp" :Time (Variables|Room|Event|GetTimeLimit) :bLooping false)`. 해제는 `(Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "OnTimeUp")`. 대상은 인자 없는 BP 함수 `OnTimeUp`이다.
- 플레이어에게 GE 적용: `(bind asc (Ability|GetAbilitySystemComponent :Actor (Game|GetPlayerPawn :PlayerIndex 0)))` → `(GameplayEffects|ApplyGameplayEffectToSelf :self asc :GameplayEffectClass "/Game/SoulCombat/GAS/Effects/GE_RestoreFull.GE_RestoreFull_C" :Level 1.0 :EffectContext (GameplayEffects|MakeEffectContext :self asc))`. Level 기본값이 0이라 1.0을 꼭 넣는다.
- 진행 문자열: `Append :A "봉인석 " :B (ToString(Integer) n)` → `Append :A s1 :B " / "` → `Append :A s2 :B (ToString(Integer) total)` → `ToText(String)`. 공용 함수 `UpdateProgress`로 뺐다.
- 배너 겹침 주의(설계): `ClearRoom`이 `ClearBannerTitle`('클리어')을 띄운다. 결과 배너('성공!'/'실패')를 먼저 띄우는 이벤트 방은 CDO `ClearBannerTitle`을 ''로 두었다. 그러지 않으면 '클리어'가 곧바로 덮는다.

### 게임 모드 (BP_DungeonGameMode)

- BP_SCGameModeBase 자식의 EventGraph에는 BeginPlay/Tick만 있고 Parent 노드가 없다(부모에 BeginPlay 없음). DSL `(event EventBeginPlay ...)`로 그대로 이어 썼고 Tick은 지웠다.
- `(bind rooms (Actor|GetAllActorsOfClass :ActorClass "/Game/SoulCombat/Dungeon/BP_DungeonRoom.BP_DungeonRoom_C")) (for room rooms (Default|AssignOnRoomCleared :self room))` → `OnRoomCleared_Event (Room)`(BP Dungeon Room 타입)이 자동 생성된다. 경과 시간은 Delay 전에 `ClearSeconds`에 저장해서 연출 대기 시간이 기록에 섞이지 않게 했다.

### 레벨 인스턴스 컴포넌트의 구조체 값 (함정)

- **레벨에 놓인 BP 액터의 컴포넌트에 구조체를 한 번에 넣으면 첫 필드만 들어간다.** `OT set_properties {"instance":{"refPath":"/Game/_Scratch/L_RoomSmoke.L_RoomSmoke:PersistentLevel.BP_Room_Mob_C_0.RoomTrigger"},"values":"{\"BoxExtent\":{\"x\":600,\"y\":600,\"z\":250}}"}` → true인데 다시 읽으면 (600, 800, 250)이다. (601, 599, 251)을 넣어도 x만 바뀌었다. 첫 필드가 바뀔 때 컨스트럭션 스크립트가 다시 돌며 컴포넌트가 새로 만들어지는 것으로 보인다. BP 템플릿(`..._C:RoomTrigger_GEN_VARIABLE`)에서는 세 필드가 한 번에 들어갔다.
- 해결: 필드마다 따로 부른다. `{"BoxExtent":{"x":600}}` → `{"BoxExtent":{"y":600}}` → `{"BoxExtent":{"z":250}}` → (600, 600, 250). 액터 자체 프로퍼티(EntryDoor, ExitDoor, Enemies 배열, bStartDormant와 Wave)는 한 번에 들어갔다.
- 레벨 액터 참조 넣기: `{"EntryDoor":"<레벨>:PersistentLevel.BP_DungeonDoor_C_0","Enemies":["...BP_Enemy_Grunt_C_0","...BP_Enemy_Grunt_C_1"]}` → 읽으면 `{"refPath":...}`.

### PIE에서 방 진입 테스트

- `APP StartPIE` 뒤 `AcT set_actor_transform {"actor":{"refPath":"/Game/_Scratch/UEDPIE_0_L_RoomSmoke.L_RoomSmoke:PersistentLevel.BP_PlayerCharacter_C_0"},"xform":{"location":{"x":1300,"y":0,"z":100}}}` → true. 순간이동으로도 트리거 BeginOverlap이 불렸다.
- 기다리기: Bash `sleep`은 막혀 있어서 `python -c "import time;time.sleep(3)"`을 썼다(그동안 에디터는 계속 돈다).
- HUD 안 중첩 위젯 경로는 `WidgetTree`가 아니라 `WidgetTree_0`이다. `OT get_properties {"instance":<PIE PC>,"properties":["HUD"]}` → HUD ref → `get_properties(HUD, ["RoomBanner"])` → `/Engine/Transient.UnrealEdEngine_0:BP_SCGameInstance_C_0.WBP_PlayerHUD_C_0.WidgetTree_0.RoomBanner`. 그 안의 `titleText`(`...RoomBanner.WidgetTree_0.TitleText`)에서 `text`를 읽어 배너 내용을 확인했다. 배너는 3초(`pendingDuration`) 뒤 Collapsed가 된다.
- 플레이어 리스폰 위치: `OT get_properties {"instance":{"refPath":"...BP_PlayerCharacter_C_0.Combat"},"properties":["respawnTransform"]}`.

## 7단계 로직 액터 배치 (에디터 B, 실제 맵 L_CombatField·L_Dungeon_01)

### 배치한 BP 액터 컴포넌트: 프로퍼티도 한 호출에 하나씩 (함정 확장)

- 구조체 필드만이 아니다. **서로 다른 프로퍼티 여러 개를 한 번에 넣어도 첫 프로퍼티만 들어간다.** `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/Maps/L_CombatField.L_CombatField:PersistentLevel.BP_Enemy_Grunt_C_1.Combat"},"values":"{\"bRespawnOnDeath\":true,\"bDestroyOnDeath\":false,\"RespawnDelay\":5}"}` → true인데 다시 읽으면 `{"bRespawnOnDeath":true,"bDestroyOnDeath":true,"RespawnDelay":3}`였다.
- 해결: `{"bRespawnOnDeath":true}` → `{"bDestroyOnDeath":false}` → `{"RespawnDelay":5}`처럼 호출을 나눈다. 그 뒤 `set_actor_folder`, 액터 자체 프로퍼티(`bStartDormant`) 설정에도 값이 유지됐다(get_properties 확인, 저장 후 PIE에서도 적용).
- 액터 자체 프로퍼티는 여러 개를 한 번에 넣어도 됐지만, 안전하게 PT 스크립트에서 `for k,v in vals.items(): sp(R,{k:v})`로 하나씩 넣고 한 번에 읽어 확인했다(방 RoomIndex·EntryDoor·ExitDoor·bIsFinalRoom·Enemies).
- 배치 BP 인스턴스의 컴포넌트 ref: `<맵>.<맵>:PersistentLevel.<액터 이름>.<컴포넌트 이름>`(`AcT get_components`가 돌려준다. 예 `.Combat`, `.RoomTrigger`, `.RespawnPoint`, `.DoorMesh`).

### 캐릭터 z와 방 트리거

- 캐릭터 캡슐 반높이 읽기: `OT get_properties {"instance":{"refPath":"/Game/SoulCombat/Characters/Enemies/BP_Enemy_Grunt.Default__BP_Enemy_Grunt_C:CollisionCylinder"},"properties":["CapsuleHalfHeight","CapsuleRadius"]}` → Grunt·Dummy·SealCrystal 88/34, Boss 132/51. 바닥 z=0 위에 놓으려면 z = 반높이 + 2~4(Grunt·Dummy 92, 봉인석 90, 보스 136). PIE에서 떨어져 Grunt 90.2, 보스 134.2로 선다.
- 방 트리거: 방 액터를 방 중심 (cx,0,0)에 두면 RoomTrigger 기본 RelativeLocation이 (0,0,250)이라 BoxExtent만 필드별로 바꾼다(`{"BoxExtent":{"x":ex}}` → `{"y":ey}` → `{"z":250}`). RespawnPoint는 `{"RelativeLocation":{"x":<방 min x + 250 - cx>}}` 한 필드만 넣으면 y 0, z 100이 유지된다. `AcT get_actor_bounds(방)` = 트리거 범위(예 Room_Mob1 (1200,-800,0)~(2800,800,500))라 바로 대조된다.

### 스폰 지점이 방 트리거 안이면 방이 시작되지 않는다 (BP_DungeonRoom 한계)

- L_Dungeon_01 PIE: PlayerStart (0,0)가 Room_Start 트리거(x·y ±400) 안인데 3초 뒤 `bStarted`/`bCleared` false. 플레이어를 (-500,0,100)으로 옮겼다가 (0,0,100)으로 돌려놓으면 바로 true/true가 됐다. 트리거 크기·위치는 맞다.
- 원인(그래프 읽기로 확인, `find_nodes` EventGraph): 처리기는 `OnComponentBeginOverlap(RoomTrigger)` → `OtherActor == GetPlayerPawn(0)` AND NOT bStarted → StartRoom 하나뿐이다. PIE에서 폰은 월드 BeginPlay 전에 스폰되고, 첫 겹침은 빙의 전에 생긴다. 그래서 그때는 GetPlayerPawn(0)이 None이고, 조건이 거짓이 되는 것으로 본다. 그 뒤로는 겹침이 새로 생기지 않는다.
- (고침: 아래 '7c 검증 지적 수정: 방 초기 겹침 확인' 절) 고치려면 BP 수정이 필요하다(이번 작업 범위 밖): BP_DungeonRoom BeginPlay에서 한 틱 뒤(Delay 0) `RoomTrigger.IsOverlappingActor(GetPlayerPawn(0))`이고 시작 전이면 StartRoom. 레벨만 바꾸는 대안은 Start 트리거를 스폰 지점 앞(예 x[100,400])으로 옮겨 걸어 들어가게 하는 것이다.
- PIE 중 `AcT set_actor_transform`은 되지만, 로그에 `LogUtils: Error: The Editor is currently in a play mode.`와 `LevelEditorSubsystem: Error: GetCurrentLevel...`가 한 번씩 남는다(툴이 남기는 것). PIE 로그 검사에서 이 두 줄과 `list_properties`가 남기는 `LogJson: Warning: ... unhandled during Json schema generation`은 빼고 본다.

## 7c 흐름 테스트 (에디터 B, 키보드 없이 게임 루프 검증)

결과는 `flowtest-report.md`에 있다. 여기에는 다시 쓸 레시피와 함정만 적는다.

### 적 즉사 도우미 (GE 스펙 + SetByCaller, DSL)

- `/Game/_Scratch/BP_TestKiller`: `add_variable Interval float` → `add_function_graph KillActive` → 아래 DSL → `compile_blueprint {"warnings_as_errors":true}` → CDO `{"Interval":1.0}`.
  ```
  (fn KillActive ()
    (bind enemies (Actor|GetAllActorsOfClass :ActorClass "/Game/SoulCombat/Characters/Enemies/BP_EnemyBase.BP_EnemyBase_C"))
    (for e enemies
      (bind combat (Class|BPCombatCharacterBase|GetCombat :self e))
      (if (and (Class|BPEnemyBase|GetActive :self e) (not (Class|ACCombatComponent|GetIsDead :self combat)))
        (bind asc (Ability|GetAbilitySystemComponent :Actor e))
        (bind spec (GameplayEffects|MakeOutgoingSpec :self asc :GameplayEffectClass "/Game/SoulCombat/GAS/Effects/GE_Damage.GE_Damage_C" :Level 1.0 :Context (GameplayEffects|MakeEffectContext :self asc)))
        (bind spec2 (Ability|GameplayEffect|AssignTagSetbyCallerMagnitude :SpecHandle spec :DataTag "(TagName=\"Data.Damage\")" :Magnitude 100000.0))
        (GameplayEffects|ApplyGameplayEffectSpecToSelf :self asc :SpecHandle spec2))))
  ```
  - `MakeOutgoingSpec`의 `Level` 기본값은 0.0이라 1.0을 꼭 넣는다.
  - `AssignTagSetbyCallerMagnitude`는 실행 노드다. 출력 스펙을 bind해서 Apply에 넘긴다.
  - bool 멤버 Get은 `GetActive`/`GetIsDead`(b 빠짐)로 쓰고, 만들어진 노드는 `|GetbActive`로 읽힌다.
- 타이머: `(event EventBeginPlay (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "KillActive" :Time (Variables|Default|GetInterval) :bLooping true))`.
- 킬러 GE도 `GC_Hit`를 부른다. 그래서 봉인석에서 `spine_03` 소켓 경고가 난다(보고서 B2).

### 순서대로 움직이는 드라이버 액터 (Delay 체인, DSL)

- BeginPlay 한 줄에 `(Utilities|FlowControl|Delay :Duration x)`를 문장으로 이어 쓰면 Completed에 순서대로 붙는다. 캐스트 뒤에는 `(:then ...)` 안에 Delay를 계속 넣어도 된다.
- 벡터 × 실수: `(* fwd (Variables|Default|GetFrontDistance))` → `Math|Vector|vector*vector` 노드가 되지만 B 핀이 `Float (double-precision)`으로 잡혀 경고 없이 컴파일된다. 게이트 앞 = `(+ (+ (Transformation|GetActorLocation :self g) (* fwd 250)) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 100.0))`.
- 플레이어 순간이동(BP 안): `(Transformation|SetActorLocation :self (Game|GetPlayerPawn :PlayerIndex 0) :NewLocation v :bSweep false :bTeleport true)`.
- 다른 BP의 컴포넌트 함수: `(Class|ACInteractable|Interact :self (Class|BPDungeonGate|GetInteractable :self gate) :Interactor pawn)`. 게이트는 `Actor|GetActorOfClass :ActorClass "/Game/SoulCombat/Dungeon/BP_DungeonGate.BP_DungeonGate_C"`로 찾는다(출력이 BP 타입으로 잡힌다).
- 다른 위젯의 디스패처 방송(버튼 클릭 대용): `(Default|CallOnConfirmed :self w)`, `(Default|CallOnCancelled :self w)`. `w`는 `(Class|BPSCPlayerController|GetEntryWidget :self pc)`이고 self 핀 타입은 `WBP Dungeon Entry Object Reference`다.
- 진행 확인용 `Step`(int) 변수를 단계마다 Set하면, 폴링에서 드라이버가 어디까지 왔는지 바로 보인다.

### PIE 상태 폴링 (ProgrammaticToolset)

- 한 PT 스크립트에서 `ObjectTools.get_properties`를 액터마다 부르고, `ActorTools.get_actor_transform`과 `AbilitySystemInspectorToolset.GetAttributeValues/GetActiveEffects`를 같이 부른다. 속성 20여 개면 백그라운드 PIE(3 fps)에서 5~10초가 걸린다.
- 한 번의 폴링 안에서도 값끼리 프레임이 어긋난다. 예: 방 `bCleared` false인데 뒤에 읽은 배너 제목은 이미 '클리어'. 판정은 다시 한 번 읽어서 한다.
- 설정 JSON을 스크립트 문자열에 넣을 때 `CFG = %s % json.dumps(cfg)`로 넣으면 `true`가 파이썬에서 `name 'true' is not defined`가 된다. `CFG = json.loads(%r)`로 넣는다.
- 방·적 상태 프로퍼티: 방 `bStarted`, `bCleared`, Mob `CurrentWave`·`MaxWave`·`AliveCount`, Event `DestroyedCount`·`TotalCrystals`·`bEventDone`, Boss `CurrentBoss`, 문 `bIsOpen`, 적 `bActive`·`bHidden`(액터 숨김), 적 `<액터>.Combat`의 `bIsDead`, 게이트 `bIsOpen`·`bEntryOpen`, 게이트 컴포넌트 `<게이트>.DoorL`의 `RelativeLocation`, `<게이트>.PortalPlane`의 `bHiddenInGame`·`bVisible`.
- PC 위젯: `get_properties(PC, ["HUD","ClearWidget","EntryWidget","bShowMouseCursor"])`. 위젯이 없으면 문자열 `"None"`이 온다(dict가 아님). 있으면 `{"refPath":"/Engine/Transient.UnrealEdEngine_0:BP_SCGameInstance_C_<n>.WBP_DungeonClear_C_0"}`.
  - `<n>`은 PIE 세션마다 하나씩 늘었다.
  - 레벨을 이동하면 HUD가 `WBP_PlayerHUD_C_1`처럼 새로 생긴다.
  - 위젯 안 글자는 `<위젯>.WidgetTree_0.<TextBlock>`의 `text`로 읽는다(예: `...WBP_DungeonClear_C_0.WidgetTree_0.TimeText` → '클리어 시간 4.3초').
- HUD 자식 표시 여부: `get_properties(HUD, ["BossBar","EventTimer","RoomBanner"])` → 각 ref의 `visibility`. `Collapsed`는 숨김, `HitTestInvisible`/`SelfHitTestInvisible`은 표시다. 배너 제목은 `RoomBanner.WidgetTree_0.TitleText`에서 읽는다. 한 번도 표시되지 않았으면 디자인 기본값 '방 제목'이 그대로 남아 있다.
- 레벨 이동(OpenLevel) 뒤에는 PIE 경로가 바뀐다(`/Game/SoulCombat/Maps/UEDPIE_0_L_CombatField.L_CombatField:PersistentLevel.BP_PlayerCharacter_C_0`). 옛 경로를 쓰면 `Parameter error: ... is not valid Object for property 'instance'`가 난다. 이동 여부는 `find_actors {"actor_type":{"refPath":"/Script/Engine.GameModeBase"}}`로 본다. 로그 `LogNet: Browse: /Game/SoulCombat/Maps/L_CombatField#GateReturn`도 남는다.
- 대기: `python -c "import time;time.sleep(N)"`(Bash 쪽). PT 스크립트 안에서는 기다리지 않는다(스크립트가 도는 동안 게임이 멈출 수 있다, 검증 안 함).
- 짧게 떴다 사라지는 창(클리어 창 2초 뒤 표시, 5초 카운트다운)은 순간이동 직후 Bash 루프로 1~2초마다 한 번씩 작은 PT 스크립트(ClearWidget ref → 글자 3개)를 불러야 잡힌다.

### PIE 안 UMG 버튼 누르기 (SlateInspector) — 함정과 우회

- `SlateInspectorToolset Windows {"action":"list"}` → `[{"index":0,"title":"SoulCombat - Unreal Editor"}, ...]`. 뷰포트 PIE는 메인 창 안에 있다.
- `Snapshot {"ref":"","maxDepth":80}`(약 14 KB)에서 PIE 위젯이 보인다. 예: `button "입장" [pos=922,627 size=129,47] [ref=b22]`, `button "취소" [...] [ref=b23]`. ref는 스냅샷마다 바뀐다(다음 PIE에서 취소는 `b63`). 매번 새로 찾는다.
- **함정**: `Click {"ref":"b22"}` → `true`인데 OnClicked가 불리지 않았다. 다음 스냅샷에서 버튼이 `[focused]`로만 바뀌어 있었다.
- **우회(확인)**: `Click`으로 포커스를 준 뒤 `PressKey {"key":"Enter"}` → `true` → 버튼 OnClicked가 불렸다. '입장'은 L_Dungeon_01로 이동했고, '취소'는 창이 닫히고 bEntryOpen false가 됐다.
- 참고: 입장 창의 `bIsFocusable`이 false라 SetInputModeUIOnly 포커스 에러가 로그에 남는다(보고서 B4). 창을 열자마자 Enter를 보내면 어디에도 먹지 않는다. 먼저 Click으로 버튼에 포커스를 준다.

### 로그 필터 (PIE 흐름 테스트)

- 제외할 줄: `LogJson: Warning ... unhandled during Json schema generation`(list_properties), `LogUtils: Error: The Editor is currently in a play mode.`와 `LevelEditorSubsystem: Error: GetCurrentLevel...`(PIE 중 set_actor_transform), `LogAudioMixerWasapi` 경고.
- 로그 시각은 UTC다(로컬 21:17 = 로그 12:17). 비교할 때는 `l[1:20] >= '2026.09.29-12.17.10'`처럼 문자열로 비교한다.
- 이번에 새로 잡힌 게임 쪽 경고와 에러:
  - `GetSocketInfoByName(spine_03)` (봉인석, GC_Hit)
  - `Invalid material [MI_SC_Telegraph] used on Nanite static mesh [SM_Cylinder]`
  - `LogPlayerController: Error: InputMode:UIOnly - Attempting to focus Non-Focusable widget`

## 7c 검증 지적 수정: 방 초기 겹침 확인 (에디터 B)

### 스폰 지점이 트리거 안일 때 방 시작 (BP_DungeonRoom BeginPlay) — 버그 B1 수정

- BeginPlay 추가: `BT add_event {"blueprint":{"refPath":"/Game/SoulCombat/Dungeon/BP_DungeonRoom.BP_DungeonRoom"},"event_name":"ReceiveBeginPlay","position":{"x":0,"y":700}}` → `K2Node_Event_3`. 자식 BP_Room_*의 EventGraph에 BeginPlay가 없어서(find_nodes entry_points_only로 확인) 그대로 상속된다.
- 대기 시간 변수: `add_variable {"name":"InitialCheckDelay","type_name":"float"}` → `set_variable_category "Room"` → `set_variable_instance_editable true` → 컴파일 뒤 CDO `{"InitialCheckDelay":0.2}`.
- DSL(EventGraph에 Assign 노드가 없어 read_graph_dsl 버그와 무관):
  ```
  (event EventBeginPlay
    (Utilities|FlowControl|Delay :Duration (Variables|Room|GetInitialCheckDelay))
    (bind p (Game|GetPlayerPawn :PlayerIndex 0))
    (if (and (not (Variables|Room|State|GetStarted))
             (Collision|IsOverlappingActor :Other p))
      (CallFunction|StartRoom)))
  ```
- PIE 결과: 스폰 직후 Room_Start가 시작·클리어되고 배너('시련의 회랑')와 부활 지점(-350,0,100)이 설정됐다. 다른 방은 영향 없음.

### 같은 type_id가 두 클래스에 있을 때 (함정: IsOverlappingActor)

- `find_node_types {"type_id_filter":"IsOverlappingActor"}` → `["Collision|IsOverlappingActor","Collision|IsOverlappingActor"]`(Actor 버전, PrimitiveComponent 버전). DSL은 Actor 버전을 골라 `(Collision|IsOverlappingActor :self (Variables|Default|GetRoomTrigger) :Other p)`가 `RuntimeError: Could not connect pin RoomTrigger to self`로 실패한다(write 전체가 롤백되어 노드는 남지 않음). `Class|PrimitiveComponent|IsOverlappingActor`는 `does not exist`.
- 우회: DSL은 `:self` 없이(Actor 버전, self 기본) 쓰고, 컴포넌트 버전을 직접 만든다.
  - `BT create_node {"graph":{"refPath":"...BP_DungeonRoom:EventGraph"},"type_id":"Collision|IsOverlappingActor","pos":{"x":1680,"y":900},"declaring_class":{"refPath":"/Script/Engine.PrimitiveComponent"}}` → `get_node_infos`로 self 핀 타입 `Primitive Component Object Reference` 확인.
  - `create_node {"type_id":"Variables|Default|GetRoomTrigger"}` → `connect_pins`(Get 출력 0 → 새 노드 입력 0 self, GetPlayerPawn 출력 0 → 입력 1 Other) → Actor 버전 `delete_node` → 새 노드 출력 0 → AND 입력 1(B) `connect_pins` → `compile_blueprint warnings_as_errors` 통과.

### 부모에 새 변수를 더하면 자식 CDO·레벨 인스턴스는 기본값 0 (함정)

- 부모 BP_DungeonRoom CDO에 `InitialCheckDelay` 0.2를 넣고 자식 4개를 다시 컴파일해도 자식 CDO는 0이었다. 레벨에 놓인 방 인스턴스(L_Dungeon_01)도 0이었고, 레벨이 dirty가 됐다.
- 해결: 자식 CDO마다 `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/Dungeon/BP_Room_Start.BP_Room_Start"},"values":"{\"InitialCheckDelay\":0.2}"}`, 레벨 인스턴스는 `SceneTools find_actors {"actor_type":{"refPath":"/Game/SoulCombat/Dungeon/BP_DungeonRoom.BP_DungeonRoom_C"}}`로 모아 같은 값을 넣고 레벨을 저장(`save_assets`에 `/Game/SoulCombat/Maps/L_Dungeon_01` 명시). 이후 부모·자식 재컴파일 뒤에도 0.2 유지를 확인했다.
- 범위 주의: 이렇게 하면 부모 BP 하나를 고쳐도 자식 BP 파일과 맵 파일이 함께 바뀐다. 수정 단계의 허용 에셋 목록에 자식 BP와 맵을 처음부터 넣고, 본 프로젝트로 옮길 때도 부모·자식·맵을 한 묶음으로 옮긴다. 부모만 옮기면 자식 CDO와 레벨 인스턴스 값이 0이 된다.
- 확인 호출(읽기만, 파일 안 바뀜): `OT get_properties {"instance":{"refPath":"/Game/SoulCombat/Dungeon/BP_Room_Start.Default__BP_Room_Start_C"},"properties":["InitialCheckDelay"]}`. 레벨 쪽은 `SceneTools find_actors {"name":"","tag":"","collision_channels":[],"actor_type":{"refPath":"/Game/SoulCombat/Dungeon/BP_DungeonRoom.BP_DungeonRoom_C"}}`로 모은다(`name`·`tag`·`collision_channels`는 필수라 빈 값을 준다). 모은 액터마다 같은 `get_properties`를 부른다.
- 변경이 없는 BP에 `compile_blueprint`를 불러도 is_dirty는 false로 남았다(BP_Room_Start). 이때는 다시 저장하지 않는다.

## 7c 수정 확인: B1 보강, B4, B5 (에디터 B)

### 기존 실행 흐름에 IsValid 매크로 끼우기 (DSL 재작성 없이)

- DSL로 다시 쓰면 손으로 만든 노드(예: `declaring_class`로 만든 PrimitiveComponent 버전 IsOverlappingActor)가 바뀔 수 있다. 그래서 노드 단위로 끼웠다.
  1. `BT create_node {"graph":{"refPath":"/Game/SoulCombat/Dungeon/BP_DungeonRoom.BP_DungeonRoom:EventGraph"},"type_id":"Utilities|IsValid","pos":{"x":700,"y":778}}` → `K2Node_MacroInstance_24`.
  2. 핀 index는 입력 `exec` 0, `InputObject` 1(`Object Reference`), 출력 `Is Valid` 0, `Is Not Valid` 1이다.
  3. PT 스크립트 한 번에 다음을 했다.
     - `break_pins`(Delay then 0 → Branch execute 0)
     - `connect_pins`(Delay then → IsValid exec 0)
     - `connect_pins`(IsValid `Is Valid` 0 → Branch execute 0)
     - `connect_pins`(GetPlayerPawn ReturnValue 0 → IsValid InputObject 1)
  4. `get_node_infos`로 연결을 확인했다. GetPlayerPawn 출력 하나가 IsValid와 IsOverlappingActor 두 곳에 이어진다.
  5. `compile_blueprint {"warnings_as_errors":true}` → null, `[Compiler]` 로그 0건.
- `arrange_nodes`(get_connected_subgraph 결과)는 exec 줄을 계단식으로 내려 놓았다(겹침은 없음). 그래서 `set_node_position`으로 exec 5개를 한 줄(y 688, x 0/400/752/1104/1408)에, 순수 노드를 그 아래(y 864~1184)에 두었다.
- Git Bash에서 로그 패턴 `\[Compiler\]`를 `echo '...'`로 JSON 파일에 쓰면 백슬래시가 줄어 `Invalid \escape` 에러가 난다. 인자 파일은 `python -c "import json;json.dump({...,'pattern':r'\[Compiler\]'},open(f,'w'))"`로 만든다. 여러 줄 heredoc 여러 개를 한 Bash 호출에 이어 붙였을 때도 셸 파싱이 깨졌다. 긴 한국어 조각은 파일로 먼저 쓰고 `cat >>`한다.

### 스폰 직후 잠깐 뜨는 배너 잡기

- `StartPIE {"options":{"bSimulate":false,"playMode":"PlayMode_InViewPort","warmupSeconds":0.5}}` 바로 뒤에 작은 PT 스크립트를 부른다.
  - 스크립트 내용: PC ref를 직접 지정(`.../UEDPIE_0_L_Dungeon_01.L_Dungeon_01:PersistentLevel.BP_SCPlayerController_C_0`) → `HUD` → `RoomBanner` → `visibility`와 `WidgetTree_0.TitleText.text`.
  - 결과: `HitTestInvisible`과 '시련의 회랑'을 잡았다. 1초 뒤에는 Collapsed였다.
  - warmup 2초에 폴링 20여 개면 배너(3초)가 이미 사라진 뒤라 글자만 남는다.
- Bash에서 PT 결과의 한글이 깨져 보이면 `--out` 파일로 받아 utf-8로 읽는다(`PYTHONIOENCODING=utf-8`).

### 위젯 CDO 포커스 플래그 (B4)

- `OT list_properties {"instance":{"refPath":"/Game/SoulCombat/UI/WBP_DungeonEntry.WBP_DungeonEntry"}}`(약 10 KB)에 `bIsFocusable`(boolean)이 있다.
- 다음 순서로 고쳤다.
  1. `OT set_properties {..., "values":"{\"bIsFocusable\":true}"}` → true, `get_properties`로 true 확인.
  2. `UMGToolSet CompileWidgetBlueprint` → true.
  3. `BT compile_blueprint {"warnings_as_errors":true}` → null.
  4. `AT save_assets ["/Game/SoulCombat/UI/WBP_DungeonEntry"]`.
- PIE에서 만들어진 위젯 인스턴스(`/Engine/Transient...WBP_DungeonEntry_C_0`)도 `bIsFocusable` true로 읽혔고, UIOnly 포커스 에러가 사라졌다.

### 레벨 적 인스턴스 어그로 범위 (B5)

- 인스턴스 편집 변수라 레벨 액터에 바로 넣는다. `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/Maps/L_CombatField.L_CombatField:PersistentLevel.BP_Enemy_Grunt_C_0"},"values":"{\"AggroRange\":800}"}` → true.
  - 두 번째 액터(`_C_1`)는 따로 부른다.
  - 라벨은 `AcT get_label`로 확인한다. `_C_0` = SparringGrunt_1, `_C_1` = SparringGrunt_2.
- AI(Think)는 거리를 잡몹의 **현재 위치**에서 잰다. 잡몹은 집으로 돌아가지 않으므로, 플레이어가 한 번 끌고 오면 그 자리에서 다시 추적할 수 있다.
- 확인: PIE에서 `AbilitySystemInspectorToolset GetAttributeValues`로 Health를 읽었다. `AcT set_actor_transform`으로 플레이어를 복귀점과 스파링 구역에 옮겨, 추적하지 않는 경우와 여전히 공격하는 경우를 둘 다 봤다.

## 9단계 주석 패스: 방 로직과 던전 게임 모드 (에디터 B)

대상은 BP_DungeonRoom(그래프 6), BP_Room_Mob(1), BP_Room_Event(5), BP_Room_Boss(2), BP_DungeonGameMode(1)다. 그래프 15개에 주석 박스 41개를 붙였다. BP_Room_Start는 건너뛰었다(ConstructionScript가 진입 노드와 부모 호출뿐이고 EventGraph는 비어 있음).
절차는 `docs/comment-pass-recipe.md` 그대로 하고, 모든 도구 호출에 `--port 8001`을 줬다. `graph_layout.py`는 `--port`가 **서브명령 앞**(`python Tools/graph_layout.py --port 8001 dump ...`)이고, `graph_comments.py`는 **서브명령 뒤**(`ui-run ... --port 8001`)다.

### 함정: 워터마크 밑에 노드가 있으면 ui-run 보정 붙여넣기가 안 된다

- 증상: `ui-run`이 `get_node_infos ... K2Node_Knot_Cal is not valid EdGraphNode`로 멈춘다. 그래프에는 아무것도 붙지 않았다(다시 덤프해 노드 수 그대로 확인).
- 원인: 에디터 B의 BP 창은 1672×914로 작다. 그래서 그래프를 1:1로 열면 `BLUEPRINT` 워터마크 밑에 노드(Return Node)가 깔린다. 오른쪽 클릭이 노드 컨텍스트 메뉴로 가서 노드만 선택되고, 그 뒤 Ctrl+V는 무시됐다. 로직은 바뀌지 않았다(same-logic 모두 same).
- 우회: 포커스 앵커를 그래프 패널 오른쪽 위의 줌 글자 `text "Zoom 1:1"`로 바꿨다. `graph_comments.py`는 고치지 않고, 스크래치 폴더에 래퍼를 두어 `open_graph`만 바꿔 끼웠다.
  ```python
  # C:/Project/SoulCombat_B/_agent_tmp/cp/gc_zoom.py (사용: python gc_zoom.py ui-run ... --port 8001 --fit-all)
  import re, sys
  sys.path.insert(0, r"<repo>/Tools"); import graph_comments as gc
  _orig = gc.open_graph
  def open_graph(window, graph, port):
      _orig(window, graph, port)   # 탭 열기(워터마크 확인은 그대로)
      tree = gc.mcp(gc.SI, "Snapshot", {"ref": window, "maxDepth": 40}, port)
      refs = re.findall(r'text "Zoom[^"]*" \[.*?\] \[ref=(\w+)\]', tree)
      assert len(refs) == 1, refs
      return refs[0]
  gc.open_graph = open_graph; sys.argv[0] = "graph_comments.py"; sys.exit(gc.main())
  ```
  결과: 그래프 15개 모두 `knot_ok: true`, `mismatch: []`, `comments_pasted` = spec 박스 수였다.
  수동으로 확인할 때는 `graph_comments.py ui-calib <graph_ref> <Zoom text ref> --port 8001` → `{"L": [...]}`처럼 앵커만 바꿔 넣으면 된다.
- 제안: 도구에 `--anchor zoom` 옵션을 넣으면 래퍼가 필요 없다.

### 함정: --fit-all 없이 찍으면 1:1 화면이 찍힌다

- 첫 그래프(GetSCPlayerController)를 `--fit-all` 없이 찍었더니 `Zoom 1:1` 그대로였다. 선택이 빈 상태의 Home이 뷰를 움직이지 않았고, 주석 제목도 잘렸다.
- `ui-shot <graph_ref> <png> --window <w> --port 8001 --fit-all`로 다시 찍었다(Ctrl+A → Home → 3초 → 선택 해제). 이후에는 `ui-run`에 처음부터 `--fit-all`을 줬다.

### 행 사이가 좁을 때: layout 결과를 y로 밀기

- 함수 헤더 박스 안에 안쪽 박스를 세로로 쌓으면, 제목 3줄짜리 박스끼리 16~32 겹치거나 딱 붙었다(`boxes i and j overlap`, 또는 한 박스 아래 = 다음 박스 위).
- `--breaks`는 가로 간격만 벌린다. 그래서 layout JSON의 `pos`와 `rects`에서 y ≥ Y(필요하면 x 범위 제한)인 노드를 +64~128 옮긴 뒤 preview를 다시 돌렸다. 값은 `docs/comment-specs/breaks.json`에 적었다.
- 순수 노드도 같은 행 기준으로 함께 옮겨진다. same-logic은 위치만 바뀌므로 모두 same이었다.

### 그 밖에

- `compile_blueprint`의 `blueprint`는 오브젝트 경로(`/Game/.../BP_X.BP_X`)여야 한다. 패키지 경로만 주면 `is not a valid object path`로 실패한다.
- 에디터 B에서 `EditorAppToolset`의 긴 이름은 `EditorToolset.EditorAppToolset`이다(`OpenEditorForAsset`, `GetOpenAssets`).
- BP 창 ref는 에셋을 열 때마다 새로 생겼다(w54 → w60 → w63 → w68 → w71). 에디터 A의 w116처럼 고정되지 않으므로, 열 때마다 `Snapshot {"ref":"","maxDepth":1}`로 확인한다.
- Assign 노드가 있는 그래프(Room_Mob, Room_Event, Room_Boss, DungeonGameMode의 EventGraph)는 `read_graph_dsl`을 쓰지 않았다. 덤프(get_node_infos)로만 읽었고, 스트레이 `*_Event_N`은 생기지 않았다(전후 노드 수가 같음).

## 9단계 주석 패스: UI 위젯 블루프린트 (에디터 B)

대상은 /Game/SoulCombat/UI의 위젯 BP 9개다. 그래프 34개에 주석 박스 40개를 붙였다. 절차는 `docs/comment-pass-recipe.md`와 위 절(방 로직)과 같다. 모든 도구 호출에 `--port 8001`을 줬다.
건너뛴 그래프: 노드가 0개인 EventGraph(WBP_BossHealthBar, WBP_InteractPrompt, WBP_PlayerHUD), 디스패처 시그니처 그래프(WBP_DungeonEntry OnConfirmed·OnCancelled, WBP_DungeonClear OnReturnRequested, 진입 노드 1개).

### 위젯 BP는 Graph 모드로 바꿔야 하고, 워터마크 글자가 다르다

- `EditorToolset.EditorAppToolset OpenEditorForAsset {"assetPath":"/Game/SoulCombat/UI/WBP_X"}`로 열면 매번 Designer 모드다. 스냅샷(`Snapshot {"ref":"<창>","maxDepth":40}`)에 `checkbox "Graph" [unchecked] [ref=cbNN]`이 있으면 `Click {"ref":"cbNN"}` → `[checked]`가 된다. 그다음에야 `tab "My Blueprint"`, `listitem "<함수>"`, `tab "EventGraph"`가 나온다.
- Designer 모드에도 `text "Zoom -3"`(디자이너 캔버스 줌)이 있다. Graph로 바꾼 뒤에는 그래프 패널의 `Zoom` 글자 하나만 남는다.
- 그래프 워터마크가 `text "BLUEPRINT"`가 아니라 `text "WIDGET BLUEPRINT"`다. 그래서 `graph_comments.open_graph`가 `expected one BLUEPRINT watermark`로 멈춘다.
- 우회: 스크래치 래퍼 `C:/Project/SoulCombat_B/_agent_tmp/cp/gc_widget.py`. `open_graph`를 통째로 바꿔, 탭 클릭(없으면 My Blueprint 항목 더블클릭) 뒤 `Zoom` 글자 ref를 앵커로 돌려준다. 나머지(보정·붙여넣기·검증·스크린샷·클립보드 잠금)는 `graph_comments.py` 그대로다.
  ```
  python gc_widget.py ui-run <spec> /Game/SoulCombat/UI/WBP_X.WBP_X:<Graph> --window <창 ref> --layout <layout> --shot docs/screenshots/graphs/WBP_X__<Graph>.png --port 8001 --fit-all
  python gc_widget.py ui-shot /Game/SoulCombat/UI/WBP_X.WBP_X:<Graph> <png> --window <창 ref> --port 8001 --fit-all
  ```
  그래프 ref 형식은 일반 BP와 같다(`/Game/SoulCombat/UI/WBP_DungeonClear.WBP_DungeonClear:UpdateCountdownText`). `graph_layout.py dump/apply/same-logic`도 위젯 BP에 그대로 됐다.
- 결과: 그래프 34개 모두 `knot_ok: true`, `mismatch: []`, `comments_pasted` = spec 박스 수. 보정 위치 L은 대부분 (0,0)이었지만 균형추 검증으로 위치가 정확히 맞았다.
- 창 ref는 에셋마다 새로 생겼다(w74, w79, w82, w85, w88, w91, w94, w99, w102). `Snapshot {"ref":"","maxDepth":1}`의 `window "WBP_X"`에서 읽는다.
- 저장·닫기는 일반 BP와 같다: `compile_blueprint {"blueprint":{"refPath":"/Game/SoulCombat/UI/WBP_X.WBP_X"},"warnings_as_errors":true}` → null, `save_assets` → `graph_comments.py ui-close WBP_X --window <창> --port 8001`. 다시 열면 또 Designer 모드다.

### 함정: 핀이 많은 노드 밑에 순수 노드가 가려진다 (WBP_BossHealthBar ShowFor)

- `WBP_AttributeBar.Setup` 호출 노드는 구조체 드롭다운(InAttribute, InMaxAttribute)과 체크박스가 있어 실제 높이가 약 323이다. layout 추정은 246이라, 그 아래 y 288에 놓인 `GetHealthBar`가 노드 밑에 가려졌다(스크린샷에서 발견).
- 해결: 붙인 뒤 `BT set_node_position {"node":{"refPath":"/Game/SoulCombat/UI/WBP_BossHealthBar.WBP_BossHealthBar:ShowFor.K2Node_VariableGet_1"},"pos":{"x":960,"y":336}}` → `gc_widget.py ui-shot ... --fit-all`로 다시 찍었다. 새 위치도 헤더 박스 안이라 주석은 그대로 뒀다.

### 함정: 박스 폭이 그래프 패널보다 조금 넓으면 --fit-all이 1:1에 머문다 (WBP_DungeonClear UpdateCountdownText)

- 박스 폭 1440, 에디터 B 그래프 패널 폭 약 1360. Ctrl+A → Home 뒤에도 `Zoom 1:1`이어서 박스 제목 왼쪽이 잘렸다. `ui-shot`을 다시 해도 같았다.
- 붙인 주석 하나 지우기(레시피 4절 방법): 1:1 스냅샷에 제목이 `text "■ UpdateCountdownText()..." [ref=x1280]`로 나온다 → `Click {"ref":"x1280"}`(왼쪽, 주석만 선택) → `PressKey {"key":"Delete"}` → `find_nodes` 노드 수 8 그대로, 스냅샷에 `■` 0개.
- 그다음 layout JSON에서 x ≥ 800인 노드를 +320 옮겨 폭을 1760으로 넓혔다 → preview → apply → ui-run을 다시 했다. 결과는 Zoom -2로 전체가 보였다. 이동값은 `docs/comment-specs/breaks.json`에 적었다.
