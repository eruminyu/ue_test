# 01. SoulCombat 게임 사양

소울워커식 스킬 전투 프로토타입이다. 전투의 중심 축은 **스킬 시스템**(평타를 끊고 들어가는 스킬, 스킬 사이 연계, 대시로 모든 행동 캔슬)이고, GAS로 만든다. 레벨은 전투 테스트 필드 하나와 던전 하나다.

## 1. 원칙

- **C++는 GAS에 꼭 필요한 것만.** `USCAttributeSet`(속성 세트, BP로 못 만듦)과 `USCAbilitySet`(GA/GE 클래스 목록을 담는 데이터 에셋, BP 변수로는 클래스 배열을 MCP로 만들 수 없어서)뿐이다. 나머지는 전부 BP.
- **모듈화.** 전투 기능(타깃 찾기, 피해 적용, 가드 판정, 사망)은 액터 컴포넌트(`AC_CombatComponent`)에 모아 플레이어, 몬스터, 보스, 파괴 오브젝트, 투사체가 같이 쓴다. 어빌리티는 부모 GA(`GA_SCBase`, `GA_ActionBase`)의 공통 흐름을 상속한다. UI는 재사용 위젯(속성 바, 스킬 슬롯)을 조립한다. BP 사이 통신은 이벤트 디스패처, 게임플레이 이벤트, 게임플레이 태그로 한다.
- **데이터 주도.** 캐릭터별 스탯은 DataTable, 부여할 어빌리티는 `SCAbilitySet` 데이터 에셋, 어빌리티 수치는 GA의 인스턴스 편집 가능 변수(자식 GA에서 기본값만 바꿈)에 둔다.
- **템플릿 에셋 재사용.** 캐릭터 메시, 애니메이션, 몽타주, 레벨 프로토타이핑 메시는 템플릿 것을 참조만 한다(수정 금지).
- 모든 새 에셋은 `/Game/SoulCombat` 아래에 이 문서의 이름 그대로 만든다.

## 2. 조작

| 입력 | 동작 | 어빌리티 / 처리 |
| --- | --- | --- |
| W A S D | 이동 (카메라 기준) | 플레이어 컨트롤러 |
| 마우스 | 카메라 회전 | 플레이어 컨트롤러 |
| 좌클릭 | 기본 공격 4콤보 | `GA_Player_BasicAttack` |
| 우클릭 (누르고 있는 동안) | 가드 | `GA_Player_Guard` |
| Left Shift | 대시 (무적) | `GA_Player_Dash` |
| Space | 점프 | `GA_Player_Jump` |
| Q | 스킬 1 돌진 베기 | `GA_Skill_DashSlash` |
| E | 스킬 2 대지 강타 | `GA_Skill_GroundSlam` |
| R | 스킬 3 검기 날리기 | `GA_Skill_WaveSlash` |
| F | 상호작용 (게이트 열기) | `AC_Interactable` |

입력 흐름: `IMC_SoulCombat` → `BP_SCPlayerController`의 Enhanced Input 이벤트 → 폰의 `AC_CombatComponent.PressInput(InputTag)` / `ReleaseInput(InputTag)` → 태그에 묶인 어빌리티 핸들로 `TryActivateAbility`. 누를 때와 뗄 때 모두 같은 InputTag로 게임플레이 이벤트를 보낸다(EventMagnitude 1 = 누름, 0 = 뗌). 실행 중인 어빌리티는 이 이벤트로 콤보 입력을 받거나(평타) 버튼 떼기를 감지한다(가드).

## 3. 캔슬과 차단 규칙 (소울워커식)

우선순위: **대시 > 스킬 > 가드 > 기본 공격**.

| 어빌리티 | Asset Tags | Cancel Abilities With Tag | Activation Blocked Tags | Activation Owned Tags |
| --- | --- | --- | --- | --- |
| 기본 공격 | Ability.Attack.Basic | - | State.Dead, State.HitStun, State.Casting, State.Guard, State.Dashing | State.Attacking |
| 가드 | Ability.Guard | Ability.Attack.Basic | State.Dead, State.HitStun, State.Casting, State.Dashing | State.Guard |
| 대시 | Ability.Dash | Ability.Attack.Basic, Ability.Skill, Ability.Guard, Ability.HitReact | State.Dead | State.Dashing (무적 0.35초는 GE_DashInvuln) |
| 점프 | Ability.Jump | Ability.Attack.Basic | State.Dead, State.HitStun, State.Casting, State.Guard | - |
| 스킬 1~3 | Ability.Skill.* | Ability.Attack.Basic, Ability.Guard, Ability.Skill | State.Dead, State.HitStun, State.Dashing | State.Casting, State.SuperArmor (스킬 중 경직 없음) |
| 피격 경직 | Ability.HitReact | Ability.Attack.Basic, Ability.Enemy.Attack, Ability.Guard | State.Dead, State.SuperArmor, State.Invulnerable | State.HitStun |
| 몬스터 공격 | Ability.Enemy.Attack.* | - | State.Dead, State.HitStun | State.Attacking |

- 스킬은 평타와 다른 스킬을 끊고 바로 나간다(스킬 연계). 연타 남용은 쿨타임과 SP가 막는다.
- 대시는 피격 경직 중에도 쓸 수 있다(회피 탈출).
- 기본 공격, 스킬, 경직, 대시, 가드 중에는 이동 입력이 막힌다(`AC_CombatComponent.CanMove`). 가드는 제자리에서 버틴다.

## 4. 수치

### 스탯 (DataTable, 행 구조체 AttributeMetaData, 행 이름 `SCAttributeSet.<속성>`)

| 테이블 | Health/MaxHealth | Mana/MaxMana (SP) | Stamina/MaxStamina | AttackPower | Defense |
| --- | --- | --- | --- | --- | --- |
| DT_Attr_Player | 1000 | 100 | 100 | 50 | 20 |
| DT_Attr_Grunt | 400 | 0 | 0 | 30 | 0 |
| DT_Attr_Boss | 6000 | 0 | 0 | 60 | 30 |
| DT_Attr_Dummy | 5000 | 0 | 0 | 0 | 0 |
| DT_Attr_Crystal | 500 | 0 | 0 | 0 | 0 |

받는 데미지 = 공격력 × 계수 × 100 / (100 + 방어력). 가드 성공 시 계수 × 0.2.

플레이어 자원 회복(`GE_Regen_Player`, Infinite, Period 0.1초): SP +0.5 (초당 5), 스태미나 +2 (초당 20).

### 플레이어 어빌리티

| 어빌리티 | 비용 | 쿨타임 | 계수 | 판정 | 넉백 / 띄우기 (cm/s) | 애니메이션 |
| --- | --- | --- | --- | --- | --- | --- |
| 기본 공격 1타 | - | - | 1.0 | 반경 160, 전방 120 | 200 / 0 | AM_ComboAttack `Melee01` |
| 기본 공격 2타 | - | - | 1.1 | 반경 160, 전방 120 | 200 / 0 | AM_ComboAttack `Melee02` |
| 기본 공격 3타 | - | - | 1.3 | 반경 170, 전방 130 | 250 / 0 | AM_ComboAttack `Melee03` |
| 기본 공격 4타 (피니시) | - | - | 2.0 | 반경 220, 전방 120 | 450 / 350 | AM_ChargedAttack `Attack` |
| 가드 | - | - | - | 전방 120도 안의 공격을 계수 0.2로 줄임, 경직 없음, 넉백 30% | - | AM_ChargedAttack `Charge` 초반 자세에서 멈춤 + GameplayCue.Guard.Active |
| 대시 | 스태미나 25 | 0.3초 | - | 무적 0.35초 (`GE_DashInvuln`) | - | AM_Dash (루트 모션, 재생 속도 1.3), 입력 방향으로 회전 후. 0.55초에 종료 |
| 점프 | - | - | - | - | - | 캐릭터 Jump, 착지하면 종료 |
| Q 돌진 베기 | SP 20 | 5초 | 3.0 | 전방으로 돌진(1800) 후 반경 250, 전방 100 | 600 / 150 | AM_ComboAttack `Melee03` |
| E 대지 강타 | SP 30 | 8초 | 4.0 | 자기 중심 반경 450 | 300 / 700 (공중에 뜸) | AM_ChargedAttack `Attack` + GameplayCue.Skill.GroundSlam |
| R 검기 날리기 | SP 25 | 6초 | 2.5 (적마다 1회) | 투사체 `BP_WaveProjectile` 속도 2000, 수명 0.8초, 관통, 반경 120 | 400 / 0 | AM_ComboAttack `Melee02` |

- 콤보: 각 타의 **콤보 입력 구간**에 좌클릭이 들어오면 **연결 시점**에 다음 타로 넘어간다. 입력이 없으면 그 타가 끝나고 어빌리티가 끝난다. 4타 뒤에는 처음으로 돌아가지 않고 끝난다.
- 각 타의 시작 시 이동 입력이 있으면 그 방향으로 몸을 돌린다(`AC_CombatComponent.DesiredFacing`).
- 타격 시점과 연결 시점은 GA 변수 배열로 두고 `WaitDelay`로 맞춘다. 값은 템플릿 몽타주의 노티파이 시간(엔진 노트 D1a)이다: 타격 Melee01 0.467, Melee02 0.467, Melee03 0.40, 피니시 0.367초 / 연결 Melee01 0.533, Melee02 0.567초(섹션 시작 기준). 1~3타는 몽타주 하나의 섹션 점프, 4타는 몽타주 교체.

### 몬스터

| 몬스터 | 스탯 | 행동 | 비고 |
| --- | --- | --- | --- |
| 잡몹 `BP_Enemy_Grunt` | DT_Attr_Grunt | 근접 베기(`GA_Enemy_Melee`): 사거리 180, 선딜 0.45초, 반경 130 전방 110, 계수 1.0, 넉백 300, 쿨타임 2초 | 이동 속도 350, 어그로 거리 2500 |
| 보스 `BP_Enemy_Boss` (수호자) | DT_Attr_Boss | 1) 연속 베기(`GA_Enemy_Melee` 보스 설정): 사거리 260, 계수 1.2, 쿨타임 2.5초 2) 내려찍기(`GA_Boss_Slam`): 사거리 600, 바닥 예고원 1.2초 후 반경 500, 계수 2.5, 띄우기 600, 쿨타임 8초 3) 돌진(`GA_Boss_Charge`): 사거리 1500, 선딜 0.5초 후 돌진 2500, 경로 반경 200, 계수 1.8, 쿨타임 10초 | 크기 1.5배, State.SuperArmor(경직 없음), HP 50% 이하에서 분노(`GE_Boss_Enrage`: 공격력 ×1.3, 한 번) |
| 훈련 더미 `BP_TrainingDummy` | DT_Attr_Dummy | 없음 | 필드 전용. 죽으면 3초 뒤 제자리 부활 |
| 봉인석 `BP_SealCrystal` | DT_Attr_Crystal | 없음 | 이벤트 방 전용. 넉백·경직 없음 |

몬스터 AI(`BP_EnemyAIController`): 0.2초마다 생각한다. 대상(플레이어)이 어그로 거리 안이면 쫓아가고(직접 이동 입력, 내비메시 불필요), 행동 목록을 우선순위대로 보며 사거리 안이고 쿨타임이 아닌 첫 행동을 발동한다. 경직, 공격 중, 사망, 비활성 상태면 아무것도 안 한다.

## 5. 피해 처리 흐름

`AC_CombatComponent.ApplyHit(Target, Coefficient, Knockback, Launch)` (어빌리티와 투사체가 같이 쓴다):

1. 대상이 `State.Guard`이고 공격자가 대상 전방 120도 안에 있으면 가드 성공: 계수 × 0.2, 대상에게 `Event.Guard.Blocked`, 큐 `GameplayCue.Guard.Block`, 경직 없음, 넉백 30%.
2. `GE_Damage` 스펙에 SetByCaller `Data.Damage` = 공격력 × 계수를 넣어 대상에게 적용. `GameplayCue.Hit` 재생.
3. 가드 실패면 대상에게 `Event.HitReact`(Payload: Instigator = 공격자, EventMagnitude = 넉백). 대상의 `GA_HitReact`가 경직(`GE_HitStun` 0.4초), 넉백, 피격 모션을 처리. `State.SuperArmor`면 발동하지 않는다.
4. 대상 선정(`AC_CombatComponent.FindTargets`): Pawn 스피어 오버랩 → 자기 제외 → ASC 있음 → 진영 태그가 다름(Team.Player ↔ Team.Enemy) → `State.Dead` 아님.

사망: `AC_CombatComponent`가 Health 변화를 감시하다 0 이하가 되면 `State.Dead` 부여, `GE_Death`(Cancel Abilities with Tags 컴포넌트)로 모든 어빌리티 취소, 래그돌, `OnDied` 방송. 플레이어는 3초 뒤 현재 체크포인트(필드: 시작 지점, 던전: 현재 방 입구)에서 전부 회복하고 부활. 몬스터는 3초 뒤 제거(필드의 더미와 잡몹은 제자리 부활).

## 6. 게임 흐름

### 전투 테스트 필드 `L_CombatField`

- 넓은 바닥, 하늘, 조명. 플레이어 시작점(0, 0).
- 훈련 더미 3개 (800, -400), (800, 0), (800, 400).
- 스파링 구역 (-1200, 900) 근처에 잡몹 2마리 (죽으면 5초 뒤 부활, 가드 연습용). 어그로 거리 800이라 스파링 구역에 들어가야 공격한다.
- 던전 게이트 `BP_DungeonGate` (0, 2200), 플레이어 쪽을 바라봄. 복귀용 PlayerStart(태그 `GateReturn`) (0, 1450). 게이트 상호작용 범위 밖이다.

### 게이트 → 던전 입장

1. 게이트 가까이 가면 `[F] 게이트 열기` 안내(`WBP_InteractPrompt`).
2. F를 누르면 게이트 문이 열리고(1초) 포털이 빛난다.
3. 포털에 들어가면 **던전 입장 확인 화면**(`WBP_DungeonEntry`): 던전 이름, 설명, 구성 `Start → Mob → Event → Mob → Boss`, [입장] [취소]. 화면이 떠 있는 동안 게임 입력을 막고 커서를 보인다.
4. [입장] → `BP_SCGameInstance.EnterDungeon` → `L_Dungeon_01` 로드. [취소] → 창 닫고 포털 밖으로 밀려남.

### 던전 `L_Dungeon_01` (Start - Mob - Event - Mob - Boss)

방은 +X 방향으로 일렬, 방 사이는 짧은 통로와 문(`BP_DungeonDoor`)이다. 방 로직은 `BP_DungeonRoom`(부모)과 자식 BP 4종이다. 방에 들어가면(방 트리거) 입구·출구 문이 닫히고 방 규칙이 시작되며, 클리어하면 출구 문이 열린다. 진행은 `BP_DungeonGameMode`가 관리한다.

| 순서 | 방 BP | 규칙 | 배너 |
| --- | --- | --- | --- |
| 1 | `BP_Room_Start` | 들어오면 바로 클리어. 출구 문 열림 | "시련의 회랑" / "앞으로 나아가라" |
| 2 | `BP_Room_Mob` (잡몹 1) | 웨이브 1: 잡몹 3, 웨이브 2: 잡몹 2. 모두 처치하면 클리어 | "적을 모두 처치하라" |
| 3 | `BP_Room_Event` | 30초 안에 봉인석 3개 파괴. 성공하면 보상(체력·SP 전부 회복 + `GE_Buff_Attack` 공격력 +30% 60초), 실패하면 봉인석이 사라지고 보상 없음. 어느 쪽이든 출구 열림 | "EVENT: 봉인석을 파괴하라" + 남은 시간·파괴 수(`WBP_EventTimer`) |
| 4 | `BP_Room_Mob` (잡몹 2) | 웨이브 1: 잡몹 3, 웨이브 2: 잡몹 3 | "적을 모두 처치하라" |
| 5 | `BP_Room_Boss` | 보스 1. 보스 HP 바 표시(`WBP_BossHealthBar`). 보스를 쓰러뜨리면 던전 클리어 | "BOSS: 수호자" |

몬스터는 레벨에 미리 배치된 **휴면 상태**로 있다가 방이 웨이브 순서대로 깨운다(숨김·충돌 끔 → 보이기·AI 시작). 방 BP는 몬스터 목록(레벨 액터 참조 배열)과 각 몬스터의 웨이브 번호로 진행한다.

### 던전 클리어 → 필드 복귀

보스 사망 → `WBP_DungeonClear`("DUNGEON CLEAR", 클리어 시간, 5초 카운트다운, [필드로 돌아가기]) → `BP_SCGameInstance.ReturnToField` → `L_CombatField#GateReturn` 로드(`#` 뒤가 PlayerStartTag), 플레이어는 `GateReturn` 시작점에서 스폰. 처음 필드에 들어올 때는 `BP_FieldGameMode`가 태그 `FieldStart` 시작점을 고른다.

## 7. UI

| 위젯 | 역할 | 재사용 |
| --- | --- | --- |
| `WBP_AttributeBar` | 현재값/최대값 속성 한 쌍을 스스로 읽어 그리는 바. 변수: Attribute, MaxAttribute, Label, FillColor, bShowNumbers. 함수: `BindToActor(Actor)` | HP/SP/스태미나, 몬스터 머리 위 HP, 보스 HP |
| `WBP_SkillSlot` | 키, 이름, 쿨타임 오버레이와 남은 초, SP 부족 표시. 변수: KeyLabel, SkillName, CooldownTag, Cost. 함수: `BindToActor(Actor)` | Shift, Q, E, R 슬롯 |
| `WBP_PlayerHUD` | 속성 바 3개 + 스킬 슬롯 4개 + 아래 위젯들을 배치하고 폰에 연결 | 필드, 던전 공통 |
| `WBP_BossHealthBar` | 보스 이름 + `WBP_AttributeBar`(큰 크기) | 보스 방 |
| `WBP_RoomBanner` | 화면 위쪽 큰 제목/부제, 일정 시간 뒤 사라짐 | 방 진입, 클리어 |
| `WBP_EventTimer` | 이벤트 목표와 남은 시간 | 이벤트 방 |
| `WBP_InteractPrompt` | `[F] 게이트 열기` | 상호작용 대상 |
| `WBP_DungeonEntry` | 던전 입장 확인 창. 디스패처 OnConfirmed, OnCancelled | 게이트 |
| `WBP_DungeonClear` | 클리어 결과 창. 디스패처 OnReturnRequested | 보스 방 |

UI 허브는 `BP_SCPlayerController`다. 게임 쪽 BP(게이트, 방, 게임 모드)는 컨트롤러의 공개 함수(`ShowRoomBanner`, `ShowBossBar`, `ShowEventTimer`, `ShowInteractPrompt`, `OpenDungeonEntry`, `OpenDungeonClear`)만 부르고, 위젯 내부 구조는 모른다.

## 8. 에셋 목록 (`/Game/SoulCombat`)

| 폴더 | 에셋 | 설명 |
| --- | --- | --- |
| Core | BP_SCGameInstance | 레벨 이동(EnterDungeon, ReturnToField), 복귀 플래그 |
| Core | BP_SCGameModeBase, BP_FieldGameMode, BP_DungeonGameMode | 공통 설정 / 필드(복귀 스폰) / 던전 진행 |
| Core | BP_SCPlayerController | 입력, UI 허브, 상호작용 대상 관리 |
| Components | AC_CombatComponent | ASC 초기화, 어빌리티 부여와 입력 라우팅, 대상 찾기·피해 적용·가드 판정(어빌리티와 투사체가 공용), 사망·부활, 디스패처(OnHealthChanged, OnDied, OnRespawned) |
| Components | AC_Interactable | 상호작용 대상 표시. PromptText, 디스패처 OnInteracted |
| Characters | BP_CombatCharacterBase | Character + ASC + AC_CombatComponent. 모든 전투 캐릭터의 부모 |
| Characters | BP_PlayerCharacter | 카메라, 플레이어 메시(Quinn + ABP_Manny_Combat) |
| Characters/Enemies | BP_EnemyBase, BP_Enemy_Grunt, BP_Enemy_Boss, BP_TrainingDummy, BP_SealCrystal | 몬스터 공통(휴면·활성, 머리 위 HP 바, 행동 목록) / 개별 설정 |
| AI | BP_EnemyAIController | 생각 루프, 추적, 행동 선택 |
| GAS/Abilities | GA_SCBase, GA_ActionBase, GA_HitReact, GA_Player_BasicAttack, GA_Player_Guard, GA_Player_Dash, GA_Player_Jump, GA_Skill_DashSlash, GA_Skill_GroundSlam, GA_Skill_WaveSlash, GA_Enemy_Melee, GA_Enemy_Melee_Boss, GA_Boss_Slam, GA_Boss_Charge | 3장, 4장 표. GA_ActionBase = 몽타주 하나 + 타격 시점 하나짜리 행동의 공통 부모(스킬 3종, 몬스터 근접 공격이 상속) |
| GAS/Effects | GE_Damage, GE_Death, GE_DashInvuln, GE_Regen_Player, GE_RestoreFull, GE_Buff_Attack, GE_Boss_Enrage, GE_Cost_Dash, GE_Cost_Skill1/2/3, GE_Cooldown_Dash, GE_Cooldown_Skill1/2/3, GE_Cooldown_Enemy_Melee, GE_Cooldown_Boss_Melee, GE_Cooldown_Boss_Slam, GE_Cooldown_Boss_Charge | 수치는 4장 |
| GAS/Cues | GC_Hit, GC_Guard_Block, GC_Guard_Active, GC_Skill_GroundSlam, GC_Enemy_Slam, GC_Buff_Attack | 큐 경로 `/Game/SoulCombat/GAS/Cues` (DefaultGame.ini) |
| GAS/Data | DA_AbilitySet_Player, DA_AbilitySet_Grunt, DA_AbilitySet_Boss, DA_AbilitySet_Static, DA_AbilitySet_Crystal, DT_Attr_Player, DT_Attr_Grunt, DT_Attr_Boss, DT_Attr_Dummy, DT_Attr_Crystal | Static = 더미(경직만), Crystal = 봉인석(어빌리티 없음) |
| Combat | BP_WaveProjectile, BP_TelegraphCircle | 검기 투사체 / 보스 예고원 |
| Input | IA_Attack, IA_Guard, IA_Dash, IA_Skill1, IA_Skill2, IA_Skill3, IA_Interact, IMC_SoulCombat | 2장 키. 이동·카메라·점프는 템플릿 `/Game/Input`의 IA_Move, IA_MouseLook, IA_Jump와 IMC_Default, IMC_MouseLook을 그대로 쓴다 |
| VFX | NS_SC_Shockwave, NS_SC_GuardSpark | Niagara 템플릿으로 생성 |
| UI | 7장 위젯 전부 | |
| Dungeon | BP_DungeonGate, BP_DungeonDoor, BP_DungeonRoom, BP_Room_Start, BP_Room_Mob, BP_Room_Event, BP_Room_Boss | |
| Materials | MI_SC_* | 바닥, 벽, 포털, 봉인석, 예고원, 보스 색 |
| Maps | L_CombatField, L_Dungeon_01 | 6장 |

## 9. 게임플레이 태그

`SoulCombat/Config/DefaultGameplayTags.ini`에 이미 있다. 분류: `InputTag.*`(입력·AI 행동 요청), `Ability.*`, `Cooldown.*`, `State.*`, `Event.*`, `Data.Damage`, `GameplayCue.*`, `Team.Player`, `Team.Enemy`. `State.Invulnerable`, `State.Dead`는 C++ AttributeSet이 이름으로 찾는다.

## 10. 완료 기준

1. 필드에서 좌클릭 연타로 4콤보가 이어지고, 4타에 더미가 밀려나며 머리 위 HP 바가 준다.
2. 우클릭을 누르는 동안 가드 자세가 유지되고, 잡몹의 정면 공격 피해가 20%로 줄며 경직이 없다. 떼면 풀린다.
3. Shift 대시 중에는 피해를 받지 않고, 평타·스킬·경직을 끊는다. Space로 점프한다.
4. Q, E, R이 SP를 쓰고 쿨타임 동안 HUD 슬롯에 남은 시간이 보인다. 스킬이 평타와 다른 스킬을 끊는다. E에 맞은 적이 뜬다. R 투사체가 여러 적을 관통한다.
5. 게이트에서 F → 문 열림 → 포털 → 입장 확인 화면 → 입장하면 던전이 로드된다. 취소하면 필드에 남는다.
6. 던전이 Start → Mob → Event → Mob → Boss 순서로 진행되고, 방마다 문이 닫혔다가 클리어하면 열린다. 이벤트 방은 성공과 실패가 모두 처리된다.
7. 보스를 쓰러뜨리면 클리어 화면이 뜨고 필드의 게이트 앞으로 돌아온다.
8. 모든 BP가 에러·경고 없이 컴파일되고, 그래프가 정리돼 있으며 기능 단위 한국어 주석이 달려 있다.
9. `docs/03-build-log.md`에 단계별 결과(MCP로 된 것, 우회한 것, 사람이 한 것)가 적혀 있다.
