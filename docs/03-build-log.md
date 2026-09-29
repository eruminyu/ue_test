# 03. SoulCombat 제작 기록

`02-build-plan.md`의 단계를 진행하면서 채운다. 판정: **성공**(전용 MCP 툴만으로) / **우회**(다른 툴·UI 자동화·설계 변경으로) / **사람**(사용자가 에디터에서 직접) / **실패**.

## 진행 상태

- 2026-09-29 준비: 이전 ActionDemo 파일 삭제. 새 프로젝트 `SoulCombat`(UE 5.8.2) 생성: 템플릿 콘텐츠 복사(`Tools/Setup-Project.ps1`), C++ 모듈(`SCAttributeSet`, `SCAbilitySet`) 빌드 성공, 게임플레이 태그 ini 작성, 에디터 실행과 MCP 서버 자동 시작 확인. 커밋 `fa30f08`.
- 2026-09-29 MCP 기능 탐색(`docs/mcp/`, `docs/mcp-cookbook.md`)과 엔진 API 검증(`docs/engine-api-notes.md`) 진행.

## 환경

| 항목 | 값 |
| --- | --- |
| 엔진 | UE 5.8.2 (CL 56702186, 런처 설치, `C:\Program Files\Epic Games\UE_5.8`) |
| 컴파일러 | Visual Studio Community 2026 |
| 프로젝트 | `SoulCombat/SoulCombat.uproject` (Third Person BP 템플릿 콘텐츠 + Combat, Platforming 변형 팩) |
| 에디터 실행 | `-culture=en -ModelContextProtocolStartServer`, MCP `http://127.0.0.1:8000/mcp` |
| 날짜 | 2026-09-29 |

## 단계별 기록

| 단계 | 작업 | 사용한 툴 | 판정 | 사람 개입 | 메모 |
| --- | --- | --- | --- | --- | --- |
| 준비 | 프로젝트 생성, C++ 빌드, 태그, 설정 | 파일 직접 작성, UBT | 해당 없음 (MCP 불필요) | 없음 | 텍스트 파일(C++, ini)은 MCP 없이 직접 작성. 에디터 시작 시 GameFeatures 경고(에셋 매니저 GameFeatureData 항목)가 떴고, "Add entry"로 DefaultGame.ini에 추가됨 |
| 1-0 | 안 쓰는 태그 Event.Input.Released.Guard 삭제 | GameplayTagsToolset RemoveTag, ListTags | 성공 | 없음 | 뗌은 InputTag 이벤트 EventMagnitude 0으로 처리. 빈 부모 Event.Input, Event.Input.Released도 목록에서 사라짐 |
| 1-1 | DT_Attr_Player/Grunt/Boss/Dummy/Crystal (AttributeMetaData, 8행) | DataTableTools create, add_rows, set_rows, get_rows (Player는 직접, 나머지 4개는 ProgrammaticToolset) | 성공 | 없음 | 자원 0인 캐릭터는 MaxMana/MaxStamina 1, 현재값 0. get_rows로 전부 대조 |
| 1-2 | GE 19개 (Damage, Death, DashInvuln, Regen_Player, RestoreFull, Buff_Attack, Boss_Enrage, Cost 4, Cooldown 8) | BlueprintTools create, compile_blueprint(warnings_as_errors), ObjectTools set/get_properties (GE_Damage, Cooldown_Dash, Death, RestoreFull은 직접, 나머지 15개는 ProgrammaticToolset) | 성공 | 없음 | 쿨타임 GE는 TargetTags + AssetTags 컴포넌트에 같은 태그. GE_Death는 CancelAbilityTags 컴포넌트(태그 비움). 전체를 스크립트로 다시 읽어 표와 대조, 로그 경고 없음 |
| 1-3a | NS_SC_Shockwave(SimpleExplosion), NS_SC_GuardSpark(DirectionalBurst) | NiagaraToolset_System CreateNiagaraSystem, GetSystemCompileState | 성공 | 없음 | 둘 다 UpToDate, 에러·경고 없음 |
| 1-3b | 큐 6개 (Burst: GC_Hit, GC_Guard_Block, GC_Skill_GroundSlam, GC_Enemy_Slam / Looping: GC_Guard_Active, GC_Buff_Attack) | GameplayCueToolset CreateCueNotifyAsset, BlueprintTools set_parent, ObjectTools set/get_properties (GC_Hit, GC_Guard_Active는 직접, 나머지 4개는 ProgrammaticToolset) | 성공 (PIE 확인 필요) | 없음 | GC_Hit, GC_Guard_Block에 socketName spine_03. 에디터의 FindCueNotifyAssets/GetCueInfo는 새 큐를 못 찾음(목록 미갱신). 에셋 레지스트리 태그 GameplayCueName은 들어가 있음 → 8단계 PIE에서 재생 확인 |
| 1-4 | IA 7개(Boolean) + IMC_SoulCombat 매핑 7개 | DataAssetTools create, ObjectTools set/get_properties (IA 6개와 IMC 생성은 ProgrammaticToolset) | 성공 | 없음 | valueType 기본값이 Boolean. defaultKeyMappings.mappings로 LMB, RMB, LeftShift, Q, E, R, F 설정 후 다시 읽어 확인 |
| 1-5 | MI 10개 (FloorField, FloorDungeon, Wall, Door, Gate, Crystal, Portal, Telegraph, Boss_01, Boss_02) | MaterialInstanceTools list_parameters, create, set/get_vector_parameter (Door는 직접, 나머지 9개는 ProgrammaticToolset) | 성공 | 없음 | 마네킹 MI 실제 경로는 `/Game/Characters/Mannequins/Materials/Manny/` (계획서 경로에 Manny/ 빠짐). Portal/Telegraph는 발광용으로 1 초과 값 |
| 1-끝 | 저장 확인 | AssetTools save_assets(경로 명시), find_assets + is_dirty (ProgrammaticToolset) | 성공 | 없음 | /Game/SoulCombat 에셋 50개 전부 저장됨. 템플릿 에셋은 저장하지 않음 |

## 문제와 해결 기록

| 시각 | 증상 | 원인 | 해결 |
| --- | --- | --- | --- |
| 1단계 | MaterialInstanceTools list_parameters가 `MI_Manny_01_New ... is not valid MaterialInterface` | 계획서 경로에 하위 폴더 `Manny/`가 빠짐 | find_assets로 실제 경로 `/Game/Characters/Mannequins/Materials/Manny/` 확인 후 사용 |
| 1단계 | 새 GC가 FindCueNotifyAssets/GetCueInfo에 안 나옴 | 에디터 큐 매니저 목록이 새 에셋을 반영하지 않음(추정) | 에셋 레지스트리 태그 GameplayCueName 확인. 8단계 PIE에서 실제 재생 확인 예정 |
