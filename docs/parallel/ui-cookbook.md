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
