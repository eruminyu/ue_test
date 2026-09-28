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
- **다음: 단계 1.** 템플릿 조사.

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
| 1 | 템플릿 조사 | | | | | |
| 2 | 게임플레이 태그 24개 | | | | | |
| 3 | DT_Attr_Player, DT_Attr_Dummy | | | | | |
| 4-1 | GE_Damage (SetByCaller, 큐) | | | | | |
| 4-2 | GE 쿨타임 4종 (태그 부여 컴포넌트) | | | | | |
| 4-3 | GE_Cost 3종, GE_ManaRegen, GE_Awaken, GE_DodgeInvuln, GE_RestoreFull | | | | | |
| 4-4 | GC_Hit, GC_Slam, GC_Awaken | | | | | |
| 5-1 | AN_DemoGameplayEvent (함수 오버라이드) | | | | | |
| 5-2 | 몽타주 복제와 노티파이 추가 | | | | | |
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
