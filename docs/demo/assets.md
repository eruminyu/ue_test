# 템플릿 에셋 조사 (단계 1)

2026-09-28, Unreal MCP로 읽기만 해서 조사했다(서브에이전트 3개를 하나씩 순차 실행, 플레이어와 Combat의 핵심 주장 28개는 별도 에이전트가 MCP로 재확인해 모두 유지). 템플릿 원본은 바꾸지 않았다.

## 계획 변경 요약 (03 계획서 대비)

| 항목 | 원래 계획 | 바꾼 내용 | 이유 |
| --- | --- | --- | --- |
| 단계 5-2, 5-3 | 몽타주 복제본에 `AN_DemoGameplayEvent` 노티파이 추가 | 노티파이는 추가하지 않는다. 몽타주는 `AM_Demo_*`로 복제만 하고, `BP_DemoPlayer`가 `BPI_Attacker`를 구현한다. `Do Attack Trace` → `SendGameplayEventToActor(self, Event.Hit)`, `Check Combo` → `SendGameplayEventToActor(self, Event.Montage.ComboCheck)`, `Check Charged Attack` → `Attack` 섹션으로 점프 | Combat 몽타주의 노티파이 3종이 소유자에게 `BPI_Attacker` 인터페이스 메시지를 보낸다(계획서 단계 1-5의 분기 조건). 게다가 ObjectTools로는 몽타주의 `Notifies`, `CompositeSections`를 읽을 수도 없다 |
| 단계 5-1 | `AN_DemoGameplayEvent` 생성 | 그대로 만든다(함수 오버라이드 생성 확인용). 데모 몽타주에는 쓰지 않는다 | 확인 항목 유지 |
| GA_Attack | 섹션 3~4개, 계수 1.0/1.1/1.3, 마지막 1.8 | 섹션 `Melee01`, `Melee02`, `Melee03`. 계수 `[1.0, 1.1, 1.8]`, 마지막 타만 띄우기 400 | 템플릿 콤보가 3타다(`BP_CombatCharacter.Combo Section Names`) |
| GA_Skill_GroundSlam | `AM_Demo_Slam`의 공격 섹션 | `AM_Demo_Slam`(= `AM_ChargedAttack` 복제) StartSection `Attack` | 차지 루프(`Charge`)에 갇히지 않게 |
| GA_Dodge | LaunchCharacter 1500 + 대시 몽타주 | 그대로 하되, `MM_Dash`에 루트 모션이 켜져 있어 몽타주가 속도를 덮어쓸 수 있음을 단계 10에서 확인 | 템플릿 대시는 LaunchCharacter 없이 루트 모션으로 움직인다 |
| 큐 이펙트 | 단계 1에서 찾은 Niagara, 없으면 생성 | GC_Hit = `NS_Damage`, GC_Awaken = `NS_JumpPad`(참조만), GC_Slam = `SimpleExplosion` 템플릿으로 `/Game/Demo/VFX/NS_Demo_Slam` 생성 | 지면 강타용 이펙트가 프로젝트에 없다 |
| AnimBP | 슬롯 없으면 교체 | 교체하지 않는다 | `ABP_Unarmed` AnimGraph에 `DefaultSlot` 슬롯 노드가 있다 |
| BP_DemoGameMode | Player Controller = 템플릿 PC | `BP_ThirdPersonPlayerController`, 부모 `GameModeBase` | `BP_CombatPlayerController`는 R 키 충돌, 점프 없음, `BP_CombatCharacter` 하드코딩 리스폰 |
| 입력 검증 | `read_graph_dsl`로 확인 | Enhanced Input 이벤트 노드 연결은 `find_nodes`(entry_points_only=false) + `get_node_infos`로 확인 | `read_graph_dsl`은 EI 이벤트의 Started/Triggered 핀 연결을 보여 주지 않는다 |
| IMC 매핑 | ObjectTools가 안 되면 Python `map_key` | `defaultKeyMappings.mappings`에 ObjectTools로 시도. Python은 MCP로 불가 | 레거시 `mappings`는 비어 있고 실제 데이터는 `defaultKeyMappings`에 있다 |

## MCP 툴 특이사항 (조사 중 발견)

- `ObjectTools.get_properties`로 AnimMontage의 `CompositeSections`, `Notifies`를 읽을 수 없다("could not be read"). `list_properties`에도 없다.
- `BlueprintTools.read_graph_dsl`: AnimGraph는 빈 문자열을 돌려준다. EI 이벤트 노드는 본문 없이 나오고, 여러 이벤트가 공유하는 실행 체인은 한 이벤트 밑에만 나온다. 인터페이스 메시지와 같은 이름의 엔진 함수를 구분하지 않는다(`Game|Damage|ApplyDamage`).
- `BlueprintTools.find_nodes(entry_points_only=true)`는 EI 이벤트 노드를 빠뜨린다.
- `BlueprintTools.list_variables`는 SCS 컴포넌트를 돌려주지 않는다.
- ObjectTools 속성 이름: 네이티브는 lowerCamelCase(`capsuleRadius`, `defaultKeyMappings`), BP 변수는 표시 이름 그대로(첫 글자 소문자, 공백 포함, 예: `dash Montage`).
- `AssetTools.find_assets`는 `.에셋이름` 없는 패키지 경로를 돌려준다. refPath로 쓸 때는 직접 붙인다.
- `AssetTools.get_asset_class`는 BP 에셋에 생성 클래스 이름(`AN_EndDash_C`)을 돌려준다.
- NiagaraToolset_System: `describe_toolset`이 약 278KB. stateless 이미터는 요약/토폴로지가 비어 나온다.


## 플레이어 BP, AnimBP, 입력, 게임 모드 (단계 1 조사, 읽기 전용)

조사일: 2026-09-28. 사용 툴: AssetTools, BlueprintTools, ObjectTools. 에셋은 하나도 바꾸지 않았다.

### 1. /Game/ThirdPerson 에셋

| 에셋 | 전체 오브젝트 경로 | 부모 클래스 |
|---|---|---|
| 캐릭터 BP | `/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter.BP_ThirdPersonCharacter` | `/Script/Engine.Character` |
| 플레이어 컨트롤러 BP | `/Game/ThirdPerson/Blueprints/BP_ThirdPersonPlayerController.BP_ThirdPersonPlayerController` | `/Script/Engine.PlayerController` |
| 게임 모드 BP | `/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode.BP_ThirdPersonGameMode` | `/Script/Engine.GameModeBase` |
| 맵 | `/Game/ThirdPerson/Lvl_ThirdPerson.Lvl_ThirdPerson` | - |
| 머티리얼 인스턴스 | `/Game/ThirdPerson/MI_ThirdPersonColWay.MI_ThirdPersonColWay` | - |

### 2. BP_ThirdPersonCharacter 핵심 설정 (CDO 기준)

- 메시 컴포넌트: `...BP_ThirdPersonCharacter.Default__BP_ThirdPersonCharacter_C:CharacterMesh0`
  - SkeletalMesh: `/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple.SKM_Quinn_Simple` (스켈레톤 `/Game/Characters/Mannequins/Meshes/SK_Mannequin`)
  - AnimClass: `/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed.ABP_Unarmed_C` (AnimationMode = AnimationBlueprint)
  - 상대 위치 (0, 0, -89), 상대 회전 Yaw 270
- 캡슐 `CollisionCylinder`: 반경 35, 반높이 90
- CharacterMovement `CharMoveComp`: MaxWalkSpeed 600, JumpZVelocity 500, bOrientRotationToMovement true, RotationRate Yaw 500, AirControl 0.35, MaxAcceleration 1500, BrakingDecelerationWalking 2000
- bUseControllerRotationYaw false, AutoPossessPlayer Disabled
- CameraBoom, FollowCamera: SCS 컴포넌트로 있다. 세부 값(암 길이 등)은 미확인.
- 그래프: `UserConstructionScript`, `Move`, `Aim`, `EventGraph`. BP 변수 없음(list_variables가 빈 배열).
- **ReceiveBeginPlay 미구현.** 캐릭터는 IMC를 추가하지 않는다.

#### EventGraph 입력 이벤트

| 노드 | InputAction | 연결된 실행 핀 → 호출 |
|---|---|---|
| K2Node_EnhancedInputAction_1 | `/Game/Input/Actions/IA_Move.IA_Move` | Triggered → `Move(X Axis, Y Axis)` (ActionValue_X/Y 연결) |
| K2Node_EnhancedInputAction_4 | `/Game/Input/Actions/IA_Look.IA_Look` | Triggered → `Aim(X, Y)` |
| K2Node_EnhancedInputAction_7 | `/Game/Input/Actions/IA_MouseLook.IA_MouseLook` | Triggered → `Aim(X, Y)` |
| K2Node_EnhancedInputAction_6 | `/Game/Input/Actions/IA_Jump.IA_Jump` | Started → `Character.Jump`, Completed → `Character.StopJumping` |
| 터치 커스텀 이벤트 4개 | - | Primary/Secondary Thumbstick → Move/Aim, Touch Jump Start/End → Jump/StopJumping |

노드 type_id 형식은 `Input|EnhancedActionEvents|EnhancedInputActionIA_Move`이다.

### 3. AnimBP: ABP_Unarmed

- 경로: `/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed.ABP_Unarmed` (부모 `/Script/Engine.AnimInstance`, 스켈레톤 `SK_Mannequin`)
- 참조하는 에셋은 `BP_ThirdPersonCharacter` 하나뿐이다.
- AnimGraph 포즈 흐름: `StateMachine "Main States"` → **`Slot 'DefaultSlot'`** (AnimGraphNode_Slot_0) → `ControlRig` (CR_Mannequin_FootIK) → `Output Pose`
  - 슬롯 노드의 `node.slotName` = `DefaultSlot`. 슬롯 그룹 이름(DefaultGroup)은 미확인.
- 상태 머신: `Locomotion`(Idle, Walk / Run), `Main States`(Locomotion, Jump, Fall Loop, Land)
- 사용 애니메이션: BS_Idle_Walk_Run, MM_Idle, MM_Jump, MM_Fall_Loop, MM_Land (모두 `/Game/Characters/Mannequins/Anims/Unarmed/` 아래)

### 4. 입력 에셋

| 에셋 | 전체 오브젝트 경로 | 비고 |
|---|---|---|
| IMC_Default | `/Game/Input/IMC_Default.IMC_Default` | 매핑 12개 |
| IMC_MouseLook | `/Game/Input/IMC_MouseLook.IMC_MouseLook` | 매핑 1개: Mouse2D → IA_MouseLook (Negate 모디파이어) |
| IA_Move | `/Game/Input/Actions/IA_Move.IA_Move` | valueType Axis2D, 트리거·모디파이어 없음 |
| IA_Look | `/Game/Input/Actions/IA_Look.IA_Look` | 게임패드 Right2D 전용 |
| IA_MouseLook | `/Game/Input/Actions/IA_MouseLook.IA_MouseLook` | - |
| IA_Jump | `/Game/Input/Actions/IA_Jump.IA_Jump` | valueType Boolean, 트리거 Pressed + Released, bConsumeInput true |
| 터치 | `/Game/Input/Touch/BPI_TouchInterface`, `UI_Thumbstick`, `UI_TouchSimple` | - |

**IMC 매핑 속성 구조**(ObjectTools.list_properties):
- 실제 데이터는 `defaultKeyMappings.mappings` 배열에 있다. 레거시 `mappings` 배열은 비어 있다(`[]`).
- 원소(EnhancedActionKeyMapping) 필드: `action`({refPath}), `key`, `triggers`(배열), `modifiers`(배열, 인스턴스드 서브오브젝트 refPath), `settingBehavior`, `playerMappableKeySettings`
- `key`는 스키마상 `{"keyName": ...}` 객체지만, get_properties는 `"SpaceBar"`처럼 문자열로 돌려준다.
- 예시: `{"action":{"refPath":"/Game/Input/Actions/IA_Jump.IA_Jump"},"key":"SpaceBar","triggers":[],"modifiers":[],"settingBehavior":"InheritSettingsFromAction","playerMappableKeySettings":"None"}`

IMC_Default 키: SpaceBar, Gamepad_FaceButton_Bottom (IA_Jump) / W, S, A, D, Up, Down, Left, Right, Gamepad_Left2D (IA_Move) / Gamepad_Right2D (IA_Look).
좌클릭, Left Shift, Q, E, R은 템플릿 IMC 두 개 어디에도 매핑돼 있지 않다.

### 5. 플레이어 컨트롤러와 게임 모드

**BP_ThirdPersonPlayerController EventGraph (BeginPlay 요약)**
1. `DelayUntilNextTick`
2. `IsLocalPlayerController`가 참이면 `EnhancedInputLocalPlayerSubsystem.AddMappingContext(IMC_Default, 우선순위 0)`
3. `ShouldUseTouchControls()`가 참이면 터치 위젯을 만들어 `AddToPlayerScreen`에 추가한다. 거짓이면 `AddMappingContext(IMC_MouseLook, 우선순위 0)`
   - 옵션: `bIgnoreAllPressedKeysUntilRelease=True`
   - `ShouldUseTouchControls`: 플랫폼 이름이 iOS면 true, 기본(Default)은 `Force Touch Controls` 변수를 쓴다(CDO 값 false). Windows에서는 IMC_Default와 IMC_MouseLook이 둘 다 추가된다.
- BP 변수: `Touch Controls Widget Class`, `Force Touch Controls`

**BP_ThirdPersonGameMode CDO**
- DefaultPawnClass: `/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter.BP_ThirdPersonCharacter_C`
- PlayerControllerClass: `/Game/ThirdPerson/Blueprints/BP_ThirdPersonPlayerController.BP_ThirdPersonPlayerController_C`
- HUDClass `/Script/Engine.HUD`, GameStateClass `/Script/Engine.GameStateBase`, PlayerStateClass `/Script/Engine.PlayerState`

### 6. 맵과 프로젝트 기본값

| 맵 | 경로 |
|---|---|
| Lvl_ThirdPerson | `/Game/ThirdPerson/Lvl_ThirdPerson.Lvl_ThirdPerson` (World Settings의 DefaultGameMode = BP_ThirdPersonGameMode_C) |
| Lvl_Combat | `/Game/Variant_Combat/Lvl_Combat` |
| Lvl_Platforming | `/Game/Variant_Platforming/Lvl_Platforming` |

- `Config/DefaultEngine.ini`: EditorStartupMap과 GameDefaultMap = `/Game/ThirdPerson/Lvl_ThirdPerson.Lvl_ThirdPerson`, GlobalDefaultGameMode = `/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode.BP_ThirdPersonGameMode_C`
- `Config/DefaultInput.ini`: DefaultPlayerInputClass = EnhancedPlayerInput, DefaultInputComponentClass = EnhancedInputComponent


## Variant_Combat 조사 결과 (읽기 전용, 2026-09-28)

조사는 전부 Unreal MCP 전용 툴(AssetTools, BlueprintTools, ObjectTools)로 했다. ProgrammaticToolset(Python)은 쓰지 않았다. 확인하지 못한 값은 "미확인", 정황으로 짐작한 값은 "추정"으로 표시했다.

### 1. 폴더별 에셋

| 폴더 | 에셋 (클래스) |
| --- | --- |
| /Game/Variant_Combat | `Lvl_Combat` (맵, One File Per Actor. 액터는 `/Game/__ExternalActors__/Variant_Combat/Lvl_Combat/...`에 있음) |
| Anims | `AM_ComboAttack`, `AM_ChargedAttack` (AnimMontage) · `AN_AttackDamage`, `AN_AttackCombo`, `AN_ChargedAttack` (BP AnimNotify, 부모 `/Script/Engine.AnimNotify`) · `ABP_Manny_Combat` (AnimBP, 부모 `/Script/Engine.AnimInstance`) |
| Blueprints | `BP_CombatCharacter`, `BP_CombatGameMode`, `BP_CombatPlayerController`, `BP_CameraShake_Hit_Enemy`, `BP_CameraShake_Hit_Player` (부모 `/Script/EngineCameras.DefaultCameraShakeBase`), `BPI_Attacker`, `BPI_Damageable`, `BPI_Activatable` |
| Blueprints/AI | `BP_CombatEnemy`, `BP_CombatAIController`, `BP_Combat_EnemySpawner`, `ST_CombatEnemy` (StateTree) |
| Blueprints/AI/EQS | `EnvQueryContext_Danger`, `EnvQueryContext_Player`, `EnvQuery_Evade`, `EnvQuery_Fallback`, `EnvQuery_Flank` |
| Blueprints/AI/StateTreeTasks | `StateTreeCondition_IsCharacterGrounded`, `StateTreeCondition_IsInDanger`, `StateTreeTask_ChargedAttack`, `StateTreeTask_ComboAttack`, `StateTreeTask_FaceActor`, `StateTreeTask_FaceLocation`, `StateTreeTask_GetPlayerInfo`, `StateTreeTask_SetCharacterSpeed`, `StateTreeTask_WaitForLanding` |
| Blueprints/Interactables | `BP_Combat_ActivationVolume`, `BP_Combat_CheckpointVolume`, `BP_Combat_DamageableBox`, `BP_Combat_Dummy`, `BP_Combat_LavaFloor` |
| Input | `IMC_Combat`, `BPI_TouchInterface_Combat`, `UI_TouchInterface_Combat` |
| Input/Actions | `IA_ComboAttack`, `IA_ChargedAttack`, `IA_ToggleCameraSide` |
| VFX | `NS_Damage` (Niagara System) |
| UI | `UI_LifeBar` |
| Materials | `M_Lava`, `MI_Box_Destroyed` |

### 2. 전투 플레이어 캐릭터 `/Game/Variant_Combat/Blueprints/BP_CombatCharacter.BP_CombatCharacter`

- 부모: `/Script/Engine.Character`. `BP_ThirdPersonCharacter`의 자식이 아니다.
- 메시: `/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple.SKM_Quinn_Simple`
- AnimClass: `/Game/Variant_Combat/Anims/ABP_Manny_Combat.ABP_Manny_Combat_C` (AnimationMode = AnimationBlueprint)
- 태그: `Tags = ["Player"]`. 적의 공격 판정이 이 태그로 플레이어를 가려낸다.
- 구현한 인터페이스: `BPI_Attacker`, `BPI_Damageable`, `BPI_TouchInterface_Combat`. 의존성 목록과 구현된 이벤트로 확인했다. `BPI_Activatable`은 쓰지 않는다.
- 그래프: EventGraph, UserConstructionScript, 함수 `Aim`, `Move`

**주요 변수 기본값 (CDO)**

| 변수 | 값 |
| --- | --- |
| Max HP / Current HP | 10 / 5. BeginPlay의 `Reset HP`가 Current를 Max로 맞춘다 |
| Combo Attack Montage | `/Game/Variant_Combat/Anims/AM_ComboAttack.AM_ComboAttack` |
| Combo Section Names | `["Melee01","Melee02","Melee03"]` |
| Charged Attack Montage | `/Game/Variant_Combat/Anims/AM_ChargedAttack.AM_ChargedAttack` |
| Charge Loop Section / Charge Attack Section | `Charge` / `Attack` |
| Combo Input Cache Time Tolerance | 0.45 |
| Attack Input Cache Time Tolerance | 1.0 |
| Melee Trace Distance / Radius | 75 / 75 |
| Melee Damage | 1 |
| Melee Knockback Impulse / Launch Impulse | 250 / 300 |
| Danger Trace Distance / Radius | 300 / 100 |
| Pelvis Bone Name | `pelvis` |
| Respawn Time | 3 |
| Default / Death Camera Distance | 100 / 400 |

**로직 요약**

- **입력**: `IA_ComboAttack`의 Started 핀과 터치 이벤트 `Touch Combo Attack Start`가 같은 Branch 노드(`K2Node_IfThenElse_7`)로 들어간다.
  - 공격 중이 아니면 `IsAttacking = true`, `ComboCount = 0`, `Notify Enemies of Attack`을 부른다. 이어서 `Play Montage(AM_ComboAttack)`로 재생하고, OnCompleted에서 `Check for Cached Attack Input out of Combo`를 부른다.
  - 공격 중이면 `CachedAttackInputTime`에 현재 시간을 저장한다.
- **차지 입력**: `IA_ChargedAttack`의 Started 핀은 `SetIsChargingAttack(true)`(`K2Node_VariableSet_11`)로, Completed 핀은 `SetIsChargingAttack(false)`(`K2Node_VariableSet_12`)로 들어간다. 이 두 체인은 `Touch Charged Attack Start`/`End`와 공유한다.
- **Check Combo** (BPI_Attacker 이벤트, 노티파이가 부른다):
  1. 조건: 공격 중이고 차지 중이 아니며 `Now - CachedAttackInputTime <= 0.45`
  2. 조건을 만족하면 `ComboCount`를 1 늘린다.
  3. 늘린 값이 `ComboSectionNames`의 LastIndex 이하이면 `Notify Enemies of Attack`을 부르고 `Montage_JumpToSection(ComboSectionNames[ComboCount], AM_ComboAttack)`을 실행한다.
- **Check Charged Attack** (BPI_Attacker 이벤트): `HasLoopedChargedAttack = true`, `HasReleasedChargedAttack = !IsChargingAttack`로 둔다. 그다음 `Montage_JumpToSection(Select(Attack, Charge, HasReleased), AM_ChargedAttack)`을 실행한다. 버튼을 떼면 `Attack` 섹션으로, 누르고 있으면 `Charge` 섹션으로 간다.
- **Do Attack Trace (Damage Source Bone: Name)** (BPI_Attacker 이벤트):
  1. Mesh 소켓 위치(`Damage Source Bone`)에서 전방 × `MeleeTraceDistance`까지 `MultiSphereTraceForObjects`를 한다. 반경은 `MeleeTraceRadius`, 오브젝트 타입은 `ObjectTypeQuery3`, `ObjectTypeQuery2`다. 기본 매핑이라면 Pawn과 WorldDynamic이다(추정).
  2. 맞은 액터마다 **`BPI_Damageable.Apply Damage` 인터페이스 메시지**(`K2Node_Message_0`)를 보낸다. 인자는 Damage = MeleeDamage, Causer = self, Location = ImpactPoint다.
  3. Impulse는 (히트 벡터 × -Knockback) + (Up × Launch)로 계산한다. 여기서 히트 벡터가 어느 필드인지는 추정이다.
  4. 마지막으로 `PlayWorldCameraShake(BP_CameraShake_Hit_Enemy)`를 재생한다.
- **Apply Damage** (피격):
  1. HP가 0보다 크면 엔진 `ApplyDamage(self)`를 부르고, 이어서 `AnyDamage` 이벤트가 불린다.
  2. `CharacterMovement.AddImpulse`를 적용한다.
  3. `NS_Damage`를 스폰한다.
  4. 물리 시뮬레이션 중이면 Mesh에도 임펄스를 준다.
- **AnyDamage**:
  - HP가 0 이하가 되면 `BPI_Damageable.Handle Death`를 부른다.
  - 아니면 LifeBar를 갱신한다. 이어서 PhysicsBlendWeight 0.5와 pelvis 아래 물리 시뮬레이션으로 피격 반응을 낸다(DSL 라벨 `SetBodySimulatePhysics`). 마지막으로 카메라 셰이크를 재생한다.
  - `OnLanded`에서 PhysicsBlendWeight를 원래대로 돌린다.
- **Handle Death**:
  1. `DisableInput`으로 입력을 끄고, Mesh `SetSimulatePhysics(true)`로 래그돌을 켠다.
  2. LifeBar를 숨기고 카메라 거리를 400으로 바꾼다.
  3. `RetriggerableDelay(3)` 뒤 `DestroyActor`를 부른다.
  4. 컨트롤러의 `OnPawnDestroyed`가 `BP_CombatCharacter_C`를 다시 스폰해서 빙의한다.
- **Notify Enemies of Attack**: 전방 300, 반경 100으로 스피어 트레이스를 하고, 맞은 액터에 `BPI_Damageable.Notify Danger`를 보낸다. AI가 회피할 때 쓴다.

### 3. 몽타주

| 항목 | AM_ComboAttack | AM_ChargedAttack |
| --- | --- | --- |
| 경로 | `/Game/Variant_Combat/Anims/AM_ComboAttack.AM_ComboAttack` | `/Game/Variant_Combat/Anims/AM_ChargedAttack.AM_ChargedAttack` |
| 길이 (sequenceLength) | 3.6667초 | 1.8333초 |
| 스켈레톤 | `/Game/Characters/Mannequins/Meshes/SK_Mannequin.SK_Mannequin` | 동일 |
| 슬롯 | `DefaultSlot` | `DefaultSlot` |
| 세그먼트 | `MM_Attack_01` (startPos 0, 1.0초), `MM_Attack_02` (startPos 1, 1.0초), `MM_Attack_03` (startPos 2, 1.667초). 경로는 `/Game/Characters/Mannequins/Anims/Unarmed/Attack/` | `MM_ChargedAttack` (startPos 0, 1.833초) |
| Blend In / Out | Cubic 0.1 / Cubic 0.2, AutoBlendOut 켜짐 | 동일 |
| 섹션 이름 | **미확인.** 캐릭터 변수 기준으로는 `Melee01`, `Melee02`, `Melee03`(추정). 시작 시간은 세그먼트 경계로 보아 0 / 1 / 2초(추정) | **미확인.** 캐릭터 변수 기준으로는 `Charge`(루프), `Attack`(추정). 시작 시간과 섹션 링크는 미확인 |
| 노티파이 클래스 | `AN_AttackDamage`, `AN_AttackCombo`. 참조 관계로 확인했다 | `AN_AttackDamage`, `AN_ChargedAttack`. 참조 관계로 확인했다 |
| 노티파이 트리거 시간·개수 | 미확인 | 미확인 |
| 인스턴스 값 (`Damage Bone`) | 미확인. CDO 기본값은 `None` | 미확인 |

ObjectTools로는 몽타주의 섹션(CompositeSections)과 노티파이(Notifies) 배열을 읽을 수 없었다. 자세한 내용은 tool_quirks에 있다.

### 4. 공격 판정 방식 (핵심)

**BP AnimNotify가 소유자에게 BP 인터페이스 메시지를 보내는 방식이다.** 캐스트는 하지 않는다. 트레이스도 노티파이 안에서 하지 않고 캐릭터가 직접 한다.

| 노티파이 | 표시 이름 (GetNotifyName) | Received_Notify 내용 | 쓰는 몽타주 |
| --- | --- | --- | --- |
| `/Game/Variant_Combat/Anims/AN_AttackDamage.AN_AttackDamage` | "Do Melee Attack Damage" | `BPI_Attacker.Do Attack Trace(Target = MeshComp.GetOwner, Damage Source Bone = 변수 Damage Bone)`, return true | AM_ComboAttack, AM_ChargedAttack |
| `/Game/Variant_Combat/Anims/AN_AttackCombo.AN_AttackCombo` | "Check Combo" | `BPI_Attacker.Check Combo(Target = Owner)`, return true | AM_ComboAttack |
| `/Game/Variant_Combat/Anims/AN_ChargedAttack.AN_ChargedAttack` | "Check Charged Attack" | `BPI_Attacker.Check Charged Attack(Target = Owner)`, return true | AM_ChargedAttack |

세 노티파이 모두 호출 노드가 `K2Node_Message`다. 즉 인터페이스 메시지이므로, 소유자가 인터페이스를 구현하지 않았으면 에러 없이 아무 일도 일어나지 않는다. 콤보 체크(다음 타로 넘어갈지 판단)도 노티파이 `AN_AttackCombo`가 `Check Combo`를 불러서 한다.

**인터페이스 시그니처**. 모두 출력 없는 이벤트형이다.

- `/Game/Variant_Combat/Blueprints/BPI_Attacker.BPI_Attacker`
  - `Do Attack Trace(Damage Source Bone: Name)`
  - `Check Combo()`
  - `Check Charged Attack()`
- `/Game/Variant_Combat/Blueprints/BPI_Damageable.BPI_Damageable`
  - `Apply Damage(Damage: Float(double), Damage Causer: Actor, Damage Location: Vector, Damage Impulse: Vector)`
  - `Handle Death()`
  - `Apply Healing(Healing: Float(double), Healer: Actor)`
  - `Notify Danger(Danger Location: Vector, Danger Source: Actor)`
- `/Game/Variant_Combat/Blueprints/BPI_Activatable.BPI_Activatable`
  - `Toggle Interaction`, `Activate Interaction`, `Deactivate Interaction` (시그니처 미확인)
- `/Game/Variant_Combat/Input/BPI_TouchInterface_Combat.BPI_TouchInterface_Combat`
  - `Primary Thumbstick`, `Secondary Thumbstick`, `Touch Combo Attack Start/End`, `Touch Charged Attack Start/End`, `Touch Toggle Camera`

### 5. AnimBP `/Game/Variant_Combat/Anims/ABP_Manny_Combat.ABP_Manny_Combat`

- 부모는 `AnimInstance`다. AnimGraph에 **Slot 노드(`AnimGraphNode_Slot_0`, slotName = `DefaultSlot`)가 있다.**
- 상태 머신은 `Locomotion`(Idle, Walk / Run)과 `Main States`(Locomotion, Jump, Fall Loop, Land) 두 개다.
- 플레이어(Quinn)와 적(Manny)이 함께 쓴다.

### 6. 적과 더미

**`/Game/Variant_Combat/Blueprints/AI/BP_CombatEnemy.BP_CombatEnemy`**

- 부모 `Character`, 메시 `/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple`, AnimClass `ABP_Manny_Combat_C`
- AIControllerClass는 `/Game/Variant_Combat/Blueprints/AI/BP_CombatAIController.BP_CombatAIController_C`이고, AutoPossessAI는 PlacedInWorldOrSpawned다. StateTree `ST_CombatEnemy`로 공격한다.
- 수치: Max HP 5(ConstructionScript에서 Current = Max), Melee Trace 75/50, Damage 1, Knockback 150, Launch 350, Min/Max Charge Loops 2/5, Death Removal Time 5
- 구현: `BPI_Attacker`(Do Attack Trace는 `Player` 태그를 가진 액터에게만 Apply Damage를 보냄), `BPI_Damageable`(Apply Damage, Handle Death, Notify Danger). 이벤트 디스패처는 `On Attack Completed`, `On Enemy Died`다.
- **사망**:
  1. LifeBar를 숨긴다.
  2. 캡슐 `SetCollisionEnabled`로 콜리전을 바꾼다. 인자값은 미확인.
  3. `DisableMovement`로 이동을 막고, Mesh `SetSimulatePhysics(true)`로 래그돌을 켠다.
  4. `On Enemy Died`를 방송한다.
  5. `Delay(5)` 뒤 `DestroyActor`를 부른다. **부활 기능은 없다.**
- **피격**: 엔진 ApplyDamage와 임펄스를 적용하고 NS_Damage를 스폰한다. 콤보·차지 몽타주를 `Montage_Stop(0.1)`로 끊고, PhysicsBlendWeight 0.5와 pelvis 아래 물리로 흔들린다.
- 훈련용 더미로 쓰기에는 맞지 않는다. AI가 자동으로 빙의해서 공격하고, 죽으면 파괴되며, ASC가 없다.

**`/Game/Variant_Combat/Blueprints/Interactables/BP_Combat_Dummy.BP_Combat_Dummy`**

- 부모는 `Actor`다. 컴포넌트는 `BasePlate`, `Dummy`, `PhysicsConstraint`이고, ConstructionScript에서 BasePlate와 Dummy를 PhysicsConstraint로 잇는다.
- 사용하는 메시는 `/Game/LevelPrototyping/Meshes/SM_Cylinder`, `/Game/LevelPrototyping/Interactable/Target/Assets/SM_TargetBaseMesh`, 머티리얼은 `/Game/ThirdPerson/MI_ThirdPersonColWay`다.
- `BPI_Damageable.Apply Damage`만 구현한다. Dummy에 `AddImpulseAtLocation`을 주고 `NS_Damage`를 스폰하는 게 전부다. **HP, 사망, 부활, 캐릭터 메시가 없다.** 흔들리는 샌드백이라 GAS 훈련용 더미의 기반으로는 맞지 않는다.

### 7. 입력

- `/Game/Variant_Combat/Input/Actions/IA_ComboAttack.IA_ComboAttack`: Boolean, Triggers = Pressed + Released
- `/Game/Variant_Combat/Input/Actions/IA_ChargedAttack.IA_ChargedAttack`: Boolean, Triggers = Pressed + Released
- `/Game/Variant_Combat/Input/Actions/IA_ToggleCameraSide.IA_ToggleCameraSide`: Boolean, Triggers = Pressed
- `/Game/Variant_Combat/Input/IMC_Combat.IMC_Combat` 매핑
  - `IA_Move`: W/S/A/D, 방향키, Gamepad_Left2D
  - `IA_Look`: Gamepad_Right2D
  - `IA_ComboAttack`: LeftMouseButton, Gamepad_RightShoulder
  - `IA_ChargedAttack`: RightMouseButton, Gamepad_RightTriggerAxis
  - `IA_ToggleCameraSide`: **R**, Gamepad_DPad_Down
  - **IA_Jump 매핑은 없다.**
- `/Game/Variant_Combat/Blueprints/BP_CombatPlayerController.BP_CombatPlayerController`
  - BeginPlay에서 `IMC_Combat`(우선순위 0)을 추가한다. 터치 모드가 아니면 `/Game/Input/IMC_MouseLook.IMC_MouseLook`(0)도 추가한다.
  - OnPossess에서 리스폰 위치를 저장하고, 폰이 파괴되면 **`BP_CombatCharacter_C`를 하드코딩으로 다시 스폰**한다.
- `/Game/Variant_Combat/Blueprints/BP_CombatGameMode.BP_CombatGameMode`: DefaultPawnClass = `BP_CombatCharacter_C`, PlayerControllerClass = `BP_CombatPlayerController_C`

### 8. VFX

- `/Game/Variant_Combat/VFX/NS_Damage.NS_Damage`: Niagara System. 에셋 태그 기준으로 이미터 1개(Stateless), Sprite 렌더러 1개, GPU 이미터 없음, EffectType None, LibraryVisibility Unexposed다.
- 플레이어, 적, 더미 모두 피격 위치에 `SpawnSystemAtLocation`으로 쓴다. Combat VFX 폴더에는 이것 하나뿐이고, 먼지나 오라용 이펙트는 없다.


## Variant_Platforming과 Niagara 이펙트 (단계 1-3, 1-6 조사)

조사 방법: Unreal MCP로 읽기만 했다. 에셋 생성, 수정, 저장, 컴파일, PIE는 하지 않았다. 확인하지 못한 항목은 "미확인", 정황으로만 판단한 항목은 "추정"으로 적었다.

### 1. /Game/Variant_Platforming 에셋 목록

| 폴더 | 에셋 (전체 오브젝트 경로) | 종류 |
| --- | --- | --- |
| Anims | `/Game/Variant_Platforming/Anims/AM_Dash.AM_Dash` | AnimMontage |
| Anims | `/Game/Variant_Platforming/Anims/AN_EndDash.AN_EndDash` | BP AnimNotify (부모 `/Script/Engine.AnimNotify`) |
| Anims | `/Game/Variant_Platforming/Anims/ABP_Manny_Platforming.ABP_Manny_Platforming` | AnimBP |
| Blueprints | `/Game/Variant_Platforming/Blueprints/BP_PlatformingCharacter.BP_PlatformingCharacter` | 캐릭터 BP (부모 `/Script/Engine.Character`) |
| Blueprints | `/Game/Variant_Platforming/Blueprints/BP_PlatformingGameMode.BP_PlatformingGameMode` | 게임 모드 |
| Blueprints | `/Game/Variant_Platforming/Blueprints/BP_PlatformingPlayerController.BP_PlatformingPlayerController` | 플레이어 컨트롤러 |
| Input | `/Game/Variant_Platforming/Input/Actions/IA_Dash.IA_Dash` | InputAction (값 타입 Boolean) |
| Input | `/Game/Variant_Platforming/Input/IMC_Platforming.IMC_Platforming` | InputMappingContext |
| Input | `/Game/Variant_Platforming/Input/BPI_TouchInterface_Platforming.BPI_TouchInterface_Platforming` | 터치 인터페이스 BPI |
| Input | `/Game/Variant_Platforming/Input/UI_TouchInterface_Platforming.UI_TouchInterface_Platforming` | 터치 UI |
| VFX | `/Game/Variant_Platforming/VFX/NS_Jump_Trail.NS_Jump_Trail` | NiagaraSystem |
| (루트) | `/Game/Variant_Platforming/Lvl_Platforming.Lvl_Platforming` | 레벨 |

IMC_Platforming의 대시 키는 `IA_Dash`에 `LeftShift`와 `Gamepad_FaceButton_Right`다. 트리거와 모디파이어는 없다.

### 2. 대시 몽타주 AM_Dash

| 항목 | 값 |
| --- | --- |
| 경로 | `/Game/Variant_Platforming/Anims/AM_Dash.AM_Dash` |
| 스켈레톤 | `/Game/Characters/Mannequins/Meshes/SK_Mannequin.SK_Mannequin` |
| 길이 (sequenceLength) | 0.96666664초 |
| 슬롯 트랙 | 1개, `DefaultSlot` |
| 세그먼트 | `/Game/Characters/Mannequins/Anims/Unarmed/Jump/MM_Dash.MM_Dash`, 0 ~ 0.96666664초, 재생 속도 1, 반복 1회 |
| 블렌드 | Blend In 0.25초 Linear, Blend Out 0.25초 Linear, 자동 블렌드 아웃 켜짐, blendOutTriggerTime -1, rateScale 1 |
| 루트 모션 | 원본 `MM_Dash`에 bEnableRootMotion **true**, rootMotionRootLock RefPose |
| 섹션 | **미확인.** `CompositeSections` 속성을 MCP로 읽을 수 없음 |
| 노티파이 | `AN_EndDash` 1종이 들어 있다. 근거는 AM_Dash의 의존성에 AN_EndDash가 있고, AN_EndDash를 참조하는 에셋이 AM_Dash 하나뿐이라는 점이다. **트리거 시간은 미확인**(`Notifies` 속성을 읽을 수 없음) |

AN_EndDash의 `Received_Notify`는 `GetOwner(MeshComp)`를 `BP_PlatformingCharacter`로 캐스트해서 `EndDash`를 호출하고 true를 반환한다. 캐스트가 실패하면 아무것도 하지 않는다.

### 3. BP_PlatformingCharacter의 대시 구현

- 진입점은 `IA_Dash`의 **Started**와 `Touch Dash Start` 두 개이고, 둘 다 같은 Branch 노드 `K2Node_IfThenElse_7`로 연결된다. Triggered, Completed, Ongoing, Canceled 핀은 연결되지 않았다.
- 순서:
  1. `HasDashed`가 false일 때만 실행한다.
  2. `HasDashed`와 `IsDashing`을 true로 바꾼다.
  3. `CharacterMovement.SetGravityScale(0)`과 `SetVelocity(0,0,0)`을 호출한다.
  4. `Trail_L`(Niagara)를 Activate한다.
  5. 비동기 `PlayMontage(Mesh, DashMontage)`를 호출한다. `dash Montage`의 기본값은 AM_Dash다.
- **LaunchCharacter는 대시에 쓰지 않는다.** LaunchCharacter는 벽 점프에만 있다. 대시 이동은 몽타주의 루트 모션으로 한다(`MM_Dash`의 루트 모션이 켜져 있고 속도를 0으로 만든 뒤 몽타주를 재생하는 구조에서 추정).
- 끝내기: `EndDash` 커스텀 이벤트(AN_EndDash가 호출)가 중력 스케일을 2.5로 되돌리고 `IsDashing`을 false로 바꾼다. 땅 위에 있으면 `HasDashed`를 false로 바꾸고 `Trail_L`을 Deactivate한다. PlayMontage의 OnInterrupted에도 비슷한 복구 코드가 있다. `OnLanded`에서도 `HasDashed`를 false로 되돌린다.
- CDO 값: `max Coyote Time` 0.16, `trail Color` (0.051, 0.527, 0.051, 0.25).

### 4. Niagara 시스템 목록

프로젝트 전체에서 `/Script/Niagara.NiagaraSystem`을 검색하면 20개가 나온다. 그중 `/Game`에 있는 것은 3개다. 이름에 Hit, Impact, Spark, Dust, Aura가 들어간 시스템은 없다. `/Game`에는 Cascade ParticleSystem이 0개다.

| 경로 | 위치 | 이미터 (렌더러) | 루프 | 용도 |
| --- | --- | --- | --- | --- |
| `/Game/Variant_Combat/VFX/NS_Damage.NS_Damage` | /Game | DirectionalBurst (CPU, stateless로 추정) | 시스템 Infinite 5초. 이미터 자체 루프는 미확인 | **타격.** Combat 변형 BP 4개(BP_CombatCharacter, BP_CombatEnemy, BP_Combat_DamageableBox, BP_Combat_Dummy)가 참조한다. DamageableBox는 `SpawnSystemAtLocation(Damage Location, RotationFromX(Impulse))`로 쓴다 |
| `/Game/Variant_Platforming/VFX/NS_Jump_Trail.NS_Jump_Trail` | /Game | Fountain (CPU, Ribbon) | 이미터 Self, Infinite 2초. SpawnPerUnit 간격 5, 기준은 Engine.Owner.Velocity | 이동 궤적 리본. 움직일 때만 생긴다. User.Color 있음 |
| `/Game/LevelPrototyping/Interactable/JumpPad/Assets/NS_JumpPad.NS_JumpPad` | /Game | Glow_Base (Sprite+Mesh, 1초마다 Burst 1), Bands (Sprite+Mesh, SpawnRate), Spores (GPU, SpawnRate 100) | 시스템 Infinite 5초. 이미터 Infinite 1초(수명 주기 System) | **바닥 원형 글로우와 솟는 입자, 루프.** User.Color 기본값 (0.125, 0.43, 1, 2). 메시 SM_CircularGlow, SM_CircularBand 사용 |
| `/Niagara/DefaultAssets/Templates/Systems/SimpleExplosion.SimpleExplosion` | Niagara 플러그인 | OmnidirectionalBurst (Sprite), UpwardMeshBurst (Mesh), SimpleSpriteBurst (Sprite). SpawnBurst_Instantaneous | 시스템 **Once 1초** | 폭발, 지면 충격 |
| `/Niagara/DefaultAssets/Templates/Systems/RadialBurst.RadialBurst` | Niagara 플러그인 | RibbonTrailFollower (Ribbon), OmnidirectionalBurst (Sprite), Ribbon_Trail_Leader (Sprite) | 시스템 **Once 2초** | 방사형 파편과 리본 |
| `/Niagara/DefaultAssets/Templates/Systems/DirectionalBurst.DirectionalBurst` | Niagara 플러그인 | LocationBasedRibbon (Ribbon), DirectionalBurst (Sprite) | 시스템 **Once 1초** | 방향성 타격 |
| `/Niagara/DefaultAssets/Templates/Systems/DirectionalBurstLightweight.DirectionalBurstLightweight` | Niagara 플러그인 | DirectionalBurst (stateless로 추정) | 시스템 Infinite 5초. 이미터 루프는 미확인 | NS_Damage와 구조가 같다. NS_Damage의 원본 템플릿으로 추정 |
| `/Niagara/DefaultAssets/Templates/Systems/FountainLightweight`, `MinimalLightweight`, `AttributeReaderTrails`, `/Niagara/DefaultAssets/DefaultSystem` | Niagara 플러그인 | 상세는 읽지 않음 | 미확인 | 범용 템플릿 |
| `/HairStrands/Emitters/*System` 6개, `/Water/Effects/Niagara/Shoreline/NiagaraShore_System`, `/Niagara/VectorFields/VectorFieldVisualizationSystem`, `/Niagara/DefaultAssets/Templates/BehaviorExamples/RenderTargetTexturePainter` | 엔진 플러그인 | 헤어, 물, 디버그용 | 미확인 | 데모와 관계없음 |

### 5. GameplayCue별 추천

| 큐 | 추천 | 이유 |
| --- | --- | --- |
| GC_Hit (Burst) | `/Game/Variant_Combat/VFX/NS_Damage.NS_Damage` | 템플릿이 실제로 타격 이펙트로 쓰는 에셋이다. 타격 위치에 스폰하고 충격 방향으로 회전하는 방식이 GC_Hit와 같다. 주의: 시스템 루프가 Infinite이고 stateless 이미터의 루프는 MCP로 읽을 수 없다. 한 번 터지고 사라지는지 PIE에서 확인해야 한다. 계속 반복되면 대안은 `/Niagara/DefaultAssets/Templates/Systems/DirectionalBurst.DirectionalBurst`(Once 1초)로 만든 복제본이다 |
| GC_Slam (Burst) | `/Niagara/DefaultAssets/Templates/Systems/SimpleExplosion.SimpleExplosion`을 템플릿으로 `NiagaraToolset_System.CreateNiagaraSystem`을 호출해 `/Game/Demo`에 새 시스템을 만든다 | Once 1초로 한 번만 터진다. 위로 솟는 메시 버스트와 전방향 스프라이트 버스트가 있어 지면 강타에 맞다. 먼지 전용 이펙트는 프로젝트에 없다 |
| GC_Awaken (Looping) | `/Game/LevelPrototyping/Interactable/JumpPad/Assets/NS_JumpPad.NS_JumpPad` | Infinite 루프이고 SpawnRate로 계속 나온다. 바닥 원형 글로우, 밴드, 솟는 포자로 이루어져 발밑 오라로 쓰기 좋다. User.Color로 색을 바꿀 수 있다. NS_Jump_Trail은 움직일 때만 나오는 리본이라 오라로는 맞지 않는다 |

새로 만들어야 하는 Niagara는 없고, Fab 다운로드도 필요 없다.

