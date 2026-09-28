# 완료: ActionDemo MCP 블루프린트 제작 검증

계획: [plan-action-demo-mcp.md](plan-action-demo-mcp.md), 세션 진행 방식: [plan-action-demo-mcp-build.md](plan-action-demo-mcp-build.md), 단계별 기록: [demo/04-mcp-test-log.md](demo/04-mcp-test-log.md), 보고서: [demo/ActionDemo_MCP_Report.pdf](demo/ActionDemo_MCP_Report.pdf)

## 실제 변경 내용

- `ActionDemo/Content/Demo/` 아래 에셋 41개를 Unreal MCP로 생성했다. 블루프린트 28개, DataTable 2개, InputAction 5개와 IMC 1개, 몽타주 복제 3개, Niagara 1개, 맵 1개다.
- `ActionDemo/Config/DefaultGameplayTags.ini`: 게임플레이 태그 24개를 추가했다.
- `ActionDemo/Config/DefaultGame.ini`: `GameplayCueNotifyPaths=/Game/Demo/Cues`를 추가했다.
- `ActionDemo/Config/DefaultEngine.ini`: 에디터 시작 맵과 게임 기본 맵을 `L_DemoArena`로 바꿨다.
- C++는 추가하거나 수정하지 않았다(`DemoAttributeSet` 그대로).
- 문서: `docs/demo/04-mcp-test-log.md`(전 단계 판정), `docs/demo/assets.md`(템플릿 조사와 계획 변경), `docs/demo/screenshots/`, `docs/demo/report/`(보고서 원본), `docs/demo/ActionDemo_MCP_Report.pdf`.

## 계획 대비 바뀐 점

- 단계 5-2, 5-3: 몽타주 노티파이를 추가하지 않고, `BP_DemoPlayer`가 템플릿의 `BPI_Attacker`를 구현해 `Event.Hit`, `Event.Montage.ComboCheck`를 보낸다. 템플릿 노티파이가 인터페이스 메시지 방식이었고, MCP로는 몽타주 노티파이를 읽거나 쓸 수 없었다.
- 콤보는 템플릿 몽타주에 맞춰 3타(`Melee01~03`), 계수 `[1.0, 1.1, 1.8]`이다.
- 클래스 참조 변수와 파라미터를 만들 툴이 없다. 그래서 `PressAbility`는 InputTag만 받아 `TryActivateAbilitiesByTag`로 발동하고, 각 GA의 AbilityTags에 `InputTag.*`를 함께 넣었다. 시작 어빌리티와 이펙트는 `BP_DemoPlayer` BeginPlay에서 클래스 리터럴 핀으로 부여한다.

## 발견한 버그와 함정

- 같은 MCP 서버에 동시에 호출하면 응답이 다른 호출과 뒤섞인다. 호출은 한 번에 하나씩 해야 한다.
- 클래스 변수 대신 CDO 오브젝트 참조를 쓰면, 같은 세션에서 대상 BP를 재컴파일한 뒤 옛 `REINST_*` 클래스를 가리킨다(ensure 발생). 클래스 리터럴 핀으로 바꿔 해결했다.
- 읽기용 BlueprintTools(`find_node_types`, `get_node_type_pins`)만 써도 템플릿 BP가 dirty로 표시된다.
- `CaptureViewport`는 PIE 중에도 에디터 월드를 찍고 캐릭터가 구겨진 포즈로 나온다. PIE 화면은 `SlateInspectorToolset.Screenshot`으로 찍는다.
- SlateInspector의 키 입력은 PIE 게임 뷰포트에 전달되지 않는다.

## 검증 결과

- 데모 BP 28개 모두 `warnings_as_errors` 컴파일 통과.
- GAS 인스펙터: 플레이어에 어빌리티 5개, 속성 500/100/20, GE_ManaRegen 적용, 더미 HP 1000.
- 사용자 플레이: 완료 기준 1~5 모두 통과(콤보와 HP 감소, 마나 소모와 쿨타임 슬롯, 띄우기, 회피 무적, 사망 후 3초 부활). 플레이 중 런타임 오류 없음.
- 판정 집계: 성공 25(우회 포함 4), Python 0, 부분 1, 실패 1, 해당 없음 1.

## 주의사항

- 에디터를 닫을 때 저장 확인 창이 뜨면 템플릿 에셋(`/Game/ThirdPerson`, `/Game/Variant_*`)은 저장하지 않는다. 조사용 읽기 툴 때문에 dirty 표시만 된 것이다.
- Epic 스킬 플러그인 `unreal-engine-skills-for-claude-code`는 아직 설치되지 않았다. 필요하면 대화형 세션에서 `/plugin install unreal-engine-skills-for-claude-code@claude-plugins-official`을 입력한다.
- 로컬 커밋만 했다. 푸시는 하지 않았다.
