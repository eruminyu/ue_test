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
