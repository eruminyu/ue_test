# 02. SoulCombat 제작 계획 (MCP)

`01-game-spec.md`의 에셋을 Unreal MCP로 만드는 순서와 에셋별 상세 설계다. MCP 사용법은 `docs/mcp-cookbook.md`, API 근거는 `docs/engine-api-notes.md`를 따른다. 각 단계가 끝나면 `03-build-log.md`에 기록하고 커밋한다.

## 0. 공통 규칙 (모든 제작 에이전트)

- MCP 호출은 한 번에 하나. MCP를 쓰는 에이전트는 동시에 하나만 돈다.
- 경로: `/Game/SoulCombat/<폴더>/<이름>`. 이름은 이 문서 그대로.
- 블루프린트 하나를 끝낼 때마다: 컴파일(에러·경고 0) → 그래프 정리(노드 배치, 기능 단위 주석 박스, 한국어 주석) → `save_assets`(경로 명시) → `read_graph_dsl`로 다시 읽어 설계와 대조.
- 변수: 카테고리 지정. 수치는 하드코딩하지 말고 변수로(인스턴스 편집 가능). 툴팁은 MCP로 못 넣으면 주석 박스로 대신한다.
- 템플릿 에셋은 참조만 한다. 수정·저장 금지.
- 태그는 `SoulCombat/Config/DefaultGameplayTags.ini`에 이미 있다. 새 태그가 필요하면 멈추고 보고한다.
- 블루프린트 클래스 변수(TSubclassOf)는 MCP로 못 만든다. 클래스가 필요하면 노드의 클래스 핀 리터럴이나 `SCAbilitySet` 데이터 에셋을 쓴다.

### 공통 표기

- `ASC` = AbilitySystemComponent, `Combat` = `AC_CombatComponent`.
- 태그 리터럴 예: `InputTag.Attack`. 속성 리터럴: `SCAttributeSet.Health` (DSL 형식은 쿡북 참고).

## 1단계: 데이터와 GAS 기초 에셋

### 1-1. 스탯 DataTable (`GAS/Data`)

행 구조체 `/Script/GameplayAbilities.AttributeMetaData`, 행 이름 `SCAttributeSet.<속성>`, 열 `baseValue`. 속성 8개(Health, MaxHealth, Mana, MaxMana, Stamina, MaxStamina, AttackPower, Defense). 값은 사양 4장 표. 자원이 0인 캐릭터도 Max 값은 1로 둔다(0 나눗셈 방지). 예: Grunt MaxMana 1, Mana 0.

### 1-2. GameplayEffect (`GAS/Effects`)

| 에셋 | Duration | 내용 |
| --- | --- | --- |
| GE_Damage | Instant | IncomingDamage Add SetByCaller(Data.Damage). GameplayCues: GameplayCue.Hit |
| GE_Death | Instant | CancelAbilityTagsGameplayEffectComponent("Cancel Abilities with Tags", 태그 비움 = 전부 취소). 사망 때 자신에게 적용 |
| GE_DashInvuln | HasDuration 0.35 | 대상에게 State.Invulnerable 부여 |
| GE_Regen_Player | Infinite, Period 0.1 | Mana Add 0.5, Stamina Add 2 |
| GE_RestoreFull | Instant | Health/Mana/Stamina Override = MaxHealth/MaxMana/MaxStamina (AttributeBased, Target, 계수 1) |
| GE_Buff_Attack | HasDuration 60 | AttackPower MultiplyAdditive 1.3. GameplayCues: GameplayCue.Buff.Attack (만료 시 자동 제거) |
| GE_Boss_Enrage | Infinite | AttackPower MultiplyAdditive 1.3 |
| GE_Cost_Dash | Instant | Stamina Add -25 |
| GE_Cost_Skill1 / 2 / 3 | Instant | Mana Add -20 / -30 / -25 |
| GE_Cooldown_Dash | 0.3 | Cooldown.Dash |
| GE_Cooldown_Skill1 / 2 / 3 | 5 / 8 / 6 | Cooldown.Skill.1 / 2 / 3 |
| GE_Cooldown_Enemy_Melee | 2.0 | Cooldown.Enemy.Attack.1 |
| GE_Cooldown_Boss_Melee | 2.5 | Cooldown.Enemy.Attack.1 |
| GE_Cooldown_Boss_Slam | 8 | Cooldown.Enemy.Attack.2 |
| GE_Cooldown_Boss_Charge | 10 | Cooldown.Enemy.Attack.3 |

- 모디파이어 연산 이름은 5.8 기준(AddBase, MultiplyAdditive, Override). 비용 GE는 반드시 Instant + AddBase + 음수 ScalableFloat(사전 비용 검사는 이 형태만 본다).
- 쿨타임·상태 태그는 TargetTagsGameplayEffectComponent("Grant Tags to Target Actor")로 부여한다. **쿨타임 GE에는 같은 태그를 AssetTagsGameplayEffectComponent에도 넣는다**(HUD가 `GetActiveEffectsWithAllTags`로 찾을 수 있게. 이 함수는 에셋 태그만 본다).
- 스크립트로 설정한 GE는 컴파일 후 저장한다(부여 태그 캐시 갱신).

### 1-3. 이펙트와 큐 (`VFX`, `GAS/Cues`)

- `VFX/NS_SC_Shockwave`: `/Niagara/DefaultAssets/Templates/Systems/SimpleExplosion`을 템플릿으로 생성(한 번 터짐).
- 큐 (부모 / 태그 / 이펙트):
  - GC_Hit: Burst / GameplayCue.Hit / `/Game/Variant_Combat/VFX/NS_Damage`. 배치 SocketName `spine_03`(없으면 발밑에 생김)
  - GC_Guard_Block: Burst / GameplayCue.Guard.Block / `/Niagara/DefaultAssets/Templates/Systems/DirectionalBurst` 복제본 `VFX/NS_SC_GuardSpark` (없으면 NS_Damage), SocketName `spine_03`
  - GC_Guard_Active: Looping(액터에 붙음) / GameplayCue.Guard.Active / `/Game/LevelPrototyping/Interactable/JumpPad/Assets/NS_JumpPad`
  - GC_Skill_GroundSlam: Burst / GameplayCue.Skill.GroundSlam / NS_SC_Shockwave
  - GC_Enemy_Slam: Burst / GameplayCue.Enemy.Slam / NS_SC_Shockwave
  - GC_Buff_Attack: Looping / GameplayCue.Buff.Attack / NS_JumpPad

### 1-4. 입력 (`Input`)

이동, 카메라, 점프는 템플릿 입력을 그대로 쓴다(`/Game/Input/IMC_Default`: IA_Move, IA_Jump / `/Game/Input/IMC_MouseLook`: IA_MouseLook). 전투 입력만 새로 만든다.

| IA (Boolean) | 키 (IMC_SoulCombat) |
| --- | --- |
| IA_Attack | LeftMouseButton |
| IA_Guard | RightMouseButton |
| IA_Dash | LeftShift |
| IA_Skill1 / IA_Skill2 / IA_Skill3 | Q / E / R |
| IA_Interact | F |

### 1-5. 머티리얼 인스턴스 (`Materials`)

| MI | 부모 | 파라미터 |
| --- | --- | --- |
| MI_SC_FloorField, MI_SC_FloorDungeon, MI_SC_Wall | `/Game/LevelPrototyping/Materials/M_PrototypeGrid` | SurfaceColor, TopSurfaceColor, GridColor, SubGridColor (Vector) |
| MI_SC_Door, MI_SC_Gate, MI_SC_Crystal(보라) | `/Game/LevelPrototyping/Materials/M_FlatCol` | `Base Color` (공백 포함) |
| MI_SC_Portal(청록), MI_SC_Telegraph(빨강) | `/Game/LevelPrototyping/Interactable/JumpPad/Assets/Materials/M_SimpleGlow` | `Color` |
| MI_SC_Boss_01, MI_SC_Boss_02 (어두운 빨강) | `/Game/Characters/Mannequins/Materials/Manny/MI_Manny_01_New`, `Manny/MI_Manny_02_New` | `Paint Tint` |

보스 메시 SKM_Manny_Simple의 머티리얼 슬롯 0에 Boss_01, 1에 Boss_02.

## 2단계: 전투 코어

### 2-1. `Components/AC_CombatComponent` (ActorComponent)

모든 전투 캐릭터가 공유하는 전투 로직. ASC는 소유 액터의 컴포넌트다.

변수
- 설정(인스턴스 편집): `AbilitySet`(SCAbilitySet), `TeamTag`(GameplayTag, 기본 Team.Enemy), `bRespawnOnDeath`(false), `bDestroyOnDeath`(false), `RespawnDelay`(3.0), `bSuperArmor`(false), `GuardDamageScale`(0.2), `GuardConeDot`(0.5)
- 상태: `ASC`(AbilitySystemComponent), `GrantedHandles`(GameplayAbilitySpecHandle 배열), `GrantedInputTags`(GameplayTag 배열), `bIsDead`, `BaseWalkSpeed`, `DesiredFacing`(Vector), `RespawnTransform`(Transform)

디스패처: `OnHealthChanged(NewValue: float, MaxValue: float)`, `OnDied(DeadActor: Actor)`, `OnRespawned(Actor: Actor)`

함수 / 이벤트
- `InitializeCombat()` (순서 중요: InitStats가 AttributeSet을 만들어야 비용 검사와 UI가 동작): ASC = Owner.GetComponentByClass(AbilitySystemComponent) → `InitStats(SCAttributeSet, AbilitySet.AttributeTable)` → Abilities마다 `Give Ability(Ability, Level=1)` 핸들과 InputTag를 배열에 추가 → StartupEffects마다 자신에게 적용 → `AddLooseGameplayTag(TeamTag)`, bSuperArmor면 State.SuperArmor → BaseWalkSpeed, RespawnTransform 저장 → `WaitForAttributeChanged(Owner, Health)` → `HandleHealthChanged`.
- `PressInput(InputTag) -> bool`: 죽었으면 false. **먼저** `SendGameplayEventToActor(Owner, InputTag, EventMagnitude=1)`, **그다음** GrantedInputTags에서 인덱스를 찾아 `TryActivateAbility(GrantedHandles[i])` 결과 반환. (순서가 반대면 방금 발동한 평타가 자기 발동 입력을 콤보 입력으로 받는다.)
- `ReleaseInput(InputTag)`: `SendGameplayEventToActor(Owner, InputTag, EventMagnitude=0)`.
- `CanMove() -> bool` (pure): State.Dead, State.Attacking, State.Casting, State.HitStun, State.Dashing, State.Guard 중 하나라도 있으면 false.
- `IsValidTarget(Target) -> bool` (pure): 자기 소유자가 아님, ASC 있음, State.Dead 없음, 대상이 내 TeamTag를 갖지 않고 Team.Player나 Team.Enemy를 가짐.
- `FindTargets(Center: Vector, Radius: float) -> Actor 배열`: SphereOverlapActors(Pawn, 소유자 제외) → IsValidTarget 필터.
- `IsBlockedByGuard(Target) -> bool`: 대상 ASC에 State.Guard, dot(대상 전방, 대상→공격자 방향) ≥ GuardConeDot.
- `ApplyHit(Target, Coefficient, Knockback, Launch) -> bool(가드됨)`:
  1. bGuarded = IsBlockedByGuard. 계수 = bGuarded ? Coefficient × GuardDamageScale : Coefficient.
  2. `ASC.MakeOutgoingSpec(GE_Damage)` → `AssignTagSetByCallerMagnitude(Data.Damage, 공격력 × 계수)` → 대상 ASC에 적용.
  3. 가드됨: 대상에게 `Event.Guard.Blocked`(Instigator = 소유자). 넉백 × 0.3만 적용.
  4. 아님: 대상에게 `Event.HitReact`(Instigator = 소유자, EventMagnitude = Knockback).
  5. 대상이 Character이고 State.SuperArmor가 없으면 `LaunchCharacter(수평 방향(대상-소유자) × 넉백 + (0,0,Launch), true, true)`.
- `HitTargetsInFront(Radius, ForwardOffset, Coefficient, Knockback, Launch) -> int`: 중심 = 소유자 위치 + 전방 × ForwardOffset, FindTargets → 각각 ApplyHit.
- `HandleHealthChanged(New, Old)`: OnHealthChanged(New, MaxHealth) 방송. New ≤ 0이고 살아 있으면 `Die`.
- `Die` (커스텀 이벤트): 이미 State.Dead면 무시 → bIsDead = true → `AddLooseGameplayTags(State.Dead)` → 자신에게 `GE_Death` 적용(모든 어빌리티 취소; ASC의 CancelAllAbilities는 BP에 없다) → OnDied 방송 → Delay(RespawnDelay) → bRespawnOnDeath면 `Respawn`, 아니고 bDestroyOnDeath면 소유자 파괴.
- `Respawn` (커스텀 이벤트): `RemoveLooseGameplayTags(State.Dead)` 한 번, GE_RestoreFull 적용, bIsDead = false, OnRespawned 방송.
- `SetRespawnTransform(T)`.

### 2-2. `Components/AC_Interactable` (ActorComponent)

변수 `PromptKey`(Text "F"), `PromptText`(Text "상호작용"), `bEnabled`(true). 디스패처 `OnInteracted(Interactor: Pawn)`. 함수 `Interact(Interactor)`: bEnabled면 방송.

### 2-3. `Characters/BP_CombatCharacterBase` (Character)

컴포넌트: `AbilitySystem`(AbilitySystemComponent), `Combat`(AC_CombatComponent). 변수 `InitialMeshTransform`(Transform).
- BeginPlay: InitialMeshTransform = Mesh 상대 트랜스폼 → `Combat.InitializeCombat` → Combat.OnDied에 `HandleDeath`, OnRespawned에 `HandleRespawn` 바인딩.
- `HandleDeath`: CharacterMovement `DisableMovement`, 캡슐 콜리전 끔, Mesh 콜리전 프로필 `Ragdoll`, `SetSimulatePhysics(true)`.
- `HandleRespawn`: Mesh 물리 끔, 캡슐에 다시 붙이고 InitialMeshTransform 복원, 프로필 `CharacterMesh`, 캡슐 콜리전 켬, `SetMovementMode(Walking)`, `Combat.RespawnTransform`으로 텔레포트.

### 2-4. 어빌리티 기반 (`GAS/Abilities`)

**GA_SCBase** (부모 GameplayAbility, **InstancingPolicy = InstancedPerActor**(기본값 PerExecution이면 연타마다 인스턴스가 겹친다), Blocked: State.Dead). 태그 프로퍼티 이름은 C++ 이름(`AbilityTags`, `ActivationOwnedTags` 등)
- `GetCombat() -> AC_CombatComponent`, `GetAvatarCharacter() -> Character`, `GetAttackPower() -> float`.
- `FaceDirection(Dir)`: 수평 성분이 있으면 아바타 Yaw를 그 방향으로.
- `FaceDesiredInput()`: Combat.DesiredFacing으로 FaceDirection.

**GA_ActionBase** (부모 GA_SCBase): 몽타주 하나 + 타격 시점 하나짜리 행동의 공통 흐름. 스킬 3종, 몬스터 근접 공격이 상속.
- 변수(인스턴스 편집): `Montage`(AnimMontage), `StartSection`(Name), `PlayRate`(1.0), `HitTime`(섹션 시작 기준 초), `Coefficient`, `Radius`, `ForwardOffset`, `Knockback`, `Launch`, `bFaceInputOnStart`(true), `LungeSpeed`(0), `LungeDuration`(0)
- ActivateAbility: CommitAbility 실패 → EndAbility. bFaceInputOnStart면 FaceDesiredInput → `OnActionStarted()` → LungeSpeed > 0이면 `ApplyRootMotionConstantForce`(전방, LungeSpeed, LungeDuration, **Additive**: 공격 애니의 루트 모션에 더해짐) → PlayMontageAndWait(Montage, PlayRate, StartSection) (Completed/BlendOut/Interrupted/Cancelled → EndAbility) → WaitDelay(HitTime / PlayRate) → `OnHitFrame()`.
- 참고: 공격·대시 애니(MM_Attack_01~03, MM_ChargedAttack, MM_Dash)는 루트 모션이 켜져 있어 재생 중 이동은 애니가 정한다. LaunchCharacter로 자신을 밀면 루트 모션에 덮인다. 그래서 돌진은 루트 모션 소스 태스크로 한다.
- `OnActionStarted()`: 기본 비어 있음 (자식이 오버라이드).
- `OnHitFrame()`: 기본 `Combat.HitTargetsInFront(Radius, ForwardOffset, Coefficient, Knockback, Launch)`.

**GA_HitReact** (부모 GA_SCBase): 트리거 GameplayEvent `Event.HitReact`. Asset Ability.HitReact, Cancel: Ability.Attack.Basic, Ability.Enemy.Attack, Ability.Guard, **ActivationOwnedTags: State.HitStun**(경직 태그는 여기서만 준다. GE로 주면 대시가 경직을 끊어도 태그가 남는다), Blocked: State.Dead, State.SuperArmor, State.Invulnerable. **bRetriggerInstancedAbility = true**(경직 중 다시 맞으면 갱신).
- Activate: CommitAbility → 아바타 메시 AnimInstance의 `PlaySlotAnimationAsDynamicMontage(MM_HitReact_Front_Lgt_01, DefaultSlot, 0.05, 0.15, 1.2)`(additive 움찔, 라이플 기준이라 PIE에서 확인) → WaitDelay 0.4 → EndAbility.

## 3단계: 플레이어

### 3-1. 플레이어 어빌리티

**GA_Player_BasicAttack** (부모 GA_SCBase). 태그는 사양 3장.
구조(엔진 노트 B1, B2, D1): 1~3타는 **AM_ComboAttack 하나를 PlayMontageAndWait로 한 번** 재생하고(StartSection `Melee01`), 다음 타는 GA 노드 **MontageJumpToSection**(`Melee02`, `Melee03`)으로 넘긴다(인터럽트 이벤트 없음). 섹션은 서로 연결돼 있지 않아 점프하지 않으면 섹션 끝(블렌드아웃 0.2초 전)에 몽타주가 끝난다. 4타는 **새 PlayMontageAndWait**(AM_ChargedAttack, `Attack`)이고, 이때 1번 태스크가 **동기로** OnInterrupted를 낸다 → `ComboStep` 가드로 무시한다.

- 변수(인스턴스 편집, 섹션 시작 기준 초, 템플릿 노티파이 시간에서 가져옴):
  - `ComboMontage` = AM_ComboAttack, `ComboSections` = [Melee01, Melee02, Melee03]
  - `FinisherMontage` = AM_ChargedAttack, `FinisherSection` = Attack
  - `StepHitTimes` = [0.467, 0.467, 0.40, 0.367] (AN_AttackDamage 시점)
  - `StepChainTimes` = [0.533, 0.567, 0.90] (1~2타는 AN_AttackCombo 시점. 상한: Melee01·02는 0.8, Melee03은 1.467 전이어야 점프가 먹는다)
  - `PlayRate` = 1.0, `StepCoefficients` = [1.0, 1.1, 1.3, 2.0], `StepRadii` = [160, 160, 170, 220], `StepOffsets` = [120, 120, 130, 120], `StepKnockbacks` = [200, 200, 250, 450], `StepLaunches` = [0, 0, 0, 350]
- 상태: `ComboStep`(1~4), `bInputBuffered`, `bPastChainPoint`.
- ActivateAbility: CommitAbility 실패 → End. ComboStep = 1 → `WaitGameplayEvent(InputTag.Attack, 반복)`: EventMagnitude > 0.5이면 bPastChainPoint면 `AdvanceStep`, 아니면 bInputBuffered = true → FaceDesiredInput → PlayMontageAndWait(ComboMontage, PlayRate, ComboSections[0]) — **모든 출력(Completed/BlendOut/Interrupted/Cancelled): ComboStep ≤ 3일 때만 EndAbility** → `BeginStepTimers`.
- `BeginStepTimers` (커스텀 이벤트): bInputBuffered = false, bPastChainPoint = false → WaitDelay(StepHitTimes[ComboStep-1] / PlayRate) → `Combat.HitTargetsInFront(반경, 오프셋, 계수, 넉백, 띄우기)`. ComboStep ≤ 3이면 따로 WaitDelay(StepChainTimes[ComboStep-1] / PlayRate) → bPastChainPoint = true → bInputBuffered면 `AdvanceStep`.
- `AdvanceStep` (커스텀 이벤트): ComboStep ≥ 4면 무시. ComboStep++ → FaceDesiredInput →
  - ComboStep ≤ 3: `MontageJumpToSection(ComboSections[ComboStep-1])` → BeginStepTimers
  - ComboStep == 4: PlayMontageAndWait(FinisherMontage, PlayRate, FinisherSection) — 모든 출력 → EndAbility → BeginStepTimers
- 이전 단계의 WaitDelay는 ChainTime > HitTime이라 다음 단계 시작 전에 끝난다. 히트스탑(CustomTimeDilation)은 WaitDelay 타이밍과 어긋나므로 넣지 않는다.

**GA_Player_Guard** (부모 GA_SCBase)
- Activate: Commit → `Add GameplayCue To Owner(GameplayCue.Guard.Active, bRemoveOnAbilityEnd=true)` → PlayMontageAndWait(AM_ChargedAttack, 1.0, `Charge`) (Charge 섹션은 자기 자신으로 연결돼 무한 루프한다. 템플릿 노티파이 'Check Charged Attack'은 우리 캐릭터가 BPI_Attacker를 구현하지 않아 무시됨) → `WaitGameplayEvent(InputTag.Guard, 반복)`: EventMagnitude < 0.5면 EndAbility. `WaitGameplayEvent(Event.Guard.Blocked, 반복)`: `Execute GameplayCue On Owner(GameplayCue.Guard.Block)`. (넉백 30%는 공격자의 ApplyHit가 준다.)
- 가드 중에는 제자리(Combat.CanMove가 State.Guard로 false).
- OnEndAbility: 몽타주 정지.

**GA_Player_Dash** (부모 GA_SCBase). Cost GE_Cost_Dash, Cooldown GE_Cooldown_Dash.
- Activate: Commit 실패 → End. 방향 = DesiredFacing, 없으면 전방 → FaceDirection → GE_DashInvuln 적용(무적 0.35초. ActivationOwnedTags에 무적을 넣으면 어빌리티 끝까지 유지돼서 안 됨) → PlayMontageAndWait(`/Game/Variant_Platforming/Anims/AM_Dash`, 1.3) (끝나면 End) → WaitDelay 0.49(= 루트 모션이 꺼지는 0.633초 / 1.3) → EndAbility. AM_Dash의 AN_EndDash는 BP_PlatformingCharacter 캐스트라 우리 캐릭터에서는 무시된다.

**GA_Player_Jump** (부모 GA_SCBase): Commit → 아바타 Character `Jump` → WaitDelay 0.1 → EndAbility. `WaitGameplayEvent(InputTag.Jump)` 뗌 이벤트는 쓰지 않는다(단순화).

**GA_Skill_DashSlash** (부모 GA_ActionBase): Montage AM_ComboAttack, Section `Melee03`, HitTime 0.40, 계수 3.0, 반경 250, 전방 100, 넉백 600, 띄우기 150, LungeSpeed 1800, LungeDuration 0.3.

**GA_Skill_GroundSlam** (부모 GA_ActionBase): AM_ChargedAttack, `Attack`, HitTime 0.367, 계수 4.0, 반경 450, 전방 0, 넉백 300, 띄우기 700. `OnHitFrame` 오버라이드: 부모 호출 + `Execute GameplayCue On Owner(GameplayCue.Skill.GroundSlam)`.

**GA_Skill_WaveSlash** (부모 GA_ActionBase): AM_ComboAttack, `Melee02`, HitTime 0.467. `OnHitFrame` 오버라이드: `BP_WaveProjectile`을 아바타 앞 100cm, 아바타 회전으로 스폰 → `Init(Combat, 2.5, 400, 0)`.

### 3-2. `Combat/BP_WaveProjectile` (Actor)

컴포넌트: `Hitbox`(Sphere 120, Overlap Pawn만), `Visual`(SM_Cube 0.2×1.6×0.8, MI_SC_Portal), `Movement`(ProjectileMovement 속도 2000, 중력 0). 변수 `SourceCombat`(AC_CombatComponent), `Coefficient`, `Knockback`, `Launch`, `Lifetime`(0.8), `HitActors`(Actor 배열).
- `Init(SourceCombat, Coefficient, Knockback, Launch)`: 저장.
- BeginPlay: SetLifeSpan(Lifetime).
- Hitbox BeginOverlap: SourceCombat 유효, 대상이 HitActors에 없고 `SourceCombat.IsValidTarget(대상)` → HitActors에 추가 → `SourceCombat.ApplyHit`.

### 3-3. 데이터 에셋 `GAS/Data/DA_AbilitySet_Player` (SCAbilitySet)

Abilities: (GA_Player_BasicAttack, InputTag.Attack), (GA_Player_Guard, InputTag.Guard), (GA_Player_Dash, InputTag.Dash), (GA_Player_Jump, InputTag.Jump), (GA_Skill_DashSlash, InputTag.Skill.1), (GA_Skill_GroundSlam, InputTag.Skill.2), (GA_Skill_WaveSlash, InputTag.Skill.3), (GA_HitReact, 없음). StartupEffects: GE_Regen_Player. AttributeTable: DT_Attr_Player.

### 3-4. `Characters/BP_PlayerCharacter` (부모 BP_CombatCharacterBase)

- 메시 `SKM_Quinn_Simple`, AnimClass `ABP_Manny_Combat_C`, 상대 위치 (0,0,-89) Yaw -90. 캡슐 35/90.
- `CameraBoom`(SpringArm 길이 450, UsePawnControlRotation, 소켓 오프셋 (0,0,60), 카메라 랙), `FollowCamera`.
- CharacterMovement: OrientRotationToMovement, RotationRate Yaw 720, MaxWalkSpeed 600, JumpZVelocity 600, AirControl 0.35. bUseControllerRotationYaw false.
- Combat: AbilitySet DA_AbilitySet_Player, TeamTag Team.Player, bRespawnOnDeath true.

### 3-5. `Core/BP_SCPlayerController` (PlayerController) - 입력 부분

- BeginPlay: 로컬이면 Enhanced Input 서브시스템에 IMC_Default(0), IMC_MouseLook(0), IMC_SoulCombat(1) 추가.
- IA_Move Triggered: 컨트롤 Yaw 기준 전방·오른쪽으로 월드 방향 계산 → Combat.DesiredFacing 갱신 → Combat.CanMove면 `AddMovementInput`. Completed → DesiredFacing = 0.
- IA_MouseLook Triggered: `AddYawInput(X)`, `AddPitchInput(Y)` (템플릿 캐릭터와 같은 부호).
- IA_Jump Started → PressInput(InputTag.Jump).
- IA_Attack Started → PressInput(InputTag.Attack).
- IA_Guard Started → PressInput(InputTag.Guard), Completed → ReleaseInput(InputTag.Guard).
- IA_Dash Started → PressInput(InputTag.Dash).
- IA_Skill1/2/3 Started → PressInput(InputTag.Skill.1/2/3).
- IA_Interact Started → CurrentInteractable 유효하면 `Interact(ControlledPawn)`.
- 헬퍼 `GetPawnCombat() -> AC_CombatComponent`.

### 3-6. `Core/BP_SCGameModeBase` (GameModeBase)

DefaultPawnClass BP_PlayerCharacter, PlayerControllerClass BP_SCPlayerController.

### 3-7. 중간 테스트용 `Maps/L_CombatField` 초안

엔진 템플릿 맵을 복제해 PlayerStart와 더미 자리를 둔다(더미는 5단계 후 배치). World Settings GameMode = BP_FieldGameMode(6단계 전에는 BP_SCGameModeBase).

## 4단계: UI (`UI`)

**WBP_AttributeBar**: 루트 SizeBox(기본 300×22) → Overlay → `Bar`(ProgressBar), HorizontalBox[`LabelText`, Spacer(Fill), `ValueText`]. 변수(인스턴스 편집): `Attribute`, `MaxAttribute`(GameplayAttribute), `Label`(Text), `FillColor`(LinearColor), `bShowNumbers`(bool). 상태 `BoundASC`.
- `Setup(Attribute, MaxAttribute, Label, FillColor, bShowNumbers)`: 변수 저장 + 표시 갱신 (부모 위젯이 인스턴스별 값을 못 넣을 때 대비).
- `BindToActor(Actor)`: BoundASC = GetAbilitySystemComponent(Actor) → `Refresh`.
- Tick: BoundASC 유효하면 `Refresh`: 현재/최대 읽어 Bar.Percent, ValueText "{0} / {1}"(정수).

**WBP_SkillSlot**: SizeBox 72×72 → Overlay → `Background`(Border), `NameText`(아래), `KeyText`(왼쪽 위), `CooldownBar`(ProgressBar, 아래→위 채움, 반투명 검정), `CooldownText`(가운데). 변수: `KeyLabel`, `SkillName`(Text), `CooldownTag`(GameplayTag), `CostAttribute`(GameplayAttribute), `Cost`(float), 상태 `BoundASC`.
- `Setup(...)`, `BindToActor(Actor)`.
- Tick: `GetActiveEffectsWithAllTags(CooldownTag)`(쿨타임 GE에 에셋 태그도 넣었으므로 찾힌다) → 첫 핸들의 `GetActiveGameplayEffectRemainingDuration` / `GetActiveGameplayEffectTotalDuration`으로 CooldownBar.Percent, CooldownText "3.2"; 없으면 숨김. Cost > 0이고 현재 자원 < Cost면 Background 색을 어둡게.

**WBP_BossHealthBar**: VerticalBox[`BossNameText`, `HealthBar`(WBP_AttributeBar 800×24)]. `ShowFor(Boss, Name)`, `HideBar()`.

**WBP_RoomBanner**: VerticalBox[`TitleText`(40pt), `SubtitleText`(20pt)]. `ShowBanner(Title, Subtitle, Duration)`: 표시 → BannerId 증가 → Delay(Duration) → Id가 같으면 숨김.

**WBP_EventTimer**: VerticalBox[`ObjectiveText`, `TimeText`, `ProgressText`]. `StartTimer(Objective, Seconds)`, `SetProgress(Text)`, `StopTimer()`. Tick: 남은 시간 "남은 시간 23.4초".

**WBP_InteractPrompt**: Border[HorizontalBox[`KeyText` "[F]", `ActionText`]]. `SetPrompt(Key, Action)`.

**WBP_DungeonEntry**: 전체 화면 반투명 Border → 가운데 VerticalBox[`TitleText`, `DescText`, `FlowText`("Start → Mob → Event → Mob → Boss"), HorizontalBox[`EnterButton`("입장"), `CancelButton`("취소")]]. 디스패처 `OnConfirmed`, `OnCancelled`. 버튼 OnClicked → 방송. `Setup(Title, Description)`.

**WBP_DungeonClear**: 전체 화면 → VerticalBox[`TitleText`("DUNGEON CLEAR"), `TimeText`, `CountdownText`, `ReturnButton`("필드로 돌아가기")]. 디스패처 `OnReturnRequested`. `Setup(ClearSeconds)`: 5초 카운트다운 → 0이 되거나 버튼을 누르면 한 번만 방송.

**WBP_PlayerHUD**: CanvasPanel.
- 왼쪽 아래 VerticalBox: `HPBar`(빨강, Health/MaxHealth), `SPBar`(파랑, Mana/MaxMana, 라벨 SP), `StaminaBar`(노랑).
- 가운데 아래 HorizontalBox: `SlotDash`(Shift, 대시, Cooldown.Dash, Stamina 25), `SlotSkill1`(Q, 돌진 베기, Cooldown.Skill.1, SP 20), `SlotSkill2`(E, 대지 강타, Cooldown.Skill.2, SP 30), `SlotSkill3`(R, 검기, Cooldown.Skill.3, SP 25).
- 위 가운데: `BossBar`(숨김), `RoomBanner`(숨김). 오른쪽 위: `EventTimer`(숨김). 가운데 아래: `InteractPrompt`(숨김).
- Construct: 각 바·슬롯 `Setup` 호출(인스턴스별 값 설정이 MCP로 되면 생략 가능).
- `BindToPawn(Pawn)`: 바 3개, 슬롯 4개 `BindToActor`.
- 공개 함수: `ShowBanner`, `ShowBossBar`, `HideBossBar`, `ShowEventTimer`, `SetEventProgress`, `HideEventTimer`, `ShowInteractPrompt`, `HideInteractPrompt`.

**BP_SCPlayerController - UI 허브 부분**
- 변수 `HUD`(WBP_PlayerHUD), `CurrentInteractable`(AC_Interactable), `EntryWidget`, `ClearWidget`, `PendingDungeonLevel`(Name).
- BeginPlay: HUD 생성·AddToViewport. OnPossess: HUD.BindToPawn.
- `SetInteractable(Interactable, bAvailable)`: 저장 + 안내 표시/숨김.
- `ShowRoomBanner(Title, Subtitle)`, `ShowBossBar(Boss, Name)`, `HideBossBar()`, `ShowEventTimer(Objective, Seconds)`, `SetEventProgress(Text)`, `HideEventTimer()`.
- `OpenDungeonEntry(Title, Description, LevelName) -> WBP_DungeonEntry`: 생성·표시, UIOnly 입력, 커서 표시, OnConfirmed → `HandleEntryConfirmed`(창 닫고 GameInstance.EnterDungeon), OnCancelled → `HandleEntryCancelled`(창 닫고 GameOnly).
- `OpenDungeonClear(ClearSeconds)`: 생성·표시, 커서 표시(GameAndUI), OnReturnRequested → GameInstance.ReturnToField.

## 5단계: 몬스터

**AI/BP_EnemyAIController** (AIController)
- 변수 `Enemy`(BP_EnemyBase), `Target`(Pawn), `ThinkInterval`(0.2), `bChasing`.
- OnPossess: Enemy 캐스트 저장 → `SetTimerByEvent(Think, ThinkInterval, 반복)`.
- `Think`: Enemy 무효·비활성·사망이면 bChasing=false. Target = 플레이어 폰(무효·사망이면 중지). 경직·공격 중이면 중지. 거리 > AggroRange면 중지. AttackTags를 순서대로: 거리가 [AttackMinRanges[i], AttackRanges[i]] 안이면 대상 쪽으로 회전 → `Combat.PressInput(AttackTags[i])`가 true면 bChasing=false로 끝. 모두 실패하면 bChasing = 거리 > 마지막 AttackRanges × 0.8.
- Tick: bChasing이고 Combat.CanMove면 대상 방향(수평) `AddMovementInput`.

**Characters/Enemies/BP_EnemyBase** (부모 BP_CombatCharacterBase)
- 컴포넌트 `OverheadBar`(WidgetComponent, WBP_AttributeBar, Screen, 120×12, Z 120).
- 변수(인스턴스 편집): `DisplayName`, `AttackTags`(GameplayTag 배열), `AttackRanges`, `AttackMinRanges`(float 배열), `AggroRange`(2500), `bStartDormant`, `Wave`(int), `bShowOverheadBar`(true). 상태 `bActive`.
- AIControllerClass BP_EnemyAIController, AutoPossessAI PlacedInWorldOrSpawned. Combat.TeamTag Team.Enemy.
- BeginPlay: 부모 호출 → OverheadBar 위젯 Setup(Health/MaxHealth) + BindToActor(self), bShowOverheadBar 반영 → bStartDormant면 `SetDormant(true)`, 아니면 bActive = true.
- `SetDormant(bDormant)`: 숨김, 콜리전, 이동(Disable/Walking), bActive = !bDormant.
- `ActivateEnemy()`: SetDormant(false).
- Combat.OnDied → OverheadBar 숨김.

**BP_Enemy_Grunt**: 메시 SKM_Manny_Simple + ABP_Manny_Combat, AbilitySet DA_AbilitySet_Grunt, AttackTags [InputTag.AI.Attack.1], Ranges [180], MinRanges [0], MaxWalkSpeed 350, bDestroyOnDeath true.

**BP_Enemy_Boss**: 크기 1.5, 머티리얼 슬롯 0/1 = MI_SC_Boss_01/02, AbilitySet DA_AbilitySet_Boss, AttackTags [AI.Attack.3(돌진), AI.Attack.2(내려찍기), AI.Attack.1(연속 베기)], Ranges [1500, 600, 260], MinRanges [500, 0, 0], bSuperArmor true, bShowOverheadBar false, DisplayName "수호자", bDestroyOnDeath false. Combat.OnHealthChanged → 50% 이하이고 분노 전이면 GE_Boss_Enrage 적용 + 배너 "수호자가 분노했다!".

**BP_TrainingDummy**: Manny 메시, AI 없음(AutoPossessAI Disabled), AbilitySet DA_AbilitySet_Static, bRespawnOnDeath true, AttackTags 없음.

**BP_SealCrystal**: 스켈레탈 메시 없음, `CrystalMesh`(SM_ChamferCube 0.8×0.8×1.6, 45도 기울임, MI_SC_Crystal), AI 없음, bSuperArmor true, AbilitySet DA_AbilitySet_Static, AttributeTable DT_Attr_Crystal(Static 세트와 테이블만 다른 `DA_AbilitySet_Crystal`), bDestroyOnDeath true, bStartDormant true.

**몬스터 어빌리티**
- `GA_Enemy_Melee` (부모 GA_ActionBase): AM_ComboAttack `Melee01`, PlayRate 0.8, HitTime 0.45, 계수 1.0, 반경 130, 전방 110, 넉백 300, bFaceInputOnStart false. Cooldown GE_Cooldown_Enemy_Melee. 태그 사양 3장.
- `GA_Enemy_Melee_Boss` (부모 GA_Enemy_Melee): `Melee03`, PlayRate 0.9, 계수 1.2, 반경 200, 전방 150, 넉백 500, Cooldown GE_Cooldown_Boss_Melee.
- `GA_Boss_Slam` (부모 GA_SCBase): Commit → `BP_TelegraphCircle` 스폰(반경 500, 1.2초) → PlayMontageAndWait(AM_ChargedAttack, `Charge`) → WaitDelay 1.2 → MontageJumpToSection(`Attack`) → WaitDelay 0.45 → HitTargetsInFront(500, 0, 2.5, 200, 600) + 큐 GameplayCue.Enemy.Slam + 예고원 파괴 → 몽타주 끝나면 End. Cooldown GE_Cooldown_Boss_Slam.
- `GA_Boss_Charge` (부모 GA_SCBase): Commit → 대상 쪽 회전 → WaitDelay 0.5 → LaunchCharacter(전방 × 2500) + AM_Dash 재생 → 0.15/0.35/0.55초에 반경 200 타격(HitActors로 중복 방지) → 0.8초에 End. Cooldown GE_Cooldown_Boss_Charge.

**Combat/BP_TelegraphCircle**: 바닥 원판(SM_Cylinder, 높이 0.01배, MI_SC_Telegraph). `Init(Radius, Duration)`: Tick에서 크기 0 → Radius로 키움, Duration 뒤 스스로 파괴하지 않고 스킬이 파괴.

**데이터 에셋**: DA_AbilitySet_Grunt [(GA_Enemy_Melee, AI.Attack.1), (GA_HitReact)], DT_Attr_Grunt / DA_AbilitySet_Boss [(GA_Enemy_Melee_Boss, AI.Attack.1), (GA_Boss_Slam, AI.Attack.2), (GA_Boss_Charge, AI.Attack.3)], DT_Attr_Boss / DA_AbilitySet_Static [(GA_HitReact)], DT_Attr_Dummy / DA_AbilitySet_Crystal [], DT_Attr_Crystal.

## 6단계: 게임 흐름

- **Core/BP_SCGameInstance**: 변수 `FieldLevelName`("L_CombatField"), `ReturnPortal`("GateReturn"). `EnterDungeon(LevelName)`: OpenLevel(LevelName, Absolute). `ReturnToField()`: OpenLevel("L_CombatField#GateReturn", Absolute) — `#` 뒤 문자열이 Portal이 되고, 엔진 FindPlayerStart가 PlayerStartTag가 같은 PlayerStart를 고른다.
- **Core/BP_FieldGameMode** (부모 BP_SCGameModeBase): **ChoosePlayerStart 오버라이드**: PlayerStartTag가 `FieldStart`인 PlayerStart를 반환(없으면 부모 결과). Portal이 있으면 엔진이 이 함수보다 먼저 태그로 고르므로 복귀는 영향 없다. (기본 ChoosePlayerStart는 PlayerStart가 둘 이상이면 무작위라서 필요하다. 오버라이드가 MCP로 안 되면 GateReturn을 PlayerStart가 아닌 TargetPoint로 두고 PC OnPossess에서 이동.)
- **Core/BP_DungeonGameMode** (부모 BP_SCGameModeBase): BeginPlay에 StartTime 저장, 모든 BP_DungeonRoom의 OnRoomCleared 바인딩. bIsFinalRoom인 방이 클리어되면 2초 뒤 PC.OpenDungeonClear(경과 시간).
- **Dungeon/BP_DungeonDoor**: `DoorMesh`(SM_Cube 6×0.5×5m, MI_SC_Door). 변수 `bStartOpen`, `OpenOffset`((0,0,-520)), `MoveTime`(0.6). `OpenDoor()`, `CloseDoor()`: MoveComponentTo. BeginPlay에서 초기 상태 즉시 적용.
- **Dungeon/BP_DungeonGate**: 기둥 2, 상인방 1, 문짝 2(SM_Cube, MI_SC_Gate), `PortalPlane`(SM_Plane 세움, MI_SC_Portal, 처음엔 숨김), `InteractSphere`(반경 400), `PortalTrigger`(Box, 처음엔 콜리전 끔), `Interactable`(AC_Interactable, PromptText "게이트 열기"). 변수 `DungeonLevelName`("L_Dungeon_01"), `DungeonTitle`("시련의 회랑"), `DungeonDescription`, `bIsOpen`, `bEntryOpen`.
  - InteractSphere 겹침 시작(플레이어, 안 열림) → PC.SetInteractable(Interactable, true), 끝 → false.
  - Interactable.OnInteracted → 문짝을 양옆으로 MoveComponentTo(1초), 포털 보이기, PortalTrigger 켜기, 안내 숨김, bIsOpen.
  - PortalTrigger 겹침(플레이어, 열림, 창 없음) → bEntryOpen → `PC.OpenDungeonEntry(...)` → 반환 위젯의 OnCancelled → bEntryOpen=false, 플레이어를 게이트 앞(-Y 300)으로 옮김.
- **Dungeon/BP_DungeonRoom**: `RoomTrigger`(Box, 인스턴스 편집 가능 크기), `RespawnPoint`(Arrow). 변수(인스턴스 편집) `RoomIndex`, `RoomTitle`, `RoomSubtitle`, `EntryDoor`, `ExitDoor`(BP_DungeonDoor), `Enemies`(BP_EnemyBase 배열), `bIsFinalRoom`. 상태 `bStarted`, `bCleared`. 디스패처 `OnRoomStarted(Room)`, `OnRoomCleared(Room)`.
  - RoomTrigger 겹침(플레이어, 시작 전) → `StartRoom`: 배너, 플레이어 Combat.SetRespawnTransform(RespawnPoint), 방송, `BeginRoomLogic()`.
  - `BeginRoomLogic()` 기본: `ClearRoom()`. `ClearRoom()`: 한 번만, ExitDoor.OpenDoor, 방송.
  - `CloseDoors()`: 입구·출구 닫기.
- **BP_Room_Start**: 부모 그대로(들어오면 바로 클리어).
- **BP_Room_Mob**: BeginRoomLogic 오버라이드 → CloseDoors → CurrentWave=1 → `StartWave`: Wave가 CurrentWave인 적마다 OnDied 바인딩 + ActivateEnemy, AliveCount 세기. 0마리면 ClearRoom. 적 사망 → AliveCount-- → 0이면 CurrentWave++, 1초 뒤 StartWave.
- **BP_Room_Event**: 변수 `TimeLimit`(30). BeginRoomLogic → CloseDoors → Enemies(봉인석) 활성·바인딩 → PC.ShowEventTimer("봉인석을 파괴하라", TimeLimit) → 타이머. 봉인석 파괴 → 진행 텍스트 "봉인석 n/3" → 전부면 성공(플레이어에게 GE_RestoreFull, GE_Buff_Attack, 배너 "성공! 공격력 +30%"). 시간 초과 → 남은 봉인석 휴면, 배너 "실패". 둘 다 HideEventTimer → ClearRoom.
- **BP_Room_Boss**: bIsFinalRoom true. BeginRoomLogic → CloseDoors → 보스 활성 → PC.ShowBossBar(보스, 이름) → 보스 OnDied → HideBossBar → ClearRoom.

## 7단계: 레벨

- **L_CombatField**: `/Engine/Maps/Templates/Template_Default` 복제(World Partition 아님). 사양 6장 배치. PlayerStart 2개(복제된 PlayerStart_0에 태그 `FieldStart`, 새 PlayerStart 태그 `GateReturn` Yaw -90). 게이트 (0,2200) Yaw -90(정면이 -Y). 더미 3, 스파링 잡몹 2(bRespawnOnDeath true, bDestroyOnDeath false, bStartDormant false). GameMode BP_FieldGameMode.
- **L_Dungeon_01**: Template_Default 복제(템플릿 바닥 액터는 지운다). 방 좌표(+X 일렬, 벽 높이 500, 두께 50, 통로 폭 600).

  | 방 | X 범위 | 크기 |
  | --- | --- | --- |
  | Start | -600 ~ 600 | 1200 × 1200 |
  | 통로 1 | 600 ~ 1000 | |
  | Mob 1 | 1000 ~ 3000 | 2000 × 2000 |
  | 통로 2 | 3000 ~ 3400 | |
  | Event | 3400 ~ 5000 | 1600 × 1600 |
  | 통로 3 | 5000 ~ 5400 | |
  | Mob 2 | 5400 ~ 7400 | 2000 × 2000 |
  | 통로 4 | 7400 ~ 7800 | |
  | Boss | 7800 ~ 10800 | 3000 × 3000 |

  문: 각 방 입구(서쪽 벽, bStartOpen true)와 출구(동쪽 벽, bStartOpen false). Start 방은 출구 문만(열린 채). 바닥·벽은 SM_Cube 스태틱 메시 액터(ProgrammaticToolset 루프로 배치). 방 로직 액터는 방 중심에, RoomTrigger는 방 안쪽(벽에서 200 안쪽). 적은 휴면으로 배치하고 방의 Enemies 배열에 연결. PlayerStart는 (0,0). GameMode BP_DungeonGameMode.
- 프로젝트 설정: GameInstanceClass BP_SCGameInstance, GlobalDefaultGameMode BP_SCGameModeBase, EditorStartupMap·GameDefaultMap L_CombatField.

## 8단계: 검증

1. 모든 BP 컴파일(에러·경고 0), 저장 상태 확인.
2. PIE: 인스펙터로 플레이어 어빌리티 8개, 속성, GE_Regen_Player 확인. 로그 에러 수집.
3. PIE 스크린샷(파일로)과 필드·던전 레벨 확인.
4. 사용자 플레이 테스트: 사양 10장 완료 기준 1~7.

## 9단계: 정리

- 모든 BP 그래프를 다시 읽어 정리 상태(겹침 없음, 주석 박스, 한국어 설명)를 점검하고 부족한 곳을 보완.
- `03-build-log.md` 요약, README 갱신, 커밋.
