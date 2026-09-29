# MCP 쿡북 (SoulCombat)

이 문서는 UE 5.8.2 Unreal MCP로 SoulCombat 에셋을 만들며 확인한 레시피다. 기본 레시피는 docs/mcp/probe-bp-core.md(변수, 함수, 이벤트, 디스패처, 노드 배치, 주석 박스 붙여넣기)와 docs/mcp/toolsets.md(툴 목록)를 본다.

표기: `BT` = `editor_toolset.toolsets.blueprint.BlueprintTools`, `OT` = `editor_toolset.toolsets.object.ObjectTools`, `AT` = `editor_toolset.toolsets.asset.AssetTools`. ObjectTools의 `values`는 JSON **문자열**이다(아래 예시는 읽기 쉽게 객체로 적었다).

## 제작 중 확인한 레시피

### 게임플레이 태그 삭제 (1단계)

- `GameplayTagsToolset.GameplayTagsToolset` `RemoveTag {"tagName":"Event.Input.Released.Guard"}` → `null`. ini에서 해당 줄만 지워지고, 자식이 없어진 암시적 부모(`Event.Input`, `Event.Input.Released`)도 `ListTags`에서 함께 사라진다. 확인은 `ListTags {"parentTag":"Event"}`.

### 스탯 DataTable (1-1)

- 생성: `editor_toolset.toolsets.data_table.DataTableTools` `create {"folder_path":"/Game/SoulCombat/GAS/Data","asset_name":"DT_Attr_Player","schema":{"refPath":"/Script/GameplayAbilities.AttributeMetaData"}}` (폴더가 없으면 만들어 준다).
- 행: `add_rows {"data_table":DT,"row_names":["SCAttributeSet.Health", ...]}` → 기본값 `baseValue 0, minValue 0, maxValue 1`.
- 값: `set_rows {"data_table":DT,"values":"{\"SCAttributeSet.Health\":{\"baseValue\":1000}, ...}"}` (열 이름은 lowerCamelCase `baseValue`). `get_rows`로 확인.
- 여러 테이블은 ProgrammaticToolset 한 스크립트로 create → add_rows → set_rows → get_rows를 돌렸다(오류 없음).

### GameplayEffect (1-2)

- 생성: `BT create {"folder_path":"/Game/SoulCombat/GAS/Effects","asset_name":"GE_X","asset_type":{"refPath":"/Script/GameplayAbilities.GameplayEffect"}}` → **먼저 `compile_blueprint`** 한 뒤 `OT set_properties`(BP ref = CDO).
- 프로퍼티 이름: `durationPolicy`(`Instant`/`Infinite`/`HasDuration`), `durationMagnitude`, `period`(`{"value":0.1}`), `modifiers`, `gameplayCues`, `gEComponents`. 부분 구조체만 넘겨도 나머지는 기본값으로 채워진다.
- 지속 시간: `{"durationPolicy":"HasDuration","durationMagnitude":{"magnitudeCalculationType":"ScalableFloat","scalableFloatMagnitude":{"value":0.35}}}`
- 속성 구조체: `{"attributeName":"Mana","attribute":"/Script/SoulCombat.SCAttributeSet:Mana","attributeOwner":{"refPath":"/Script/SoulCombat.SCAttributeSet"}}`
- ScalableFloat 모디파이어(비용 GE는 음수): `{"attribute":<속성>,"modifierOp":"AddBase","modifierMagnitude":{"magnitudeCalculationType":"ScalableFloat","scalableFloatMagnitude":{"value":-25}}}`. 연산 이름은 5.8 기준 `AddBase`, `MultiplyAdditive`, `Override`가 그대로 읽힌다.
- SetByCaller: `"modifierMagnitude":{"magnitudeCalculationType":"SetByCaller","setByCallerMagnitude":{"dataTag":{"tagName":"Data.Damage"}}}`
- AttributeBased(GE_RestoreFull): `"modifierMagnitude":{"magnitudeCalculationType":"AttributeBased","attributeBasedMagnitude":{"coefficient":{"value":1},"backingAttribute":{"attributeToCapture":<MaxHealth 속성>,"attributeSource":"Target","bSnapshot":false}}}` + `"modifierOp":"Override"`.
- GameplayCues: `"gameplayCues":[{"minLevel":0,"maxLevel":0,"gameplayCueTags":{"gameplayTags":[{"tagName":"GameplayCue.Hit"}]}}]`
- 컴포넌트: `"gEComponents":["/Script/GameplayAbilities.TargetTagsGameplayEffectComponent","/Script/GameplayAbilities.AssetTagsGameplayEffectComponent"]` → 서브오브젝트 `/Game/.../GE_X.Default__GE_X_C:TargetTagsGameplayEffectComponent_0`, `...:AssetTagsGameplayEffectComponent_0`가 생긴다(`get_properties ["gEComponents"]`로 경로 확인).
  - Grant 태그: 서브오브젝트에 `{"inheritableGrantedTagsContainer":{"added":{"gameplayTags":[{"tagName":"Cooldown.Dash"}]},"combinedTags":{"gameplayTags":[{"tagName":"Cooldown.Dash"}]}}}`
  - 에셋 태그: `{"inheritableAssetTags":{"added":{...},"combinedTags":{...}}}` (같은 형식)
  - 전부 취소(GE_Death): `CancelAbilityTagsGameplayEffectComponent`를 넣기만 한다. 필드 `componentMode`(기본 `OnApplication`), `inheritableCancelAbilitiesWithTagsContainer`, `inheritableCancelAbilitiesWithoutTagsContainer`를 비워 두면 엔진이 nullptr로 넘겨 전부 취소한다(engine-api-notes A8).
- 설정 후 `compile_blueprint {"warnings_as_errors":true}` → `get_properties`로 다시 읽기 → `AT save_assets`(경로 명시). 컴파일 후에도 컴포넌트 태그 값이 유지됨을 확인했다.
- 나머지 15개 GE는 위 형태를 ProgrammaticToolset 한 스크립트로 만들고, 두 번째 스크립트로 전부 읽어 표와 대조했다.

### Niagara 시스템 (1-3)

- `NiagaraToolsets.NiagaraToolset_System` `CreateNiagaraSystem {"assetName":"NS_SC_Shockwave","assetPath":"/Game/SoulCombat/VFX","templateSystem":{"refPath":"/Niagara/DefaultAssets/Templates/Systems/SimpleExplosion.SimpleExplosion"}}` → 새 시스템 ref.
- 확인: `GetSystemCompileState {"system":{"refPath":...}}` → `aggregateStatus "UpToDate"`, `bHasErrors false`.
- 주의: `describe_toolset NiagaraToolsets.NiagaraToolset_System`은 약 28만 자라 결과가 파일로 떨어진다. 필요한 툴만 스크립트로 뽑아 읽는다.

### GameplayCue 노티파이 (1-3)

- `GASToolsets.GameplayCueToolset` `CreateCueNotifyAsset {"cueTag":"GameplayCue.Hit","packagePath":"/Game/SoulCombat/GAS/Cues","assetName":"GC_Hit","bIsActor":false}` → `BT set_parent {"parent_class":{"refPath":"/Script/GameplayAbilities.GameplayCueNotify_Burst"}}` → `compile_blueprint`. 태그(`gameplayCueTag`)는 유지된다. Looping은 `bIsActor:true` + `GameplayCueNotify_Looping`.
- Burst 프로퍼티: `defaultPlacementInfo`(`socketName`, `attachPolicy` 기본 `DoNotAttach`), `defaultSpawnCondition`, `burstEffects.burstParticles[]`(`niagaraSystem`, `bOverridePlacementInfo`, `placementInfoOverride`...).
  예: `{"defaultPlacementInfo":{"socketName":"spine_03"},"burstEffects":{"burstParticles":[{"niagaraSystem":{"refPath":"/Game/Variant_Combat/VFX/NS_Damage.NS_Damage"}}]}}`
- Looping 프로퍼티: `loopingEffects.loopingParticles[]`(같은 ParticleInfo 형식), `defaultPlacementInfo.attachPolicy` 기본 `AttachToTarget`, `bAutoDestroyOnRemove` 기본 true. 그 밖에 `applicationEffects`, `recurringEffects`, `removalEffects`가 있다.
  예: `{"loopingEffects":{"loopingParticles":[{"niagaraSystem":{"refPath":"/Game/LevelPrototyping/Interactable/JumpPad/Assets/NS_JumpPad.NS_JumpPad"}}]}}`
- Burst BP CDO의 `list_properties`는 약 5만 자다. 필요한 이름을 알면 `get_properties`만 쓴다.
- **함정**: 만들고 저장한 뒤에도 `FindCueNotifyAssets`는 `[]`, `GetCueInfo`는 `notifyAssetPath ""`를 돌려준다(에디터 큐 매니저 목록이 갱신되지 않음). 에셋 레지스트리에는 `AT get_asset_tags` → `"GameplayCueName":"GameplayCue.Hit"`가 들어가 있어 런타임 스캔(DefaultGame.ini `GameplayCueNotifyPaths=/Game/SoulCombat/GAS/Cues`)으로는 찾힐 것으로 본다. 실제 재생은 PIE에서 확인해야 한다.

### Enhanced Input (1-4)

- IA: `editor_toolset.toolsets.data_asset.DataAssetTools` `create {"folder_path":"/Game/SoulCombat/Input","asset_name":"IA_Attack","asset_type":{"refPath":"/Script/EnhancedInput.InputAction"}}`. `valueType` 기본값이 `Boolean`이라 따로 설정하지 않았다.
- IMC: 같은 툴, `asset_type` `/Script/EnhancedInput.InputMappingContext`. 매핑은 `OT set_properties`:
  `{"defaultKeyMappings":{"mappings":[{"action":{"refPath":"/Game/SoulCombat/Input/IA_Attack.IA_Attack"},"key":{"keyName":"LeftMouseButton"},"triggers":[],"modifiers":[]}, ...]}}` → true.
  읽을 때 `key`는 객체가 아니라 문자열(`"LeftMouseButton"`)로 나온다. 매핑 필드: `action`, `key`, `triggers`, `modifiers`, `settingBehavior`, `playerMappableKeySettings`.

### 머티리얼 인스턴스 (1-5)

- `editor_toolset.toolsets.material_instance.MaterialInstanceTools` `create {"folder_path":"/Game/SoulCombat/Materials","asset_name":"MI_SC_Door","parent":{"refPath":"/Game/LevelPrototyping/Materials/M_FlatCol.M_FlatCol"}}` → `set_vector_parameter {"instance":MI,"name":"Base Color","value":{"r":0.18,"g":0.1,"b":0.04,"a":1}}` → `get_vector_parameter`로 확인. 이름은 공백까지 정확히.
- `list_parameters {"material":{"refPath":...}}`로 부모의 Vector 파라미터: M_PrototypeGrid = SurfaceColor, TopSurfaceColor, GridColor, SubGridColor, TopGridColor, TopSubGridGridColor, Line Dimensions / M_FlatCol = Base Color / M_SimpleGlow = Color / MI_Manny_01_New, 02_New = Paint Tint, LogoTint, Blend Offset.
- **경로 주의**: 마네킹 MI는 `/Game/Characters/Mannequins/Materials/Manny/MI_Manny_01_New.MI_Manny_01_New`(하위 폴더 `Manny/`). 계획서의 `/Materials/MI_Manny_01_New`로는 `is not valid MaterialInterface` 에러가 난다.

### 저장 확인

- 단계 끝에 ProgrammaticToolset로 `AT find_assets {"folder_path":"/Game/SoulCombat","name":""}` → 각 경로 `is_dirty`를 돌려 미저장 에셋이 없는지 본다.

### 전투 컴포넌트 그래프 DSL (2-1, 2-2)

- 노드 이름 조사는 ProgrammaticToolset 한 스크립트로 `BT find_node_types {"graph":G,"type_id_filter":"...","context_pins":[]}`와 `get_node_type_pins {"graph":G,"type_id":"..."}`를 여러 개 돌려 한 번에 받는다(자기 BP의 EventGraph에 돌려도 노드가 남지 않았다).
- 멤버 변수 노드 ID는 카테고리를 따른다: `Variables|Combat|State|GetASC`, `Variables|Combat|Config|GetGuardConeDot`. **bool은 b를 뗀 표시 이름**이다: `bIsDead` → `Variables|Combat|State|GetIsDead`/`SetIsDead`, `bRespawnOnDeath` → `GetRespawnonDeath`(on 소문자), `bSuperArmor` → `GetSuperArmor`, `bEnabled`(카테고리 Interaction) → `Variables|Interaction|GetEnabled`. `GetbIsDead`는 `does not exist`. 함수 로컬 변수는 `Variables|Default|Get<Name>`.
- 자기 함수와 커스텀 이벤트 호출: `CallFunction|IsValidTarget`, `CallFunction|Die`. 디스패처 호출: `Default|CallOnHealthChanged :NewValue x :MaxValue y`.
- 리터럴:
  - 태그: `"(TagName=\"State.Dead\")"`
  - 속성(FGameplayAttribute): `"(AttributeName=\"Health\",Attribute=/Script/SoulCombat.SCAttributeSet:Health,AttributeOwner=/Script/CoreUObject.Class'/Script/SoulCombat.SCAttributeSet')"` (핀 값으로 그대로 남는다)
  - GE 클래스: `"/Game/SoulCombat/GAS/Effects/GE_Damage.GE_Damage_C"`, AttributeSet 클래스: `"/Script/SoulCombat.SCAttributeSet"`
  - ObjectTypes 배열: `(Utilities|Array|MakeArray (Utilities|Enum|LiteralenumEObjectTypeQuery :Enum "ObjectTypeQuery3"))` (Pawn)
- `(Actor|GetComponentbyClass :self owner :ComponentClass "/Script/GameplayAbilities.AbilitySystemComponent")`는 출력 핀 타입이 ASC로 바뀌어 ASC 변수 Set에 바로 연결된다.
- 출력이 둘인 순수 노드: `(bind (found value) (Ability|Attribute|GetFloatAttributefromAbilitySystemComponent ...))` (핀 순서대로). 인라인으로 쓰면 어느 핀이 연결될지 모르므로 이 형태를 쓴다.
- 비동기 노드 데이터 출력은 연속 블록 안에서 `_newvalue`처럼 쓴다: `(Ability|Tasks|WaitforAttributeChanged :TargetActor owner :Attribute "<속성>" :OnlyTriggerOnce false (:Changed ... _newvalue ...))`.
- `(select cond a b)` → Select 노드, Index=cond(bool), Option 1(true)=a, Option 0(false)=b. 기대대로 동작.
- `(if cond (return x))` 뒤에 문장을 이어 쓰면 뒤 문장은 Branch의 **else**에 붙는다(가드 절). 함수에서 조기 반환에 쓸 수 있다.
- **함정**: `Utilities|FlowControl|Sequence`는 `then_0`, `then_1`만 있다. `(:then_2 ...)`는 `Unknown exec output "then_2"` 에러. Sequence를 then_1 안에 중첩해서 단계를 늘린다. (에러 난 write_graph_dsl은 노드를 남기지 않았다.)
- **함정**: `(Utilities|IsValid x)`를 식(조건) 자리에 쓰면 IsValid **매크로**가 exec 없이 생겨 Branch 실행 핀이 끊긴다(에러 없이 성공 반환). IsValid는 반드시 연속 블록 형태 `(Utilities|IsValid x (:"Is Valid" ...) (:"Is Not Valid" ...))`로 쓴다. 빈 분기는 `(:"Is Not Valid")`.
- 함수 그래프를 다시 쓸 때는 ProgrammaticToolset로 `find_nodes` → FunctionEntry 외 전부 `delete_node` 후 write (이번에 ApplyHit 47개 삭제 후 재작성).
- 새 ActorComponent BP의 EventGraph에는 연결 없는 BeginPlay/Tick 노드(`K2Node_Event_0`, `_1`)가 있다. 쓰지 않으면 `delete_node`로 지운다.
- 정리 확인: 그래프마다 `get_node_infos`로 연결 수 0인 노드를 찾는다(디스패처 그래프의 FunctionEntry는 원래 0). 배치: 함수는 그래프 전체 노드, EventGraph는 커스텀 이벤트마다 `get_connected_subgraph` 결과로 `arrange_nodes` → 체인끼리 세로로 떨어져 배치됐다(겹침 없음).
- `compile_blueprint`는 성공 시 `null`. 경고·에러가 없었는지 `EditorToolset.LogsToolset GetLogEntries {"pattern":"AC_CombatComponent.*(Warning|Error)","category":"","maxEntries":10}`로 한 번 더 본다.
- `read_graph_dsl`은 Sequence를 풀어서 순서대로 나열하고, 분기 안의 `return`을 생략하며, 순수 노드를 앞으로 끌어올린다(검토용으로만 쓴다). `CallFunction|GetAttackPower`가 `Class|SCAttributeSet|GetAttackPower`로 읽히는 등 이름도 틀릴 수 있다.
- Text 기본값의 한글: `OT set_properties {"PromptText":"상호작용"}` → 그대로 읽힌다.

### 캐릭터 베이스와 GA 기반 (2-3, 2-4)

- BP 컴포넌트 추가: `editor_toolset.toolsets.actor.ActorTools` `add_component {"owner":{"refPath":"/Game/SoulCombat/Characters/BP_CombatCharacterBase.BP_CombatCharacterBase"},"component_type":{"refPath":"/Script/GameplayAbilities.AbilitySystemComponent"},"name":"AbilitySystem"}` → `...BP_CombatCharacterBase_C:AbilitySystem_GEN_VARIABLE`. BP 컴포넌트 클래스도 된다: `"component_type":{"refPath":"/Game/SoulCombat/Components/AC_CombatComponent.AC_CombatComponent_C"}`. 그래프에서는 `Variables|Default|GetCombat`.
- Character 기본 컴포넌트 노드: 자기 BP 안에서는 `Variables|Character|GetMesh`, `GetCapsuleComponent`, `GetCharacterMovement`. **다른 BP(GA 등)에서 Character 참조로 읽을 때는 `Class|Character|GetMesh :self ch`** (`Variables|Character|GetMesh`는 `does not exist`).
- 다른 BP 컴포넌트의 함수/변수: `Class|ACCombatComponent|InitializeCombat :self combat`, `Class|ACCombatComponent|GetRespawnTransform`, `Class|ACCombatComponent|HitTargetsinFront`(표시 이름 대소문자 그대로, `in` 소문자).
- **함정**: 다른 객체의 impure 함수를 식 자리에 인라인으로 쓰면(`(return (Class|ACCombatComponent|GetAttackPower :self combat))`) exec가 연결되지 않아 컴파일 경고 `GetAttackPower was pruned because its Exec pin is not connected`. 먼저 `(bind ap (Class|ACCombatComponent|GetAttackPower :self combat))` 후 `(return ap)`.
- **함정**: 함수의 FunctionResult 노드를 전부 `delete_node`하면 출력 파라미터 정의도 사라진다(출력은 Result 노드에 저장). 그 상태로 `(return x)`를 쓰면 성공 반환이지만 Return 노드가 안 생긴다. 다시 쓰기 전에 `add_function_param ... "input_param":false`로 출력을 다시 만든다(FunctionResult는 지우지 않는 편이 낫다).
- **함정**: `get_node_type_pins`에 `Default|Assign<Disp>`를 넣으면 연결 없는 커스텀 이벤트 `<Disp>_Event`가 그래프에 남는다. `AddEvent|Ability|EventActivateAbility`처럼 이미 그래프에 있는 이벤트 타입을 넣으면 **기존 이벤트 노드가 사라진다**. 이벤트/Assign 타입은 핀 조회하지 않는다.
- `(Default|AssignOnDied :self combat)`는 `OnDied_Event (DeadActor)`를 만든다. 본문을 쓰는 두 번째 `write_graph_dsl` 뒤에 연결 없는 `OnDied_Event_0`, `OnRespawned_Event_0`이 또 생겼고, 지운 뒤 나중 호출에서 `_Event_1`이 한 번 더 생겼다. 마지막에 `find_nodes` + `get_node_infos`로 연결 0인 `*_Event_N`을 지운다.
- 핸들러 이벤트는 오버라이드 가능한 함수로 넘긴다: `(event Custom|OnDied_Event (DeadActor) (CallFunction|HandleDeath))`. 함수 호출이 `read_graph_dsl`에서 `Class|Damageable|HandleDeath`로 읽혀도 실제 노드는 self 호출이다(`get_node_infos`로 self 핀 타입 `Self Object Reference` 확인).
- 열거형 핀 기본값은 문자열: `:NewType "NoCollision"`/`"QueryAndPhysics"`, `:NewMovementMode "MOVE_Walking"`, `:LocationRule "KeepRelative"`, `:VelocityOnFinishMode "ClampVelocity"`. 프로필 이름은 `:InCollisionProfileName "Ragdoll"`.
- GA BP: `BT create` 부모 `/Script/GameplayAbilities.GameplayAbility`, 자식은 `"asset_type":{"refPath":"/Game/SoulCombat/GAS/Abilities/GA_SCBase.GA_SCBase_C"}`. 새 GA의 EventGraph에는 연결 없는 `ActivateAbility`, `OnEndAbility` 이벤트가 있다.
- GA CDO(`OT set_properties`, 컴파일 후): `{"instancingPolicy":"InstancedPerActor","abilityTags":{"gameplayTags":[{"tagName":"Ability.HitReact"}]},"abilityTriggers":[{"triggerTag":{"tagName":"Event.HitReact"},"triggerSource":"GameplayEvent"}],"cancelAbilitiesWithTag":{...},"activationOwnedTags":{...},"activationBlockedTags":{...},"bRetriggerInstancedAbility":true}` → true, `get_properties`로 그대로 읽혔고 컴파일 뒤에도 유지. 부모 CDO 값(instancingPolicy, activationBlockedTags)은 자식에 상속된다.
- GA 이벤트 DSL 헤드: `(event Ability|EventActivateAbility ...)`. 이벤트가 없으면 `BT add_event {"event_name":"K2_ActivateAbility"}`로 만든다.
- GA 노드 ID: `Ability|CommitAbility`(출력 ReturnValue bool), `Ability|EndAbility`, `Ability|GetAvatarActorfromActorInfo`, `Ability|Tasks|PlayMontageAndWait`(연속 `:then :OnCompleted :OnBlendedIn :OnBlendOut :OnInterrupted :OnCancelled`, 인자 `:MontageToPlay :Rate :StartSection`), `Ability|Tasks|WaitDelay :Time`(연속 `:then :OnFinish`), `Ability|Tasks|ApplyRootMotionConstantForce :TaskInstanceName :WorldDirection :Strength :Duration :bIsAdditive :VelocityOnFinishMode :ClampVelocityOnFinish :bEnableGravity`(연속 `:then :OnFinish`), `Animation|Montage|PlaySlotAnimationasDynamicMontage :self <AnimInstance> :Asset :SlotNodeName :BlendInTime :BlendOutTime :InPlayRate`, `Components|SkeletalMesh|GetAnimInstance`.
- 부모 GA의 출력 없는 함수는 자식에서 이벤트로 오버라이드된다(`AddEvent|EventFaceDesiredInput`이 목록에 나온다). 그래서 `OnActionStarted`, `OnHitFrame`은 일반 함수로 만들었다.
- if 뒤에 문장을 이어 쓰는 대신 분기 합류는 `Utilities|FlowControl|Sequence`로 만든다: `(Sequence (:then_0 (if c (X))) (:then_1 (Y) ...))`. 태스크 연속 `(:then)`, `(:OnFinish)`를 비워 두면 연결 없는 핀으로 남는다(경고 없음).
- `arrange_nodes`는 노드 높이를 모른다: 큰 태스크 노드(ApplyRootMotionConstantForce, PlayMontageAndWait)가 아래 노드와 겹쳐 배치됐고, EventGraph 일부만 넘기면 바깥 연결(디스패처 델리게이트 핀)에 끌려 흩어졌다. GA_ActionBase, GA_HitReact, BP_CombatCharacterBase EventGraph는 `set_node_position`으로 행/열을 직접 지정했다(노드 높이 추정: 핀 1개당 약 25-30 px). 또 `arrange_nodes`는 로그에 `LogBlueprint: Warning: No then pin found on node ...`를 남긴다. 컴파일 경고가 아니므로 `[Compiler]`가 붙은 줄만 본다.
- ProgrammaticToolset 스크립트 안에서 하나라도 실패하면 반환 dict가 사라진다(예: `get_node_type_pins "Variables|Character|GetMesh"` 실패 시 앞의 결과도 못 받음). 새 노드 ID는 `find_node_types`로 먼저 확인한다.

### 검증 중 확인한 함정 (2단계 검증)

- **`read_graph_dsl`이 그래프를 바꾼다**: `Default|Assign<Disp>` 노드가 있는 그래프(BP_CombatCharacterBase EventGraph)를 읽을 때마다 Assign 노드마다 연결 없는 커스텀 이벤트 `<Disp>_Event_N`이 새로 생긴다(확인: `find_nodes {"graph":G,"title":"","entry_points_only":true}` 두 번은 그대로, `read_graph_dsl {"graph":G}` 한 번 뒤 `K2Node_CustomEvent_20`, `_22` 추가). 그래서 "정리 → read_graph_dsl로 확인 → 저장" 순서면 스트레이 이벤트가 같이 저장된다. Assign이 있는 그래프는 read_graph_dsl을 먼저 하고, 그 뒤 `find_nodes` + `get_node_infos`로 연결 0인 `*_Event_N`을 지운 다음 저장한다. 검증은 read_graph_dsl 대신 `get_node_infos` 핀 연결로 한다.
- **`compile_blueprint`는 변경 없는 BP도 dirty로 만든다**: `is_dirty`가 false인 6개 BP를 `compile_blueprint {"warnings_as_errors":true}`만 한 뒤 전부 `is_dirty` true. 읽기 전용 검증에서 컴파일하면 저장 상태 확인을 먼저 해야 한다.
- 컴파일 결과는 `LogsToolset GetLogEntries {"pattern":"\[Compiler\]","category":"","maxEntries":100}`로 본다(패턴 `Compiler`만 쓰면 LogShaderCompilers 줄에 묻힌다).
- (재검증) Assign 노드가 없는 AC_CombatComponent도 `read_graph_dsl` 11개 그래프를 읽은 뒤 `is_dirty` true가 됐다(노드 수는 그대로). 반대로 깨끗하고 최신인 5개 BP는 `compile_blueprint {"warnings_as_errors":true}` 뒤에도 `is_dirty` false였다. 읽기 전용 검증은 `find_nodes` + `get_node_infos`로 연결을 덤프해서 하고(dirty 안 됨), read_graph_dsl은 꼭 필요할 때만 쓴다.
- 함수 출력 확인: `find_nodes(G,"")` → `get_node_infos`에서 `K2Node_FunctionResult_*`의 input_pins, 또는 다른 그래프의 호출 노드(`|ApplyHit`) output_pins를 본다. read_graph_dsl은 분기 안 return을 생략해서 출력이 없는지 알 수 없다.

### 기존 함수에 출력 추가와 Return 노드 (2단계 수정)

- 출력 추가: `BT add_function_param {"graph":{"refPath":"/Game/SoulCombat/Components/AC_CombatComponent.AC_CombatComponent:ApplyHit"},"param_name":"bGuarded","param_type":"bool","input_param":false}` → 새 `K2Node_FunctionResult_5`의 입력 PinID(index 1)를 준다. 이 노드는 exec가 연결되지 않은 채 (120,0)에 생긴다. 기존 본문을 다시 쓰지 않고 `connect_pins`로 exec와 값을 잇는다.
- Return 노드 추가(분기마다 하나): `BT create_node {"graph":G,"type_id":"|AddReturnNode...","pos":{"x":1150,"y":-250}}` → `K2Node_FunctionResult_N`, 출력 핀이 이미 있고 bool 기본값 `false`. `find_node_types {"type_id_filter":"ReturnNode"}`로 찾은 ID(점 세 개 포함 그대로).
- Sequence 핀 늘리기: `BT add_node_pin {"node":{"refPath":".../ApplyHit.K2Node_ExecutionSequence_1"}}` → `then_2` PinID(index 2). DSL은 then_0/then_1만 쓰지만 만든 뒤 핀 추가는 된다. 함수 끝 반환은 Sequence 마지막 핀에 둔다(앞 핀에서 Return하면 뒤 핀이 안 돈다).
- **함정**: 이미 호출되는 함수에 출력을 추가하면 기존 호출 노드가 갱신되지 않아 `compile_blueprint`가 `Could not find a pin for the parameter bGuarded of ApplyHit on  ApplyHit` 에러. 해결: 같은 그래프에 `create_node {"type_id":"CallFunction|ApplyHit"}`로 새 호출 노드를 만들고(새 출력 핀 포함) `get_node_infos`로 핀 index 확인 → 옛 노드 `delete_node` → `connect_pins`로 다시 연결. 다른 BP에 호출이 있으면 거기도 같은 처리가 필요하다.
- `arrange_nodes`는 같은 열 노드를 약 148 px 간격으로 쌓아 핀 많은 노드(MakeGameplayEventData 10핀, 입력 5-6개인 FunctionEntry)가 아래 노드와 겹친다. 정렬 뒤 핀 수 × 약 30 px로 높이를 어림해 `set_node_position`으로 아래 노드를 내린다.
- 스트레이 이벤트 정리 확인: `find_nodes {"graph":EventGraph,"title":"","entry_points_only":true}`는 그래프를 바꾸지 않는다. 정리 → `compile_blueprint` → `save_assets` 뒤에도 이벤트는 BeginPlay, OnDied_Event, OnRespawned_Event 3개만 남았다(read_graph_dsl은 쓰지 않음).
