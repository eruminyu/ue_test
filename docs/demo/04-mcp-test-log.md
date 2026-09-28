# 04. MCP 테스트 기록

PC의 Claude Code 세션이 `03-mcp-build-plan.md`를 진행하면서 채운다. 판정은 성공 / Python / 부분 / 실패 중 하나다(뜻은 03 문서 참고).

## 요약 (마지막에 채움)

| 판정 | 단계 수 | 대표 예 |
| --- | --- | --- |
| 성공 | | |
| Python | | |
| 부분 | | |
| 실패 | | |

한 줄 결론:

## 진행 상태 (이어서 할 곳)

- 2026-09-28 12:05 준비 완료: BP 템플릿 `ActionDemo` 생성, `install.ps1 -Build` 성공, 변형 팩 복사, 영어 에디터 실행, MCP 서버 8000번 기동 확인.
- 2026-09-28 단계 0 완료. unreal-mcp 연결(저장소 루트 세션). Epic 스킬 플러그인 `unreal-engine-skills-for-claude-code`는 마켓플레이스에 있으나 미설치. 에디터 내장 AgentSkill `BlueprintBasicsSkill`을 읽고 진행.
- 2026-09-28 단계 1, 2 완료. 계획 변경 요약은 `docs/demo/assets.md` 맨 위.
- 2026-09-28 단계 3 완료.
- 2026-09-28 단계 4-1 ~ 4-3 완료(GE 12개).
- 2026-09-28 단계 4-4 완료(큐 3개 + NS_Demo_Slam, 큐 경로 설정).
- 2026-09-28 단계 5 완료(AN_DemoGameplayEvent, 몽타주 복제 3개).
- **다음: 단계 6-1.** GA_DemoBase 함수 5개.

## 환경

| 항목 | 값 |
| --- | --- |
| 엔진 | UE 5.8.3 (CL 58210709, Installed Build, `D:\Program Files\Epic Games\UE_5.8`) |
| 프로젝트 | Third Person / Blueprint 템플릿 + `DemoKit/install.ps1` (C++는 DemoAttributeSet 하나). 변형 팩 Combat, Platforming은 엔진 `Templates/TemplateResources/Standard`에서 복사 |
| 컴파일러 | VS Community 2026 18.10.0, MSVC 14.51.36231 (컴파일러 14.51.36257), Windows SDK 10.0.26100.0 |
| 에디터 언어 | English (`OpenEditor_EN.bat`, `-culture=en`) |
| 툴셋 수 / 툴 수 | MCP 메타 툴 3개 + 툴셋 52개. BlueprintTools는 툴 53개. 계획서가 기대한 BlueprintTools, GameplayTagsToolset, GASToolsets(Cue, AttributeSet, AbilitySystemInspector), DataTableTools, UMGToolSet, EditorAppToolset, AutomationTestToolset, ProgrammaticToolset 모두 있음. **애니메이션 몽타주, Enhanced Input, GameplayEffect 전용 툴셋은 없음** |
| Claude Code 버전, 모델 | Claude 데스크톱 앱 Code 탭(로컬 세션), claude-opus-5-5 |
| 날짜 | 2026-09-28 |

## 단계별 기록

| 단계 | 작업 | 사용한 툴 (툴셋.함수) | 판정 | 사람 개입 | 걸린 시간 | 메모 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 연결과 툴셋 확인 | list_toolsets, describe_toolset, BlueprintTools.get_graph_dsl_docs, AttributeSetToolset.ListAttributes, AgentSkillToolset.ListSkills/GetSkills, ProgrammaticToolset.get_execution_environment | 성공 | 없음 | 5분 | 에디터 영어(`-culture=en`) 확인. DemoAttributeSet 로드 확인(속성 6개: Health, MaxHealth, Mana, MaxMana, AttackPower, IncomingDamage). **ProgrammaticToolset은 `json, math, re, time, datetime, copy`만 import할 수 있고 `unreal` 모듈을 못 쓴다.** 전용 툴을 묶어 부르는 오케스트레이션만 되고, 계획서가 가정한 `unreal.*` API 직접 호출(Python 대체)은 MCP로 불가. EditorAppToolset에도 콘솔 명령(`py`) 실행 툴이 없음 |
| 1 | 템플릿 조사 | AssetTools.find_assets/list_folders/get_asset_class/get_dependencies/get_referencers/get_asset_tags, BlueprintTools.get_parent/list_graphs/read_graph_dsl/find_nodes/get_node_infos/list_functions/list_variables/list_events, ObjectTools.list_properties/get_properties, NiagaraToolset_System.GetSystemSummary/GetEmitterSummary/GetEmitterTopology 등 | 부분 | 없음 | 40분(에이전트 순차) | 결과는 `docs/demo/assets.md`. 경로, 메시, AnimBP 슬롯, 입력, 노티파이 방식, Niagara는 전용 툴로 확인. **몽타주 섹션 이름·시작 시간과 노티파이 트리거 시간은 MCP로 못 읽음**(`CompositeSections`, `Notifies` "could not be read"), 캐릭터 변수로 추정. 공격 판정이 `BPI_Attacker` 인터페이스 메시지 방식이라 단계 5-2, 5-3을 "BP_DemoPlayer가 BPI_Attacker 구현"으로 변경(변경표는 assets.md 맨 위) |
| 2 | 게임플레이 태그 24개 | GameplayTagsToolset.AddTag ×24 (ProgrammaticToolset.execute_tool_script로 묶어 호출), GameplayTagsToolset.ListTags | 성공 | 없음 | 2분 | 24개 모두 `Config/DefaultGameplayTags.ini`에 저장, ListTags로 철자 재확인(State.Invulnerable, State.Dead, Data.Damage 포함). 호출 응답이 다른 에이전트의 호출 결과와 뒤바뀌어 돌아왔지만 실제 추가는 됨(문제 기록 참고). ProgrammaticToolset은 전용 툴을 묶기만 했으므로 판정은 성공 |
| 3 | DT_Attr_Player, DT_Attr_Dummy | DataTableTools.search_row_structs/create/get_schema/add_rows/set_rows/get_rows, AssetTools.save_assets (ProgrammaticToolset로 묶음) | 성공 | 없음 | 3분 | 행 구조체 `/Script/GameplayAbilities.AttributeMetaData`(열: baseValue, minValue, maxValue, derivedAttributeInfo, bCanStack). 행 5개 `DemoAttributeSet.MaxHealth/Health/MaxMana/Mana/AttackPower`. 플레이어 500/500/100/100/20, 더미 1000/1000/0/0/0을 get_rows로 재확인 |
| 4-1 | GE_Damage (SetByCaller, 큐) | BlueprintTools.create(asset_type=부모 클래스 `/Script/GameplayAbilities.GameplayEffect`), ObjectTools.list_properties/set_properties/get_properties, BlueprintTools.compile_blueprint | 성공 | 없음 | 5분 | `create`의 `asset_type`이 곧 부모 클래스다. BP 에셋에 set_properties하면 CDO에 들어간다. 속성 이름은 lowerCamelCase(`durationPolicy`, `modifiers`, `gameplayCues`, `gEComponents`). 속성 지정 형식: `{"attributeName":"IncomingDamage","attribute":"/Script/ActionDemo.DemoAttributeSet:IncomingDamage","attributeOwner":{"refPath":"/Script/ActionDemo.DemoAttributeSet"}}`, 크기 `{"magnitudeCalculationType":"SetByCaller","setByCallerMagnitude":{"dataTag":{"tagName":"Data.Damage"}}}`. list_properties(GE)가 115KB라 파일로 떨어짐 |
| 4-2 | GE 쿨타임 4종 (태그 부여 컴포넌트) | ObjectTools.set_properties(`gEComponents`: 클래스 경로 배열) → get_properties로 서브오브젝트 refPath 획득 → 그 서브오브젝트에 set_properties, BlueprintTools.compile_blueprint (ProgrammaticToolset로 묶음) | 성공 | 없음 | 5분 | **핵심 확인 항목 통과.** 인스턴스드 서브오브젝트 배열에 `"/Script/GameplayAbilities.TargetTagsGameplayEffectComponent"`를 넣으면 `Default__GE_X_C:TargetTagsGameplayEffectComponent_0`이 생성되고, 그 `inheritableGrantedTagsContainer`에 `added`와 `combinedTags`를 함께 써서 태그 부여. 컴파일 뒤에도 유지. 0.8/4/6/15초. 런타임 동작은 단계 10에서 확인 |
| 4-3 | GE_Cost 3종, GE_ManaRegen, GE_Awaken, GE_DodgeInvuln, GE_RestoreFull | 4-2와 같음 + AssetTools.save_assets | 성공 | 없음 | 5분 | Cost: Mana AddBase -20/-30/-40. ManaRegen: Infinite, period 1, Mana +5. Awaken: 8초, AttackPower MultiplyAdditive 1.5, 큐 GameplayCue.Awaken, State.Awakened 부여. DodgeInvuln: 0.4초 State.Invulnerable. RestoreFull: Health/Mana Override, AttributeBased(MaxHealth/MaxMana, Target, 계수 1). 12개 전부 get_properties로 재확인 후 저장 |
| 4-4 | GC_Hit, GC_Slam, GC_Awaken | GameplayCueToolset.CreateCueNotifyAsset(bIsActor false/true) → BlueprintTools.set_parent(`GameplayCueNotify_Burst` / `GameplayCueNotify_Looping`) → ObjectTools.set_properties, NiagaraToolset_System.CreateNiagaraSystem/GetSystemSummary, ConfigSettingsToolset.SetSectionProperties, AssetTools.save_assets | 성공 | 없음 | 10분 | `CreateCueNotifyAsset`는 Static/Actor 기본형만 만들어서 `set_parent`로 Burst/Looping으로 바꿈(큐 태그 유지). GC_Hit = NS_Damage, GC_Slam = 새 `/Game/Demo/VFX/NS_Demo_Slam`(SimpleExplosion 템플릿 복제), GC_Awaken = NS_JumpPad(AttachToTarget, SnapToTarget, bAutoDestroyOnRemove). 에셋 태그 `GameplayCueName`은 정상. **단, GameplayCueToolset의 FindCueNotifyAssets/GetCueInfo는 새로 만든 큐를 못 찾음**(에디터 큐 라이브러리가 큐 생성 전에 초기화됨). `DefaultGame.ini`에 `GameplayCueNotifyPaths=/Game/Demo/Cues` 추가. 실제 재생은 단계 10에서 확인 |
| 5-1 | AN_DemoGameplayEvent (함수 오버라이드) | BlueprintTools.create(부모 `/Script/Engine.AnimNotify`)/add_struct_variable(`/Script/GameplayTags.GameplayTag`)/set_variable_instance_editable/add_function_graph(`Received_Notify`)/find_node_types/get_node_type_pins/write_graph_dsl/read_graph_dsl/find_nodes/compile_blueprint(warnings_as_errors), AssetTools.save_assets | 성공 | 없음 | 8분 | **함수 오버라이드 생성 확인.** `add_function_graph`에 부모 함수 이름을 주면 오버라이드 그래프가 생긴다(파라미터 MeshComp, Animation, EventReference와 bool 반환 자동). DSL에서 멤버 변수는 맨 이름으로 못 읽고 `(Variables|Default|GetEventTag)`로 읽어야 함(첫 시도 "Undefined variable"). `find_node_types`는 `context_pins: []`를 꼭 넘겨야 함(스키마상 필수). `return true` 리터럴 유지, 고아 노드 없음. read_graph_dsl은 pure 노드를 쓰인 곳마다 펼쳐 보여 줘서 GetOwner가 3번 호출되는 것처럼 보이지만 실제 노드는 1개 |
| 5-2 | 몽타주 복제와 노티파이 추가 | AssetTools.exists/duplicate/get_asset_class/get_dependencies/save_assets | 성공(복제) / 노티파이 추가는 계획 변경으로 생략 | 없음 | 3분 | `AM_ComboAttack`→`AM_Demo_Combo`, `AM_ChargedAttack`→`AM_Demo_Slam`, `AM_Dash`→`AM_Demo_Dodge`. 복제본은 원본 노티파이 BP(AN_AttackDamage, AN_AttackCombo, AN_ChargedAttack, AN_EndDash)를 그대로 참조. 노티파이 추가(5-3)는 BPI_Attacker 구현으로 대체(단계 7-3). 참고로 몽타주 `Notifies`/`CompositeSections`는 ObjectTools로 읽기·쓰기 불가이고 Python 대체도 MCP로 불가하므로, 원래 계획대로였다면 "실패". `get_dependencies`는 저장 전 새 에셋에서 에러('NoneType' object is not iterable) |
| 6-1 | GA_DemoBase 함수 5개 | | | | | |
| 6-2 | GA_Attack 콤보 그래프 | | | | | |
| 6-3 | GA_Dodge | | | | | |
| 6-4 | 스킬 3종 | | | | | |
| 7-1 | AC_DemoAbilitySystem | | | | | |
| 7-2 | 입력 에셋 (IA 5개, IMC 매핑) | | | | | |
| 7-3 | BP_DemoPlayer 컴포넌트와 기본값 | | | | | |
| 7-4 | Enhanced Input 이벤트 노드 5개 | | | | | |
| 7-5 | BP_TrainingDummy (래그돌, HP 바) | | | | | |
| 8 | WBP_DemoHUD, WBP_DummyHealth | | | | | |
| 9-1 | BP_DemoGameMode | | | | | |
| 9-2 | L_DemoArena 배치 | | | | | |
| 9-3 | 기본 맵 설정 | | | | | |
| 10-1 | 전체 컴파일 | | | | | |
| 10-2 | PIE와 스크린샷 | | | | | |
| 10-3 | GAS 인스펙터로 상태 확인 | | | | | |
| 10-4 | Python으로 어빌리티 발동 검증 | | | | | |
| 10-5 | 사용자 플레이 테스트 | | | | | |

## 문제와 해결 기록

발생 순서대로 적는다. 크래시, 모달 창, 멈춤, 잘못된 결과가 나오면 여기에 남긴다.

| 시각 | 증상 | 원인 추정 | 해결 |
| --- | --- | --- | --- |
| 11:40 | 처음 만든 프로젝트가 `D:\Project\UE\ClaudeTest\test\test.uproject`(C++ 템플릿, 저장소 밖) | 설치 문서의 이름, 위치, 유형과 다르게 생성 | 사용자와 협의해 저장소 루트에 BP 템플릿 `ActionDemo`를 새로 생성. `test`는 그대로 둠 |
| 11:58 | 엔진이 `C:\Program Files`가 아니고 HKLM `5.8` 키도 없음 | 엔진을 D 드라이브에 설치, HKCU Builds에만 GUID로 등록 | `install.ps1 -Build -EngineDir "D:\Program Files\Epic Games\UE_5.8"` |
| 12:00 | UBT 경고: MSVC 14.51.36257은 권장 버전(14.50.x)이 아님 | VS 2026 18.10의 최신 툴체인. 금지 범위는 아님 | 무시. 빌드 성공(43초) |
| 12:00 | BP 프로젝트에 `Variant_Combat`, `Variant_Platforming` 콘텐츠 없음 | BP 템플릿은 프로젝트 브라우저의 Variants 드롭다운을 골라야 변형 팩이 복사됨(기본값 없음). C++ 템플릿은 전부 포함 | 에디터를 끈 상태에서 엔진의 `Templates/TemplateResources/Standard/Variant_Combat`, `Variant_Platforming` 팩을 `Content/<팩>`, `Content/__ExternalActors__/<팩>`, `Content/__ExternalObjects__/<팩>`에 복사(프로젝트 브라우저 동작 재현). 템플릿 콘텐츠라 커밋 대상 아님 |
| 12:04 | 이 세션에 unreal-mcp가 없음(서버 목록에도 없음). 서버는 정상(`initialize` 200, 메타 툴 3개) | 세션을 저장소 밖(`D:\Project\UE\ClaudeTest`)에서 시작해 `.mcp.json`이 로드되지 않음. 세션 중 폴더 이동으로는 다시 로드되지 않음 | 저장소 루트에서 새 세션을 열어 unreal-mcp를 승인 |
| 단계 0 | ProgrammaticToolset에서 `import unreal` 불가 | 샌드박스가 `json, math, re, time, datetime, copy`만 허용. 목적이 "툴 오케스트레이션"으로 제한됨 | 계획서의 "Python 대체"(`unreal.AnimationLibrary`, IMC `map_key` 등)는 MCP로 불가. 전용 툴이 없는 작업은 ObjectTools 속성 편집이나 SlateInspectorToolset(UI 조작)으로 시도하고, 그래도 안 되면 사용자에게 요청 |
| 단계 1~2 | 조사 에이전트 3개가 병렬로 MCP를 부르는 동안 메인 세션의 `AddTag` 스크립트 호출에, 다른 에이전트가 보낸 `get_properties(AM_Dash)`의 에러가 응답으로 돌아옴 | 같은 MCP 서버(에디터 1개)에 동시 요청을 보내면 응답이 요청과 뒤섞임. 실제 AddTag는 실행됨(ListTags로 확인) | 병렬 워크플로 중단. 이후 MCP 호출은 에이전트 하나씩 순차로만 실행. **에디터 1개당 MCP 클라이언트 1개, 호출 1개씩**이 안전 |
