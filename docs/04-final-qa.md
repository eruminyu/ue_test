# 04. SoulCombat 최종 QA

8단계 최종 점검 기록이다. 에디터 A(포트 8000) 하나로 진행했다. 두 번째 에디터 작업분을 병합한 뒤 에디터를 다시 켠 상태에서 시작했다.

**종합 판정: 통과.** `/Game/SoulCombat`의 블루프린트 72개는 에러·경고 없이 컴파일된다. 저장 안 된 에셋, `_Scratch` 의존, 맵·프로젝트 설정 불일치는 없다(1부). 플레이어 조작 10개 항목은 PIE에서 사양 수치와 태그대로 동작했다(2부). 필드 → 게이트 → 던전 5개 방 → 클리어 → 필드 복귀 흐름, 이벤트 실패, 입장 취소도 최종 맵 복제본에서 모두 통과했다. 흐름 테스트 버그 B1~B5가 고쳐진 것도 확인했다(3부). QA 중 데이터만 고친 것은 3건이다. 게이트 포털과 검기 투사체의 Nanite 끄기, 훈련 더미의 `bRunPhysicsWithNoController`이며, 그래프는 바꾸지 않았다. 남은 일은 사용자 플레이 테스트(사양 10장 완료 기준)다. 그때 볼 것은 두 가지로, 실제 키 입력에서 0.35초 간격 4콤보가 끝까지 나가는지, 넉백 거리가 타격감에 충분한지다(2-3 비고).

## 1부: 정적 점검 (컴파일, 저장 상태, 의존성, 맵 설정, 레벨 배치)

- 일시: 2026-09-29, UE 5.8.2, 에디터 A(포트 8000), MCP 툴(`mcp__unreal-mcp__call_tool`)로 진행. `Tools/mcp_http.py`는 쓰지 않았다.
- 시작 상태: 현재 레벨 `/Game/SoulCombat/Maps/L_CombatField`. `/Game/SoulCombat` 에셋 104개, 점검 전 `is_dirty` 0개.

### 1-1. 전체 블루프린트 컴파일 (warnings_as_errors)

ProgrammaticToolset 스크립트 하나로 `find_assets` → `get_asset_class`가 `_C`로 끝나는 에셋 72개를 골랐다. 부모(GA_SCBase, GA_ActionBase, AC_*, BP_CombatCharacterBase, BP_EnemyBase, BP_DungeonRoom, BP_SCGameModeBase, WBP_AttributeBar, WBP_SkillSlot)를 먼저 컴파일하고 나머지를 이어서 `compile_blueprint {"warnings_as_errors":true}`로 컴파일했다.

| 항목 | 기대 | 결과 | 판정 |
| --- | --- | --- | --- |
| GA (14) | 에러·경고 0 | GA_SCBase, GA_ActionBase, GA_HitReact, GA_Player_BasicAttack/Guard/Dash/Jump, GA_Skill_DashSlash/GroundSlam/WaveSlash, GA_Enemy_Melee, GA_Enemy_Melee_Boss, GA_Boss_Slam, GA_Boss_Charge 모두 `null`(성공) | 통과 |
| GE (19) | 에러·경고 0 | Damage, Death, DashInvuln, Regen_Player, RestoreFull, Buff_Attack, Boss_Enrage, Cost 4, Cooldown 8 모두 `null` | 통과 |
| GC (6) | 에러·경고 0 | GC_Hit, GC_Guard_Block, GC_Guard_Active, GC_Skill_GroundSlam, GC_Enemy_Slam, GC_Buff_Attack 모두 `null` | 통과 |
| 캐릭터 (7) | 에러·경고 0 | BP_CombatCharacterBase, BP_PlayerCharacter, BP_EnemyBase, BP_Enemy_Grunt, BP_Enemy_Boss, BP_TrainingDummy, BP_SealCrystal 모두 `null` | 통과 |
| 컴포넌트 (2) | 에러·경고 0 | AC_CombatComponent, AC_Interactable `null` | 통과 |
| Core (5) | 에러·경고 0 | BP_SCGameInstance, BP_SCGameModeBase, BP_FieldGameMode, BP_DungeonGameMode, BP_SCPlayerController `null` | 통과 |
| Dungeon (7) | 에러·경고 0 | BP_DungeonGate, BP_DungeonDoor, BP_DungeonRoom, BP_Room_Start/Mob/Event/Boss `null` | 통과 |
| Combat (2), AI (1) | 에러·경고 0 | BP_WaveProjectile, BP_TelegraphCircle, BP_EnemyAIController `null` | 통과 |
| UI (9) | 에러·경고 0 | WBP_AttributeBar, WBP_SkillSlot, WBP_PlayerHUD, WBP_BossHealthBar, WBP_RoomBanner, WBP_EventTimer, WBP_InteractPrompt, WBP_DungeonEntry, WBP_DungeonClear `null` | 통과 |
| 합계 | 사양 8장 BP 72개 | 72개 컴파일, 실패 0. 스크립트 중단 없음 | 통과 |
| 로그 `[Compiler]` 줄 | 에러·경고 줄 없음 | `GetLogEntries {"pattern":"\\[Compiler\\]","category":""}` 컴파일 전·후 모두 0줄 | 통과 |

### 1-2. 저장 상태 (is_dirty)

| 항목 | 기대 | 결과 | 판정 |
| --- | --- | --- | --- |
| 컴파일 전 `/Game/SoulCombat` 104개 | dirty 0 | 0 | 통과 |
| 컴파일 72개 직후 | dirty 0(생기면 경로 명시 저장) | 0. 깨끗하고 최신인 BP는 컴파일해도 dirty가 되지 않았다 | 통과 |
| 1부 끝(BP_DungeonGate 수정·저장, 두 맵 로드·읽기 뒤) | dirty 0 | 0 (L_CombatField 다시 로드 뒤 `is_dirty` false) | 통과 |

### 1-3. 의존성 (AssetTools get_dependencies, 104개 전부)

| 항목 | 기대 | 결과 | 판정 |
| --- | --- | --- | --- |
| `/Game/_Scratch` 의존 | 없음 | 0건 | 통과 |
| Characters/Mannequins | 메시·애니메이션 | `Meshes/SKM_Manny_Simple`(TrainingDummy, Grunt, Boss), `Meshes/SKM_Quinn_Simple`(PlayerCharacter), `Anims/Rifle/HitReact/MM_HitReact_Front_Lgt_01`(GA_HitReact), `Materials/Manny/MI_Manny_01_New`, `MI_Manny_02_New`(MI_SC_Boss_01/02 부모) | 통과 |
| Variant_Combat | 몽타주·ABP·NS_Damage | `Anims/AM_ComboAttack`(BasicAttack, DashSlash, WaveSlash, Enemy_Melee), `Anims/AM_ChargedAttack`(BasicAttack, Guard, GroundSlam, Boss_Slam, Boss_Charge), `Anims/ABP_Manny_Combat`(캐릭터 4종), `VFX/NS_Damage`(GC_Hit) | 통과 |
| Variant_Platforming | AM_Dash | `Anims/AM_Dash`(GA_Player_Dash, GA_Boss_Charge). IA_Dash 템플릿 의존 없음(3단계 수정 유지) | 통과 |
| LevelPrototyping | 메시·머티리얼 | `Meshes/SM_Cube`(Gate, Door, WaveProjectile, 두 맵), `SM_Plane`(Gate 포털), `SM_Cylinder`(TelegraphCircle, L_CombatField), `SM_ChamferCube`(SealCrystal), `Materials/M_FlatCol`, `M_PrototypeGrid`, `Interactable/JumpPad/Assets/Materials/M_SimpleGlow`(MI 부모), `Interactable/JumpPad/Assets/NS_JumpPad`(GC_Guard_Active, GC_Buff_Attack) | 통과 |
| Input | IA_Move, IA_MouseLook, IA_Jump, IMC_Default, IMC_MouseLook | 다섯 개 모두 BP_SCPlayerController에서만 참조 | 통과 |
| Niagara 플러그인 | 템플릿 모듈 | NS_SC_Shockwave, NS_SC_GuardSpark가 `/Niagara/Modules/...`, `/Niagara/Enums/...`, `/Niagara/DefaultAssets/...`(스프라이트·리본 머티리얼) 참조 | 통과 |
| Engine | 맵 기본 액터 | 두 맵이 `/Engine/EngineSky/*`, `WorldGridMaterial`, `S_LightError`(에디터 아이콘), L_CombatField가 `MapTemplates/SM_Template_Map_Floor` 참조. 매크로 `StandardMacros`(BP 18개) | 통과 |
| 그 밖의 템플릿 폴더(ThirdPerson 등) | 없음 | 없음 | 통과 |
| 내부 연결 표본 | 맵 → 게임 모드, 큐 → 이펙트 | L_CombatField → BP_FieldGameMode, L_Dungeon_01 → BP_DungeonGameMode, BP_Enemy_Boss → MI_SC_Boss_01/02·DA_AbilitySet_Boss·GE_Boss_Enrage, GC_Guard_Block → NS_SC_GuardSpark, GC_Skill_GroundSlam·GC_Enemy_Slam → NS_SC_Shockwave | 통과 |

### 1-4. 맵·프로젝트 설정

| 항목 | 기대 | 결과 | 판정 |
| --- | --- | --- | --- |
| L_CombatField WorldSettings DefaultGameMode | BP_FieldGameMode_C | `/Game/SoulCombat/Core/BP_FieldGameMode.BP_FieldGameMode_C` | 통과 |
| L_Dungeon_01 WorldSettings DefaultGameMode | BP_DungeonGameMode_C | `/Game/SoulCombat/Core/BP_DungeonGameMode.BP_DungeonGameMode_C` | 통과 |
| EditorStartupMap | L_CombatField | ini와 `GetSectionPropertyValues` 모두 `/Game/SoulCombat/Maps/L_CombatField.L_CombatField` | 통과 |
| GameDefaultMap | L_CombatField | 같음 | 통과 |
| GameInstanceClass | BP_SCGameInstance | `/Game/SoulCombat/Core/BP_SCGameInstance.BP_SCGameInstance_C` | 통과 |
| GlobalDefaultGameMode | BP_SCGameModeBase | `/Game/SoulCombat/Core/BP_SCGameModeBase.BP_SCGameModeBase_C` | 통과 |

### 1-5. 레벨 배치와 방 참조

현재 레벨이 dirty가 아닌 것을 확인하고 `SceneTools load_level`로 L_Dungeon_01 → L_CombatField 순서로 열었다(모달 없음, 두 맵 모두 MapCheck 0 Error 0 Warning). 액터는 `find_actors`(actor_type = 클래스)로 세고 `get_label`, `get_actor_transform`으로 확인했다. 레벨은 수정하지 않았다.

**L_CombatField** (액터 30개)

| 항목 | 기대 | 결과 | 판정 |
| --- | --- | --- | --- |
| 훈련 더미 | 3, (800, -400/0/400) | Dummy_1~3 (800,-400), (800,0), (800,400) | 통과 |
| 스파링 잡몹 | 2, (-1200, 900) 근처, 부활형 | SparringGrunt_1 (-1500,700), SparringGrunt_2 (-900,1100). 둘 다 bStartDormant false, Combat.bRespawnOnDeath true, bDestroyOnDeath false | 통과 |
| 게이트 | 1, (0,2200) Yaw -90 | DungeonGate (0,2200,20) | 통과 |
| PlayerStart | FieldStart (0,0), GateReturn | PlayerStart_FieldStart (0,0,100) 태그 FieldStart, PlayerStart_GateReturn (0,1450,100) 태그 GateReturn | 참고 |
| 던전 전용 액터 | 없음 | 방·문·봉인석·보스 0 | 통과 |

- 참고: GateReturn은 사양(0,1700)이 아니라 (0,1450)에 있다. 7b-1 기록에서 게이트 InteractSphere(반경 400, y 1650까지)가 y 1700을 덮는다고 적었으니, 그 뒤 일부러 옮긴 것으로 보고 그대로 두었다.

**L_Dungeon_01** (액터 93개)

| 항목 | 기대 | 결과 | 판정 |
| --- | --- | --- | --- |
| 방 로직 액터 | 5 | Room_Start (0,0), Room_Mob1 (2000,0), Room_Event (4200,0), Room_Mob2 (6400,0), Room_Boss (9300,0). 모두 방 중심 | 통과 |
| 문 | 8 | Door_Start_Exit 625, Door_Mob1_Entry 975, Door_Mob1_Exit 3025, Door_Event_Entry 3375, Door_Event_Exit 5025, Door_Mob2_Entry 5375, Door_Mob2_Exit 7425, Door_Boss_Entry 7775 (y 0) | 통과 |
| 문 bStartOpen | 입구 true, 출구 false, Start 출구 true | 입구 4개 true, Start 출구 true, 나머지 출구 3개 false | 통과 |
| 잡몹 | 11 (Mob1 3+2, Mob2 3+3) | Mob1_Grunt_W1_1~3, W2_1~2, Mob2_Grunt_W1_1~3, W2_1~3 | 통과 |
| 봉인석 | 3 | Event_Crystal_1~3 | 통과 |
| 보스 | 1 | Boss_Guardian (9900,0) | 통과 |
| PlayerStart | (0,0) | PlayerStart_Dungeon (0,0,100) | 통과 |
| 적 휴면 | 전부 bStartDormant true | 15개 모두 true | 통과 |

방 참조 점검: 각 방의 `EntryDoor`, `ExitDoor`, `Enemies` 원소를 `get_properties`로 읽고, 같은 레벨의 `find_actors` 결과 집합에 있는지 비교했다(없으면 stale).

| 방 | RoomIndex / bIsFinalRoom | EntryDoor | ExitDoor | Enemies (Wave) | 판정 |
| --- | --- | --- | --- | --- | --- |
| Room_Start | 0 / false | None (설계상 입구 문 없음) | Door_Start_Exit | 없음 | 통과 |
| Room_Mob1 | 1 / false | Door_Mob1_Entry | Door_Mob1_Exit | Grunt_C_0~2 (1), Grunt_C_3~4 (2) | 통과 |
| Room_Event | 2 / false | Door_Event_Entry | Door_Event_Exit | SealCrystal_C_0~2 (1) | 통과 |
| Room_Mob2 | 3 / false | Door_Mob2_Entry | Door_Mob2_Exit | Grunt_C_5~7 (1), Grunt_C_8~10 (2) | 통과 |
| Room_Boss | 4 / true | Door_Boss_Entry | None (설계상 출구 문 없음) | Boss_C_0 (1) | 통과 |

- stale 참조 0, 중복 0, 어느 방에도 속하지 않은 적 0.
- 배너 문구: Start "시련의 회랑" / "앞으로 나아가라", Mob "적을 모두 처치하라", Event "EVENT: 봉인석을 파괴하라" / "제한 시간 30초", Boss "BOSS: 수호자"로 사양 6장과 같다.

### 1-6. 로그와 수정한 데이터

| 항목 | 기대 | 결과 | 판정 |
| --- | --- | --- | --- |
| 에디터 시작 로그 경고 | 콘텐츠 경고 없음 | `LogStaticMesh: Warning: Invalid material [MI_SC_Portal] used on Nanite static mesh [SM_Plane]` 1건(L_CombatField 로드 때, BP_DungeonGate의 PortalPlane 컴포넌트) | 수정 |
| 수정 | 경고 제거 | B3(예고원)와 같은 방식으로 템플릿 메시는 그대로 두고 `BP_DungeonGate_C:PortalPlane_GEN_VARIABLE`의 `bDisallowNanite`를 false → true로 바꿈 → 컴파일(null) → 저장. 배치된 게이트 인스턴스도 true로 읽힘. L_CombatField를 다시 로드했을 때 경고 없음 | 통과 (다음 에디터 시작 때 재확인) |
| 그 밖의 경고·에러 | 무시 가능 | LogModelContextProtocol(세션 재연결), LogTemp UnifiedErrorTest(엔진 자체 테스트), LogAudioMixerWasapi(장치), LogD3D12RHI, LogLayoutService, LogJson(`list_properties` 스키마 생성 중 델리게이트 미지원) | 해당 없음 |

### 1부 결론

- 컴파일 72개 에러·경고 0, 저장 안 된 에셋 0, `_Scratch` 의존 0, 맵·프로젝트 설정 일치, 배치 수와 방 참조 모두 기대와 같다.
- 데이터 수정은 1건(BP_DungeonGate PortalPlane의 Nanite 끄기)이다.
- 확인 권장 사항은 두 가지다. GateReturn 위치(0,1450)가 사양과 다르다(의도한 이동으로 보임). Start 방의 EntryDoor와 Boss 방의 ExitDoor는 설계상 None이므로, 방 로직이 None 문을 IsValid로 거르는지는 PIE 흐름 테스트에서 확인한다.

## 2부: 플레이어 전투 PIE 테스트 (키 입력 없이 실제 입력 경로로)

- 일시: 2026-09-29, 에디터 A(포트 8000), MCP 툴만 사용.
- 테스트 맵: `/Game/SoulCombat/Maps/L_CombatField`를 `/Game/_Scratch/L_CombatTest`로 복제했다(실제 맵은 수정하지 않음). 복제 맵에서만 스파링 잡몹 2마리를 `bStartDormant true`로 바꿨다. 잡몹은 원래 깨어 있고 어그로 거리 2500 안에 플레이어가 들어오기 때문에, 그대로 두면 a~h 단계 중간에 끼어든다. 테스트 액터 `TestPlayerDriver`(0,-800,0)를 놓고 `Dummy` = Dummy_2, `Grunt` = SparringGrunt_1을 연결했다.
- 드라이버 `/Game/_Scratch/BP_TestPlayerDriver`(Actor): BeginPlay에서 2초 기다려 InitializeCombat이 끝난 뒤, 플레이어 폰의 `AC_CombatComponent`를 찾는다. 그다음 `PressInput(InputTag.X)` / `ReleaseInput(InputTag.X)`를 `BP_SCPlayerController`와 같은 방식으로 부른다. 단계 사이에는 Delay를 둔다. 기록 함수 `Rec(Label)`은 배열 변수(Labels, Times, DummyHP, Health, Mana, Stamina, PLoc, DLoc, Proj = BP_WaveProjectile 수, TagLog = 플레이어 ASC 소유 태그 문자열)에 한 줄씩 추가한다. 이벤트 리스너도 붙였다. 플레이어와 더미의 Health는 `WaitForAttributeChanged`, 플레이어 State.HitStun은 `WaitGameplayTagAddToActor`로 받아, 폴링하지 않아도 피해와 경직이 정확히 기록된다. 각 단계를 시작할 때 `ResetPos`로 플레이어를 (550,0,92) Yaw 0, Dummy_2를 원위치 (800,0) Yaw 180에 순간이동시킨다. 결과는 PIE가 끝난 뒤 `ObjectTools get_properties`로 PIE 액터의 배열을 읽었다.
- **PIE 프레임 제한**: 로그 `Bringing World ... up for play (max tick rate 3)`를 보면, 에디터가 백그라운드라 PIE가 3fps(프레임 0.333초)로 돌았다. Delay와 WaitDelay는 프레임 경계에서 끝나므로 표의 시간은 모두 약 0.33초 단위다. 수치(피해, 비용, 태그)는 프레임과 상관없이 정확하다. 입력 간격처럼 타이밍에 민감한 항목은 아래 비고를 본다.
- 두 번 실행했다. 1회차에서 더미가 한 번도 움직이지 않는 문제(아래 수정 1)와 Nanite 경고(수정 2)를 찾아 고쳤다. 표는 수정 뒤 2회차 결과다. 피해, 비용, 태그는 1회차와 2회차가 같았다.

### 2-1. 결과 (2회차, 수정 후)

| 단계 | 기대 (사양 4장) | 결과 | 판정 |
| --- | --- | --- | --- |
| a) 평타 1회 | 더미 -50 (50×1.0, DEF 0), State.Attacking | 누름 ok=true, State.Attacking. 5000→4950(-50). 더미 800→812로 밀림(넉백 200). 끝나면 Attacking 사라짐 | 통과 |
| b) 평타 4회 (간격 0.35초 지정, 실제 0.67초) | 4콤보 합 -270 (50+55+65+100), 피니시에 더미 밀림·뜸 | 2~4번째 누름은 ok=false(실행 중인 평타가 콤보 이벤트로 받음. 설계대로). 타격 -50, -55, -65, -100 = **-270**. 피니시 뒤 더미 x 838→988(z 157)→1171(z 90). 약 330cm 밀리고 약 60cm 뜸 | 통과 |
| b') 평타 6회 연타 | 4타 뒤 끝나고 새 입력은 처음부터 | 4타 합 -270. 피니시가 끝난 뒤 6번째 누름 ok=true로 새 콤보 1타(-50) | 통과 |
| c) Q 돌진 베기 | SP -20, Cooldown.Skill.1, 전방 돌진, 더미 -150 | 같은 프레임에 MP 100→80, State.Casting·State.SuperArmor·Cooldown.Skill.1. 플레이어 x 550→586→699→766(더미 캡슐에 막힘). 4360→4210(**-150**). 더미 800→1000 | 통과 |
| i) Q 쿨타임 중 재입력 (Q 뒤 약 1.7초) | 발동 안 함, SP 그대로 | ok=false. MP 90.0→90.0(같은 프레임). State.Casting 없음, Cooldown.Skill.1 유지 | 통과 |
| d) E 대지 강타 | SP -30, 더미 -200, 더미가 뜸 | MP 98.5→68.5(**-30**), Casting·SuperArmor·Cooldown.Skill.2. 4210→4010(**-200**). 더미 z 95→274→344→157→90(최고 약 +250), x 800→1232 | 통과 |
| e) R 검기 날리기 | SP -25, BP_WaveProjectile 생성, 더미 -125 | MP 87→62(**-25**), Cooldown.Skill.3. 타격 프레임부터 투사체 1개, 1초 뒤 0개(수명 0.8). 4010→3885(**-125**). 더미 800→827 | 통과 |
| f) 대시 | 스태미나 -25, 대시 중 State.Dashing·State.Invulnerable, Cooldown.Dash | SP 100→75. 누른 프레임에 Dashing, Invulnerable, Cooldown.Dash. +0.33초 둘 다 있음, +0.67초 Invulnerable만(GE 0.35초가 다음 프레임 경계에서 끝남), +1.0초 모두 없음. 플레이어 550→730(더미 앞에서 멈춤) | 통과 |
| g) 가드 누름/뗌 | 누르는 동안 State.Guard, 떼면 없음 | 누름 ok=true, State.Guard + GameplayCue.Guard.Active가 +0.33, +0.67초에 유지. ReleaseInput 같은 프레임에 둘 다 사라짐 | 통과 |
| h) 점프 | 플레이어 Z 상승 | z 92→238→274→202→92(최고 약 +182, JumpZVelocity 600 이론값 184) | 통과 |
| j-1) 잡몹 정면 공격을 가드 (2회) | 한 번에 약 5 (30×0.2×100/120), 경직 없음 | SparringGrunt_1을 (800,0) Yaw 180으로 옮기고 ActivateEnemy. 가드 유지 중 1000→995, 995→990(각 **-5**, 2.33초 간격). HitStun 이벤트 없음, State.Guard 유지, 플레이어 x 550 그대로 | 통과 |
| j-2) 가드 해제 후 피격 | 약 25 (30×100/120), State.HitStun 잠깐 | 뗀 프레임에 990→965(**-25**) + `EV +HitStun`. 다음 샘플 한 프레임에 State.HitStun이 있고 그다음 없음. 이후 공격마다 -25와 HitStun, 플레이어가 약 19cm씩 밀림 | 통과 |

### 2-2. 발견하고 고친 것

| # | 증상 | 원인 | 수정 | 재확인 |
| --- | --- | --- | --- | --- |
| 1 | 1회차에서 더미 위치가 끝까지 (800,0,92)였다. 평타 피니시(넉백 450/띄우기 350), Q(600/150), E(300/700)에 맞아도 밀리거나 뜨지 않았다. 피해는 정상 | BP_TrainingDummy는 컨트롤러가 없다(AutoPossessAI Disabled, AIControllerClass None). CharacterMovement의 `bRunPhysicsWithNoController`가 false라 이동 시뮬레이션이 돌지 않았고, PIE에서 `MovementMode`가 `MOVE_None`으로 읽혔다. 그래서 ApplyHit의 LaunchCharacter가 무시됐다. 잡몹과 보스는 AI가 빙의하므로 해당 없음 | `BP_TrainingDummy.Default__BP_TrainingDummy_C:CharMoveComp`의 `bRunPhysicsWithNoController` false → true(자식 CDO의 컴포넌트 기본값, 그래프 수정 없음) → 컴파일(warnings_as_errors, null) → 저장 | PIE에서 더미 MovementMode `MOVE_Walking`. 2회차에서 넉백과 띄우기가 모두 보였다(위 표). L_CombatField에 배치된 더미 3개도 true로 읽혔다(인스턴스 오버라이드 없음, 맵 수정 없음) |
| 2 | 1회차 R 단계에서 로그 `Invalid material [MI_SC_Portal] used on Nanite static mesh [SM_Cube]` | BP_WaveProjectile Visual(SM_Cube + 반투명 MI_SC_Portal). 1부의 게이트 포털과 같은 문제 | `BP_WaveProjectile_C:Visual_GEN_VARIABLE`의 `bDisallowNanite` true → 컴파일(null) → 저장. 템플릿 SM_Cube는 건드리지 않음 | 2회차 R 단계에서 경고 없음 |

두 수정 모두 그래프를 바꾸지 않았으므로 주석 박스는 그대로다. 수정 뒤 `/Game/SoulCombat` 104개의 `is_dirty`는 0이다.

### 2-3. 비고 (고치지 않음, 확인 권장)

- **콤보 입력 간격**: PIE가 3fps라 0.35초 간격으로 지정한 입력이 실제로는 0.67초 간격으로 들어갔고, 이때 4번 누르면 4타가 모두 나갔다. 설계상 입력 버퍼는 한 타에 하나(bool)다. 그래서 정확히 0.35초 간격으로 4번만 누르면, 3·4번째 입력이 둘 다 2타 구간(0.533~1.1초)에 들어가 3타에서 끝날 수 있다(계산상. 실측은 못 함). 사용자가 연타하면 5~6번 누르게 되므로 실제 플레이에는 문제가 없을 것으로 본다. 사용자 플레이 테스트(완료 기준 1)에서 확인한다.
- **지면 넉백 거리**: 수평 넉백만 있는 타격(띄우기 0)은 LaunchCharacter 직후 착지해 마찰(GroundFriction 8, BrakingDecelerationWalking 2048)로 멈춘다. 그래서 200cm/s는 약 12cm, 300cm/s는 약 19cm만 밀린다. 사양은 속도(cm/s)만 정하므로 설계와 다르지는 않다. 다만 타격감이 약하면 넉백 값이나 작은 띄우기를 조정한다.
- 더미가 이제 맞으면 밀려나 제자리를 벗어난다(사양 완료 기준 1 "더미가 밀려나며"와 일치). 제자리 복귀는 죽은 뒤 부활할 때만 한다.
- 가드 성공 때 넉백 30%(잡몹 300 → 90cm/s)로는 플레이어가 거의 밀리지 않았다(x 550 그대로).
- 봉인석(BP_SealCrystal)은 바꾸지 않았다. 컨트롤러가 없어 여전히 넉백되지 않는다(사양 "넉백·경직 없음"과 일치).

### 2부 결론

플레이어 조작 10개 항목(a~j)이 모두 사양 수치와 태그대로 동작했다. 더미가 넉백·띄우기에 반응하지 않던 문제와 검기 투사체 Nanite 경고, 2건을 데이터 수정으로 고쳤다. 테스트 에셋 `/Game/_Scratch/BP_TestPlayerDriver`와 `/Game/_Scratch/L_CombatTest`는 `/Game/SoulCombat`에서 참조하지 않는다.

## 3부: 게임 흐름 회귀 테스트와 PIE 스크린샷

- 일시: 2026-09-30, 에디터 A(포트 8000), MCP 툴만 사용. PIE는 에디터가 백그라운드라 3fps(`max tick rate 3`)로 돌았다.
- 테스트 도구: 다른 에디터에서 복사해 온 `/Game/_Scratch/BP_TestKiller`, `/Game/_Scratch/BP_TestGateDriver`를 이 에디터에서 `compile_blueprint {"warnings_as_errors":true}`로 한 번씩 다시 컴파일했다(둘 다 `null`, `[Compiler]` 줄 0). 그 뒤 경로를 지정해 저장했다. 두 BP의 의존은 `/Game/SoulCombat`의 BP뿐이다.
- 테스트 맵: **최종** 맵을 새로 복제했다.
  - `/Game/SoulCombat/Maps/L_Dungeon_01` → `/Game/_Scratch/L_DungeonFlowTest`. TestKiller를 (0,-400,50)에 두었다.
  - `L_CombatField` → `/Game/_Scratch/L_FieldFlowTest`. TestGateDriver를 (600,1200,50)에 두었다.
  - 복제 맵의 방 5개 `EntryDoor`, `ExitDoor`, `Enemies`가 모두 복제 맵 액터를 가리키는 것을 확인했다. 방마다 `InitialCheckDelay`는 0.2다(B1 수정분).
- 진행 방식은 `docs/parallel/flowtest-report.md`와 같다. 플레이어를 `ActorTools set_actor_transform`으로 방에 순간이동시키고, 상태는 ObjectTools `get_properties`와 AbilitySystemInspector로 읽었다.

### 3-1. 던전 전체 흐름 (`L_DungeonFlowTest` + TestKiller)

| # | 확인 | 기대 | 결과 | 판정 |
| --- | --- | --- | --- | --- |
| F-1 | 스폰 직후 Room_Start (B1) | 방이 바로 시작·클리어되고 시작 배너가 뜬다 | warmup 0.5초 PIE 직후 `bStarted`·`bCleared` true. 배너 TitleText '시련의 회랑', Subtitle '앞으로 나아가라'로 기본값 '방 제목'이 아니다. 첫 폴링 때는 이미 3초 표시가 끝나 Collapsed였다. 플레이어 (0,0,92), `Combat.RespawnTransform` (-350,0,100)으로 Start 방 안이다 | 통과 |
| F-2 | Room_Mob1 진입 (1300,0,100) | 웨이브 1(3) → 웨이브 2(2) → 클리어 | 다음 폴링에서 `CurrentWave` 3 / `MaxWave` 2, `AliveCount` 0, `bCleared` true. Grunt_C_0~4 모두 `bActive` true·`bIsDead` true이고, Mob2의 Grunt_C_5는 휴면 그대로다. Door_Mob1_Entry 닫힘, Door_Mob1_Exit 열림, 배너 '클리어' | 통과 |
| F-3 | Room_Event 진입 (3700,0,100), 킬러 있음 | 봉인석 3개 파괴 → 성공 보상 | `bEventDone`·`bCleared` true, `DestroyedCount` 3 / `TotalCrystals` 3, 봉인석 3개 `bIsDead` true. 배너 '성공!', HUD `EventTimer` Collapsed. 플레이어 이펙트에 `GE_Buff_Attack`(남은 약 50초)이 있고 AttackPower 50 → 65(+30%), HP 1000, SP 100. Door_Event_Entry 닫힘, Door_Event_Exit 열림 | 통과 |
| F-4 | Room_Mob2 진입 (5700,0,100) | 웨이브 1(3) → 웨이브 2(3) → 클리어 | `CurrentWave` 3, `AliveCount` 0, `bCleared` true. 적 6개가 모두 죽어 사라졌다(`bDestroyOnDeath`, `Enemies` 원소가 None으로 읽힘). 남은 적은 휴면 보스 하나다. Door_Mob2_Entry 닫힘, Door_Mob2_Exit 열림 | 통과 |
| F-5 | Room_Boss 진입 (8100,0,100) | 보스 바 표시 → 보스 사망 → 바 숨김 | 같은 스크립트의 첫 읽기에서 HUD `BossBar` HitTestInvisible(표시), `CurrentBoss` = Boss_C_0. 바로 다음 읽기에서 보스가 죽었고 `bCleared` true, `BossBar` Collapsed. Door_Boss_Entry 닫힘 | 통과 |
| F-6 | 클리어 창 | 약 2초 뒤 창, 클리어 시간, 카운트다운 | 보스방 진입 2.7초 뒤 `PC.ClearWidget` = `WBP_DungeonClear_C_0`, 커서 표시. TitleText 'DUNGEON CLEAR', TimeText '클리어 시간 11.3초'로 GameMode `ClearSeconds` 11.33과 같다(전체를 도는 첫 실행은 85.3초). CountdownText가 1초 간격으로 '3초 후 필드로 돌아갑니다' → '2초 …' → '1초 …'로 바뀌었다(`CountdownSeconds` 5) | 통과 |
| F-7 | 카운트다운 뒤 복귀 | L_CombatField#GateReturn | 로그 `Browse: /Game/SoulCombat/Maps/L_CombatField#GateReturn`, `LoadMap` 0.08초. PIE 월드 `UEDPIE_0_L_CombatField`, GameMode `BP_FieldGameMode_C_0`. 플레이어 (0,1450,92) Yaw -90으로 GateReturn과 정확히 같다. 새 HUD `WBP_PlayerHUD_C_1`, ClearWidget·EntryWidget None, 커서 숨김 | 통과 |
| F-8 | 복귀 직후 스파링 잡몹 (B5) | 공격하지 않는다 | 복귀 직후와 약 10초 뒤 모두 플레이어 HP 1000, 위치 (0,1450) 그대로. SparringGrunt 두 마리는 `AggroRange` 800, `bActive` true이고 (-1500,700), (-900,1100) 제자리에 있다 | 통과 |
| F-L | PIE 로그 (B2) | 봉인석이 맞을 때 `spine_03` 소켓 경고가 없다 | `Creating play world package` 뒤 `spine_03` 0줄. 콘텐츠 Error·Warning 0줄. 남은 줄은 모두 도구 잡음이다(3-5 참고) | 통과 |

### 3-2. 이벤트 방 실패 (`L_DungeonFlowTest`, 킬러를 뺀 상태)

킬러 인스턴스의 `Interval`은 인스턴스 편집이 안 됐다(`could not be set: Interval`). 그래서 액터를 `remove_from_scene`으로 뺐고, 테스트가 끝난 뒤 같은 위치에 다시 넣고(`BP_TestKiller_C_1`) 맵을 저장했다.

| # | 확인 | 기대 | 결과 | 판정 |
| --- | --- | --- | --- | --- |
| E-1 | 진입 직후 (3700,0,100) | 방 시작, 문 닫힘, 봉인석 활성, 배너·타이머 표시 | `bStarted` true, `bCleared` false. 입구·출구 닫힘. 봉인석 3개 `bActive` true·`bHidden` false. 배너 'EVENT: 봉인석을 파괴하라' / '제한 시간 30초' 표시. `EventTimer` 표시, ObjectiveText '봉인석을 파괴하라', TimeText '남은 시간 27.7초', ProgressText '봉인석 0 / 3' | 통과 |
| E-2 | 30초가 지난 뒤 | 실패, 봉인석 휴면, 보상 없음, 출구 열림 | 타이머가 '남은 시간 11.0초', '9.3초'로 줄어든 뒤 `bEventDone`·`bCleared` true, `DestroyedCount` 0. 봉인석 3개 `bActive` false·`bHidden` true(`bIsDead` false). 배너 '실패' / '봉인석이 사라졌다', `EventTimer` Collapsed. Door_Event_Exit 열림, 입구는 닫힘. 이펙트는 GE_Regen_Player 하나뿐이고 AttackPower 50 | 통과 |
| E-3 | 이어서 보스방 (킬러 없음) | 보스 활성, 보스 바 표시 | `bStarted` true, `bCleared` false. 보스 `bActive` true, HP 6000/6000. `BossBar` 표시, BossNameText '수호자'. 입구 닫힘. 보스가 연속 베기, 내려찍기, 돌진을 썼다(보스 태그 `Cooldown.Enemy.Attack.2`, 이펙트 `GE_Cooldown_Boss_Slam`, 플레이어 HP 1000 → 605) | 통과 |
| E-L | PIE 로그 (B3) | 예고원 Nanite 반투명 경고가 없다 | 보스가 내려찍기를 쓴 뒤에도 `Nanite`가 들어간 줄 0, `MI_SC_Telegraph` 0. 콘텐츠 Error·Warning 0줄 | 통과 |

### 3-3. 필드 → 던전 입장과 취소 (`L_FieldFlowTest` + TestGateDriver, Mode 0)

| # | 확인 | 기대 | 결과 | 판정 |
| --- | --- | --- | --- | --- |
| G-1 | 드라이버 진행 | Step 3 | `Step` 3, `Gate` = BP_DungeonGate_C_0, `SeenInteractable` = `BP_DungeonGate_C_0.Interactable`. InteractSphere 겹침 → SetInteractable이 동작했다는 뜻이다 | 통과 |
| G-2 | 게이트 열림 → 포털 → 입장 창 | 창과 커서 표시 | 게이트 `bIsOpen`·`bEntryOpen` true, PortalPlane `bHiddenInGame` false·`bVisible` true. `PC.EntryWidget` = `WBP_DungeonEntry_C_0`(`bIsFocusable` true), 커서 표시. 글자 '시련의 회랑', '다섯 개의 방을 돌파하고 수호자를 쓰러뜨려라.', 'Start → Mob → Event → Mob → Boss', '입장', '취소' | 통과 |
| G-3 | 포커스 에러 (B4) | `Non-Focusable widget` 에러가 없다 | 에디터 로그 전체에서 `Non-Focusable` 0줄. 이 PIE의 Error·Warning 0줄 | 통과 |
| G-4 | '입장' 누르기 | L_Dungeon_01 로드 | SlateInspector `Snapshot {"ref":"sp4"}`에서 찾은 `button "입장"`(ref b58)을 `Click` 한 번 하자 눌렸다. 흐름 테스트 때 필요했던 `PressKey Enter`는 필요 없었다(B4 수정으로 창이 포커스를 받음). 로그 `Browse: /Game/SoulCombat/Maps/L_Dungeon_01`, GameMode `BP_DungeonGameMode_C_0`, 플레이어 (0,0,92), EntryWidget None, 커서 숨김, 새 HUD. 진짜 L_Dungeon_01에서도 Room_Start `bStarted`·`bCleared` true, 배너 TitleText '시련의 회랑'(B1) | 통과 |
| G-5 | 취소 (새 PIE) | 창이 닫히고 게이트 앞으로 밀려난다 | `button "취소"`(b61)를 `Click` 한 번 → `EntryWidget` None, 커서 숨김, 게이트 `bEntryOpen` false·`bIsOpen` true. 플레이어 (0,1900,92)로 게이트 (0,2200) 앞 300이다. HP 1000, 잡몹 두 마리는 제자리(B5) | 통과 |
| G-L | PIE 로그 | Error·Warning 없음 | 두 PIE 모두 도구 잡음까지 포함해 0줄 | 통과 |

### 3-4. PIE 스크린샷

- 찍는 방법: SlateInspector `Screenshot {"ref":"sp4"}`로 레벨 뷰포트 영역을 찍었다. 크기는 2016×928이고, 위쪽에 뷰포트 툴바 한 줄이 들어간다. `CaptureViewport`는 에디터 월드를 찍으므로 쓰지 않았다.
- 저장 방법: base64는 컨텍스트에 넣지 않았다. ProgrammaticToolset 스크립트 안에서 `AssetTools write_file`로 `SoulCombat/Saved/QA/*.b64.txt`에 쓰고, 로컬 Python으로 PNG로 풀었다. 임시 파일은 지웠다.

| 파일 | 장면 | 화면 설명 | 판정 |
| --- | --- | --- | --- |
| `docs/screenshots/pie_field_hud.png` | `L_CombatTest` PIE. BP_TestPlayerDriver가 E(대지 강타) 뒤 R(검기)을 쓴 직후 | 플레이어가 더미 3개 중 가운데 더미(Dummy_2) 바로 앞에서 공격 중이다. 더미 3개 모두 머리 위에 빨간 체력 바가 있고, 가운데 더미의 바는 줄어 있다. 가운데에 검기 투사체(흰 상자)와 대지 강타 큐의 위로 솟는 화살 이펙트가 보인다. 왼쪽 아래 HUD는 HP 1000/1000(빨강), SP 67/100(파랑, 줄어 있음), ST 100/100(노랑)이다. 아래 가운데 스킬 슬롯 4개(Shift 대시, Q 돌진 베기, E 대지 강타, R 검기) 중 E에 '3.7', R에 '5.3' 쿨타임 숫자와 어두운 오버레이가 있다. 같은 순간 플레이어 태그는 `Cooldown.Skill.2`, `Cooldown.Skill.3`이었다 | 통과 |
| `docs/screenshots/pie_dungeon_boss.png` | `L_DungeonFlowTest` PIE(킬러 없음), 보스방 | 벽과 격자 바닥으로 된 보스방 안이다. 붉은 대형 마네킹 '수호자'(크기 1.5배)가 플레이어(Quinn) 바로 앞에서 공격 자세를 잡고 있다. 위쪽 가운데에 보스 바 '수호자' 6000/6000이 넓게 떠 있다. 바닥 앞쪽이 붉게 물든 것은 내려찍기 예고원이다. HUD는 HP 605/1000, SP·ST 100/100이고 스킬 슬롯은 모두 사용 가능하다. 앞의 두 장은 카메라가 보스 몸에 파묻히거나 내려찍기 폭발 이펙트에 가려서 다시 찍었다. 보스를 (9000,0), 플레이어를 (8300,0)으로 옮긴 뒤 연속으로 찍은 것 중 한 장이다 | 통과 |
| `docs/screenshots/pie_entry_window.png` | `L_FieldFlowTest` PIE. TestGateDriver가 플레이어를 포털에 넣은 직후 | 화면 전체가 어둡게 덮이고 가운데에 반투명 남색 패널이 있다. 패널에는 제목 '시련의 회랑', 설명 '다섯 개의 방을 돌파하고 수호자를 쓰러뜨려라.', 하늘색 흐름 'Start → Mob → Event → Mob → Boss', 회색 버튼 '입장'·'취소'가 있다. 뒤로 게이트 기둥, 포털 앞의 플레이어, 어둡게 가려진 HUD(HP 1000/1000, SP·ST 100/100, 스킬 슬롯)가 보인다 | 통과 |

### 3-5. PIE 로그 정리

PIE 여섯 번(던전 킬러 있음 2회, 킬러 없음 1회, 필드 2회, 전투 테스트 맵 1회)마다 `Creating play world package` 줄 뒤를 모아 Error·Warning을 분류했다.

| 분류 | 내용 | 판단 |
| --- | --- | --- |
| B2 `GetSocketInfoByName(spine_03)` | 0줄 | 수정 확인 |
| B3 `Invalid material [MI_SC_Telegraph] … Nanite` | 0줄(다른 Nanite 경고도 0) | 수정 확인 |
| B4 `Attempting to focus Non-Focusable widget` | 0줄 | 수정 확인 |
| `LogUtils: Error: The Editor is currently in a play mode.` + `LevelEditorSubsystem: Error: GetCurrentLevel …` | PIE 중 `set_actor_transform`을 부를 때마다 한 쌍 | 도구 잡음 |
| `LogScript: Warning: … is not valid Object for property 'instance'`, `LogUObjectGlobals: Warning: Failed to find object …` | 죽어서 사라진 적이나 레벨 이동 전의 PIE 경로를 내 호출이 읽음 | 도구 잡음 |
| `LogScript: Warning: Unsupported file extension ".b64"` | `write_file` 확장자 시험 | 도구 잡음 |
| `LogAudioMixer`, `LogAudioMixerWasapi` Warning·Error | 오디오 장치 제거·교체(`PostDeviceSwap - null device swap result`) | 환경(장치) |
| 그 밖의 콘텐츠 Error·Warning | 없음 | 통과 |

### 3-6. 마무리 상태

- PIE는 꺼져 있고, 현재 레벨은 `/Game/SoulCombat/Maps/L_CombatField`다.
- `/Game/SoulCombat` 104개 `is_dirty` 0. `/Game/_Scratch` 7개(BP_TestGateDriver, BP_TestKiller, BP_TestPlayerDriver, L_Smoke, L_CombatTest, L_DungeonFlowTest, L_FieldFlowTest)도 `is_dirty` 0.
- 3부에서는 `/Game/SoulCombat` 에셋과 진짜 맵을 하나도 바꾸지 않았다.

### 3부 결론

흐름 테스트 보고서의 시나리오를 최종 맵 복제본에서 다시 돌렸고, 모든 항목이 통과했다. 버그 B1(시작 방이 시작되지 않음), B2(봉인석 소켓 경고), B3(예고원 Nanite 경고), B4(입장 창 포커스 에러), B5(스파링 잡몹 추격)가 모두 고쳐진 것을 확인했다. B4 수정 덕분에 '입장'·'취소' 버튼이 SlateInspector `Click` 한 번으로 눌린다. 스크린샷 3장은 HUD, 보스전, 입장 창을 사양대로 보여 준다.

## 콤보 입력 큐 수정

- 일시: 2026-09-30, 에디터 A(포트 8000), MCP 툴만 사용. 대상 `/Game/SoulCombat/GAS/Abilities/GA_Player_BasicAttack`.
- 문제(2-3 비고): 입력 버퍼가 bool 하나(`bInputBuffered`)라 한 타에 입력을 하나만 기억했고, `BeginStepTimers`가 다음 타를 시작할 때 그 값을 지웠다. 그래서 현재 타의 연결 시점 전에 두 번째 입력이 오면 사라졌고, 빠른 4연타가 3타에서 끝날 수 있었다.

### 바꾼 것 (국소 수정, 나머지 로직 동일)

| 위치 | 전 | 후 |
| --- | --- | --- |
| 변수 | `bInputBuffered`(bool) | `QueuedInputs`(int, Combo\|State, 기본 0), `MaxQueuedInputs`(int, Combo, 인스턴스 편집, 기본 **3**). `bInputBuffered`는 쓰는 노드를 모두 지운 뒤 변수도 삭제 |
| ActivateAbility | ComboStep = 1 → WaitGameplayEvent | ComboStep = 1 → **QueuedInputs = 0** → WaitGameplayEvent |
| 입력 처리(EventMagnitude > 0.5) | 연결 시점 지남 → AdvanceStep, 아니면 bInputBuffered = true | 연결 시점 지남 → AdvanceStep(그대로), 아니면 **QueuedInputs = Min(QueuedInputs + 1, MaxQueuedInputs)** |
| BeginStepTimers | bInputBuffered = false, bPastChainPoint = false | bPastChainPoint = false만. **큐는 비우지 않는다** |
| 연결 시점(ChainTime WaitDelay 뒤) | bPastChainPoint = true → bInputBuffered면 AdvanceStep | bPastChainPoint = true → **QueuedInputs > 0이면 QueuedInputs - 1 → AdvanceStep** |

- 덤프 비교(`graph_layout.py dump` 전후): 노드 106 → 113(추가 10, 삭제 3). 바뀐 연결은 위 표의 7곳, 옮긴 노드는 연결 시점의 AdvanceStep 하나(같은 박스 안에서 아래로)뿐이다. 새 노드는 모두 기존 블록 박스 안에 넣었고 스크린샷으로 겹침이 없음을 확인했다.
- 주석: '입력 버퍼' 박스와 '단계 상태 초기화' 박스가 bInputBuffered를 설명하고 있어 틀리게 됐으므로 두 개만 같은 좌표·크기로 다시 붙였다(‘■ 입력 버퍼 (큐)’, ‘bPastChainPoint = false. 쌓인 입력(QueuedInputs)은 비우지 않는다.’). 다른 박스(입력 대기, 콤보 연결 시점 등)는 여전히 맞아서 그대로 뒀다. 주석 수 15개 그대로.
- 컴파일(warnings_as_errors) null, `[Compiler]` 로그 0줄, 저장 뒤 `/Game/SoulCombat` 미저장 0.
- **MaxQueuedInputs를 2가 아니라 3으로 한 이유**: 첫 누름은 `PressInput`에서 이벤트를 보낸 **뒤에** 어빌리티를 활성화하므로 콤보 입력으로 들어가지 않는다. 그래서 4연타가 모두 1타 연결 시점(0.533초) 전에 오면 쌓아야 할 입력은 3개다. 최대 2면 1타 → 2타 → 3타에서 끝난다. 3이면 남은 타 수(2~4타)와 같아 더 쌓여도 4타를 넘지 않는다(4타에서는 연결 시점 타이머가 없고 AdvanceStep도 ComboStep ≥ 4면 무시). 줄이고 싶으면 인스턴스 편집 값으로 바꾼다.

### PIE 결과 (`/Game/_Scratch/L_CombatTest`, 드라이버 `BP_TestPlayerDriver`)

드라이버에 시나리오 이벤트 `ComboQA`~`ComboQF`, `ComboQEnd`와 bool `ComboQueueTest`(기본 true, false면 원래 A~J 시나리오)를 추가했다. 시나리오마다 ResetPos → 0.8초 → 누름 → 4.5초 뒤 기록. 더미 HP는 `WaitForAttributeChanged` 이벤트로 타격마다 기록했다. 이번에도 에디터가 백그라운드라 PIE가 3fps였다(Delay 0.1초는 실제 0.33초).

| 시나리오 | 기대 | 결과 (더미 HP 변화) | 판정 |
| --- | --- | --- | --- |
| QA: 같은 프레임에 4번 누름(가장 빠른 연타, 모두 1타 연결 시점 전) | 4타, 합 -270, 끝남 | 누름 ok = true, false, false, false. -50(+0.67초), -55(+1.33), -65(+2.0), -100(+3.0) = **-270**. 끝에 State.Attacking 없음 | 통과 (이전 구조에서는 3타에서 끝나던 경우) |
| QB: 0.1초 간격 4번(실제 0.33초) | 4타 -270 | 2·3번째 누름이 1타 연결 시점 전후에 들어옴. -50, -55, -65, -100 = **-270**, 끝남 | 통과 |
| QC: 0.35초 간격 4번(실제 0.33~0.67초) | 4타 -270 | -50, -55, -65, -100 = **-270**, 끝남 | 통과 |
| QD: 1번 | 1타 -50 | -50 한 번, 끝남(2타로 넘어가지 않음) | 통과 |
| QE: 0.1초 간격 8번(실제 약 2.3초에 걸침) | 4타에서 끝남 | -50, -55, -65, -100 = **-270**. 8번째 누름은 피니시 중(무시). 끝에 State.Attacking 없음 | 통과 |
| QF: 같은 프레임에 8번 | 4타에서 끝남(무한 콤보 없음) | 큐는 3에서 멈춤. -50, -55, -65, -100 = **-270**, 끝남 | 통과 |

- ComboStep이 4까지 간 것은 4번째 타격이 -100(계수 2.0, 4타 전용)인 것으로 확인했다.
- 런타임 에러(`Accessed None`, `Blueprint Runtime Error`) 0줄. 테스트 뒤 PIE 종료, 현재 레벨을 L_CombatField로 되돌렸다. 테스트 에셋은 `/Game/_Scratch`에만 있다.
- 남은 확인: 3fps라 0.1초 단위 입력 간격은 검증하지 못했다. 같은 프레임 연타(QA, QF)가 가장 가혹한 경우라 큐 동작 자체는 확인됐다. 실제 손 입력 느낌은 사용자 플레이 테스트에서 본다.
