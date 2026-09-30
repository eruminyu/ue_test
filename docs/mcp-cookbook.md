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

### 플레이어 어빌리티 (3-1)

- GA CDO 비용·쿨타임 클래스: `OT set_properties {"costGameplayEffectClass":"/Game/SoulCombat/GAS/Effects/GE_Cost_Dash.GE_Cost_Dash_C","cooldownGameplayEffectClass":"/Game/SoulCombat/GAS/Effects/GE_Cooldown_Dash.GE_Cooldown_Dash_C"}` → true, `get_properties`는 `{"refPath":...}`로 읽힌다. 태그를 비울 때는 `{"gameplayTags":[]}`.
- AnimMontage 오브젝트 변수: `add_object_variable ... "object_class":{"refPath":"/Script/Engine.AnimMontage"}`, 기본값은 경로 문자열 `{"GuardMontage":"/Game/Variant_Combat/Anims/AM_ChargedAttack.AM_ChargedAttack"}`. Name 배열: `add_variable {"type_name":"name","container_type":"ARRAY"}` + `{"ComboSections":["Melee01","Melee02","Melee03"]}`. float 배열도 같은 방식.
- 카테고리 `Combo|State`인 변수 노드 ID는 `Variables|Combo|State|GetComboStep`, bool은 b를 뗀 `Variables|Combo|State|SetInputBuffered`. (`read_graph_dsl`은 `|GetbPastChainPoint`처럼 틀리게 읽는다. 실제 노드는 정상.)
- 커스텀 이벤트는 `BT add_event {"event_name":"BeginStepTimers"}`로 먼저 만들고, 본문은 `(event Custom|BeginStepTimers ...)`, 호출은 `(CallFunction|BeginStepTimers)`. 한 번의 `write_graph_dsl`에 이벤트 3개를 같이 써도 된다.
- 배열 원소: `(Utilities|Array|Get(acopy) (Variables|Combo|GetStepRadii) idx)` — 괄호가 들어간 ID 그대로 쓰고 인자는 위치 인자(배열, 인덱스). 인덱스 리터럴 `0`은 핀 기본값이 된다.
- WaitGameplayEvent 반복: `(Ability|Tasks|WaitGameplayEvent :EventTag "(TagName=\"InputTag.Guard\")" :OnlyTriggerOnce false (:then ...) (:EventReceived ...))`. EventMagnitude는 `(bind (t i tg o o2 c it tt mag td) (Utilities|Struct|BreakGameplayEventData _payload))` 후 `mag` 사용(출력 10개, 순서대로).
- GA 노드: `(Ability|AddGameplayCueToOwner :GameplayCueTag "(TagName=\"GameplayCue.Guard.Active\")" :bRemoveOnAbilityEnd true)`, `(Ability|ExecuteGameplayCueOnOwner :GameplayCueTag ...)`, `(Ability|ApplyGameplayEffectToOwner :GameplayEffectClass "/Game/SoulCombat/GAS/Effects/GE_DashInvuln.GE_DashInvuln_C")`, `(Ability|Animation|MontageJumptoSection :SectionName x)`(self는 자동으로 GA), `(Character|Jump :self ch)`, `(CallFunction|FaceDirection :Direction v)`. Context 핀은 비워 둬도 컴파일 경고 없음.
- 새 GA의 기본 `OnEndAbility` 이벤트(`K2Node_Event_1`)는 안 쓰면 `delete_node`. PlayMontageAndWait의 `bStopWhenAbilityEnds` 기본 true라 End 시 몽타주 정지는 따로 안 만든다.
- 배치: `arrange_nodes`(이벤트 체인별) 뒤 ProgrammaticToolset로 열 간격을 다시 잡았다. arrange 결과의 같은 x를 한 열로 보고, 열 너비 = 노드 종류별 추정 너비(태스크 420, Break/Select/HitTargets 340, 일반 300, 변수 Get 230, 연산 180) 최댓값 + 90, 열 안에서는 y 순서를 유지하며 추정 높이(50 + 28 × 핀 행 수) + 40 간격으로 밀어 내림. 이벤트 체인끼리는 체인 높이 + 300씩 세로로 띄움. 같은 추정으로 겹침 검사 0건.

### 스킬 어빌리티, 검기 투사체, 어빌리티 세트 (3-1 스킬, 3-2, 3-3)

- **BP 자식의 기본 이벤트 주의**: GA_ActionBase(BP)의 자식을 `BT create`로 만들면 EventGraph에 `ActivateAbility` 이벤트 + 거기 연결된 `Parent: ActivateAbility`(`K2Node_CallParentFunction_0`, type_id `Ability|Parent:ActivateAbility`)와 `OnEndAbility`가 생긴다. 부모 흐름을 그대로 쓰는 자식(스킬 3종)은 셋 다 `delete_node`로 지웠다(남겨 두면 자식 오버라이드가 부모를 한 번 더 감싼다). 데이터만 다른 자식(GA_Skill_DashSlash)은 EventGraph가 비어 있다.
- **부모 BP 함수 오버라이드**: 출력 없는 부모 함수(`OnHitFrame`, `OnActionStarted`)는 자식에서 **이벤트**로만 오버라이드된다.
  - `BT add_function_graph {"graph_name":"OnHitFrame"}` → 에러 `"OnHitFrame" is an inherited event-shape function ...; it must be placed as an event node rather than a function graph.`
  - `BT add_event {"blueprint":<자식 BP>,"event_name":"OnHitFrame"}` → `K2Node_Event_N`(type_id `AddEvent|EventOnHitFrame`). DSL 헤드는 `(event EventOnHitFrame ...)`.
- **부모 호출(Call to Parent) 노드는 MCP로 못 만든다**: `find_node_types "Parent"`에 없고, `get_node_type_pins`/`create_node`에 `Default|Parent:OnHitFrame`, `Parent:OnHitFrame`, `|Parent:OnHitFrame`(read_graph_dsl이 읽어 주는 이름), `Ability|Parent:ActivateAbility`를 넣어도 `does not exist`. 우회(SlateInspector, 사람 개입 없음):
  1. `EditorToolset.EditorAppToolset` `OpenEditorForAsset {"assetPath":"/Game/SoulCombat/GAS/Abilities/GA_Skill_GroundSlam"}` → `SlateInspectorToolset` `Windows {"action":"list"}` → `Windows {"action":"select","index":<BP 창>}` → `Snapshot {"ref":"<창 ref>","maxDepth":40}`.
  2. 그래프 패널의 이벤트 노드는 텍스트가 없는 `image`로 보인다(노드 크기 171x62, 제목 줄 171x24). 제목 줄 image를 `Click {"ref":"i815","button":"right"}` → 새 창(제목 없음) `Snapshot` → `text "Add Call to Parent Function"`을 `Click`.
  3. `K2Node_CallParentFunction_1`(type_id `|Parent:OnHitFrame`)이 **연결 없이** 생긴다. `connect_pins`(이벤트 then index 1 → 부모 노드 execute index 0, 부모 then index 0 → 다음 노드 execute)로 잇는다.
  4. 뒤 노드는 `create_node {"type_id":"Ability|ExecuteGameplayCueOnOwner"}` + `set_pin_value`(GameplayCueTag index 2, `(TagName="GameplayCue.Skill.GroundSlam")`). 부모 노드를 DSL로 참조할 수 없어서, 이 그래프는 DSL 대신 노드 단위로 만들었다. read_graph_dsl은 `(event EventOnHitFrame (|Parent:OnHitFrame) (Ability|ExecuteGameplayCueOnOwner ...))`로 읽는다.
- GA 안에서 액터 스폰: `(bind proj (Game|SpawnActorfromClass :Class "/Game/SoulCombat/Combat/BP_WaveProjectile.BP_WaveProjectile_C" :SpawnTransform (Math|Transform|MakeTransform :Location loc :Rotation rot) :CollisionHandlingOverride "AlwaysSpawn" :Owner av))` → 노드가 `Game|SpawnActorBPWaveProjectile`로 바뀌고 반환 핀이 BP 타입이 되어 `(Class|BPWaveProjectile|Init :self proj ...)`에 바로 연결된다. 벡터 × float은 `(* fwd (Variables|Action|GetForwardOffset))` → `Math|Vector|vector*vector`로 읽히지만 컴파일 경고 없음.
- BP 컴포넌트 루트 교체: `ActorTools add_component`(Sphere `Hitbox`)는 DefaultSceneRoot 아래에 붙는다 → `set_parent_component {"component":<...:DefaultSceneRoot_GEN_VARIABLE>,"parent":<...:Hitbox_GEN_VARIABLE>}` → true, 컴파일 뒤 `get_root_component(CDO)` = Hitbox, DefaultSceneRoot는 사라짐. 그 뒤 `add_component`로 붙인 StaticMesh는 새 루트(Hitbox) 아래로 붙는다.
- 컴포넌트 값(`OT set_properties`, 인스턴스 = `...BP_X_C:<Name>_GEN_VARIABLE`): Sphere `{"SphereRadius":120,"bGenerateOverlapEvents":true}`(기본 프로필 OverlapAllDynamic), StaticMesh `{"StaticMesh":"/Game/LevelPrototyping/Meshes/SM_Cube.SM_Cube","RelativeScale3D":{"x":0.2,"y":1.6,"z":0.8},"OverrideMaterials":["/Game/SoulCombat/Materials/MI_SC_Portal.MI_SC_Portal"],"bGenerateOverlapEvents":false}`, 충돌 끄기 `{"BodyInstance":{"collisionProfileName":"NoCollision","collisionEnabled":"NoCollision"}}`(읽으면 profile/enabled 모두 NoCollision), ProjectileMovement `{"InitialSpeed":2000,"MaxSpeed":2000,"ProjectileGravityScale":0,"bRotationFollowsVelocity":false}`.
- 컴포넌트 이벤트 DSL: `add_component_bound_event` 뒤 `(event OnComponentBeginOverlap(Hitbox) (OverlappedComponent OtherActor OtherComp OtherBodyIndex bFromSweep SweepResult) ...)` 그대로 쓰기가 된다.
- **스폰 직후 겹침 함정(설계)**: SpawnActor 중에 초기 겹침의 BeginOverlap이 먼저 불리고 그다음에 Init이 돈다. 그래서 적중 로직을 함수 `TryHit(Target)`로 빼고, 오버랩 이벤트와 `Init` 끝(`(for a (Collision|GetOverlappingActors) (CallFunction|TryHit :Target a))`)에서 둘 다 호출했다. `Collision|GetOverlappingActors`는 같은 ID가 두 개(Actor/PrimitiveComponent)인데 DSL은 Actor 버전(순수, self=Actor)을 골랐다.
- 다른 BP의 impure 함수 bool 결과: `(bind ok (Class|ACCombatComponent|IsValidTarget :self sc :Target t))` 후 `(if ok ...)`.
- SCAbilitySet 데이터 에셋: `DataAssetTools create {"asset_type":{"refPath":"/Script/SoulCombat.SCAbilitySet"}}` → `OT set_properties`:
  `{"Abilities":[{"ability":"/Game/SoulCombat/GAS/Abilities/GA_Player_BasicAttack.GA_Player_BasicAttack_C","inputTag":{"tagName":"InputTag.Attack"},"level":1}, ...],"StartupEffects":["/Game/SoulCombat/GAS/Effects/GE_Regen_Player.GE_Regen_Player_C"],"AttributeTable":"/Game/SoulCombat/GAS/Data/DT_Attr_Player.DT_Attr_Player"}` → true. 빈 태그는 `{"tagName":"None"}`(읽을 때도 `"None"`). 클래스는 `{"refPath":"..._C"}`로 읽힌다.
- `read_graph_dsl`(Assign 없는 함수 그래프)만 해도 GA_ActionBase가 dirty가 됐다. 저장 전 `is_dirty`로 확인해서 함께 저장했다(노드 변화 없음).

### 플레이어 캐릭터, 컨트롤러, 게임 모드와 PIE 스모크 테스트 (3-4 ~ 3-6)

- **상속 컴포넌트 값 덮어쓰기(자식 BP)**: 자식 BP 클래스 경로에 부모 컴포넌트 이름을 붙인 ref가 자식 전용 템플릿(Inheritable Component Handler)으로 해석된다. `BT create`(부모 BP_CombatCharacterBase_C) → `compile_blueprint` → `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/Characters/BP_PlayerCharacter.BP_PlayerCharacter_C:Combat_GEN_VARIABLE"},"values":"{\"AbilitySet\":\"/Game/SoulCombat/GAS/Data/DA_AbilitySet_Player.DA_AbilitySet_Player\",\"TeamTag\":{\"tagName\":\"Team.Player\"},\"bRespawnOnDeath\":true}"}` → true. 부모 `BP_CombatCharacterBase_C:Combat_GEN_VARIABLE` 값은 그대로(Team.Enemy, None, false)이고 부모 is_dirty도 false, 자식만 dirty. 컴파일·저장 뒤에도 유지되고 PIE에서 실제로 적용됐다(어빌리티 8개, Team.Player 태그). BeginPlay 오버라이드 우회는 필요 없었다.
  - 주의: `ActorTools get_components(자식 CDO)`는 계속 부모 경로(`BP_CombatCharacterBase_C:Combat_GEN_VARIABLE`)를 돌려준다. 그 경로에 쓰면 부모(=모든 자식)가 바뀐다. 반드시 자식 클래스 경로로 쓴다.
- Character 기본 컴포넌트는 자식 CDO 서브오브젝트로 쓴다: `...Default__BP_PlayerCharacter_C:CharacterMesh0` `{"SkeletalMeshAsset":"/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple.SKM_Quinn_Simple","AnimClass":"/Game/Variant_Combat/Anims/ABP_Manny_Combat.ABP_Manny_Combat_C","RelativeLocation":{"x":0,"y":0,"z":-89},"RelativeRotation":{"pitch":0,"yaw":-90,"roll":0}}`, `:CollisionCylinder` `{"CapsuleRadius":35,"CapsuleHalfHeight":90}`, `:CharMoveComp` `{"bOrientRotationToMovement":true,"RotationRate":{"pitch":0,"yaw":720,"roll":0},"MaxWalkSpeed":600,"JumpZVelocity":600,"AirControl":0.35}`, CDO `{"bUseControllerRotationYaw":false}`. 모두 true, get_properties로 확인.
- 카메라: `ActorTools add_component {"owner":<BP>,"component_type":{"refPath":"/Script/Engine.SpringArmComponent"},"name":"CameraBoom"}`(루트 캡슐 아래) → `add_component {"owner":{"refPath":"...BP_PlayerCharacter_C:CameraBoom_GEN_VARIABLE"},"component_type":{"refPath":"/Script/Engine.CameraComponent"},"name":"FollowCamera"}`(붐 아래, `get_parent_component`로 확인). 붐 값 `{"TargetArmLength":450,"bUsePawnControlRotation":true,"SocketOffset":{"x":0,"y":0,"z":60},"bEnableCameraLag":true}`. `AttachParent`는 get_properties로 못 읽는다(에러).
- 새 Character 자식 BP의 EventGraph에는 `BeginPlay` + `Parent: BeginPlay`(연결됨), `ActorBeginOverlap`, `Tick`이 있다. 부모 흐름만 쓰면 넷 다 `delete_node`.
- **Enhanced Input 이벤트 노드(컨트롤러 BP)**: type_id `Input|EnhancedActionEvents|IA_Move`(`find_node_types "IA_Move"`로 찾는다. 에셋 이름만 쓰고 /Game/Input/Actions와 /Game/SoulCombat/Input 모두 같은 형식). `create_node {"graph":EventGraph,"type_id":"Input|EnhancedActionEvents|IA_Jump","pos":{...}}` → `K2Node_EnhancedInputAction_N`. 출력 핀 index: Triggered 0, Started 1, Ongoing 2, Canceled 3, Completed 4, ActionValue 5, ElapsedSeconds 6, TriggeredSeconds 7, InputAction 8. 자기 함수 호출은 `create_node "CallFunction|PressCombatInput"`(execute 0, self 1, InputTag 2) → `connect_pins`(이벤트 Started → execute, ActionValue → Value) → 태그는 `set_pin_value "(TagName=\"InputTag.Jump\")"` → `compile_blueprint`. 13개 연결을 ProgrammaticToolset 한 스크립트로 만들었고, 핀은 `get_node_infos`에서 이름으로 찾았다. 컴파일 경고 없음.
- 매핑 컨텍스트 추가(DSL): `(bind isLocal (Pawn|IsLocalPlayerController)) (if isLocal (bind sub (LocalPlayerSubsystems|GetEnhancedInputLocalPlayerSubsystem)) (Input|AddMappingContext :self sub :MappingContext "/Game/Input/IMC_Default.IMC_Default" :Priority 0) ...)`. 서브시스템 노드는 `K2Node_GetSubsystem`(PC 문맥, 입력 핀 없음). AddMappingContext의 self는 인터페이스 핀이지만 바로 연결된다.
- 컨트롤러 노드 ID: `Pawn|GetControlledPawn`, `Pawn|GetControlRotation`(self Controller), `Pawn|Input|AddMovementInput :self p :WorldDirection v :ScaleValue f`, `Pawn|Input|AddControllerYawInput :self p :Val f`, `Pawn|Input|AddControllerPitchInput`, `Math|Vector2D|BreakVector2D`(`(bind (vx vy) ...)`), `Math|Rotator|MakeRotator :Yaw`, `Math|Vector|GetForwardVector rot`, `Math|Vector|GetRightVector rot`, `Math|Vector|Normalize`. 다른 컴포넌트 변수 쓰기: `(Class|ACCombatComponent|SetDesiredFacing :self c :DesiredFacing v)`(값을 생략하면 0 벡터). 오브젝트를 반환하는 함수에서 `(:"Is Not Valid" (return))`은 값 없는 Return 노드를 만든다(None 반환).
- GameMode CDO: `OT set_properties {"DefaultPawnClass":"/Game/SoulCombat/Characters/BP_PlayerCharacter.BP_PlayerCharacter_C","PlayerControllerClass":"/Game/SoulCombat/Core/BP_SCPlayerController.BP_SCPlayerController_C"}` → true.
- **스모크 테스트 레벨**: `AT duplicate {"path":"/Engine/Maps/Templates/Template_Default","new_path":"/Game/_Scratch/L_Smoke"}` → `save_assets ["/Game/_Scratch/L_Smoke"]` → (현재 레벨 `is_dirty` false 확인) `SceneTools load_level` → 모달 없음. WorldSettings는 `find_actors {"name":"","tag":"","collision_channels":[],"actor_type":{"refPath":"/Script/Engine.WorldSettings"}}` → `...L_Smoke:PersistentLevel.WorldSettings_1`에 `{"DefaultGameMode":"/Game/SoulCombat/Core/BP_SCGameModeBase.BP_SCGameModeBase_C"}` → 저장.
- **PIE 액터 찾기**: `StartPIE {"options":{"bSimulate":false,"playMode":"PlayMode_InViewPort","warmupSeconds":3}}` 뒤 `SceneTools find_actors`(actor_type = BP 클래스)가 PIE 월드 액터 `/Game/_Scratch/UEDPIE_0_L_Smoke.L_Smoke:PersistentLevel.BP_PlayerCharacter_C_0`를 돌려준다. 이 ref를 `AbilitySystemInspectorToolset GetGrantedAbilities/GetAttributeValues/GetActiveEffects/GetActiveTags {"actor":...}`에 그대로 넣으면 된다. GE 이름은 `Default__GE_Regen_Player_C`로 나온다.
- PIE 로그 수집: `GetLogEntries {"pattern":"","category":"","maxEntries":600}`에서 마지막 `StartPIE` 줄 뒤만 잘라 Error/Warning을 거른다. 패턴 `Error|Warning`에 시각 비교로 거르면 시각 없는 콜스택 줄(`\tFunction ...RaiseScriptError`)이 섞인다.
- PIE 뒤 `AC_CombatComponent`가 dirty였다(컨트롤러 그래프에서 `Class|ACCombatComponent|...` 노드를 조회·생성했기 때문으로 추정, 내용 변화 없음). 끝에 `/Game/SoulCombat` 전체 `is_dirty`를 보고 경로를 명시해 저장한다.

### 이름이 같은 InputAction의 Enhanced Input 이벤트 (3단계 수정)

- **함정**: `find_node_types "IA_Dash"`가 `Input|EnhancedActionEvents|IA_Dash`를 **두 번** 돌려준다(/Game/Variant_Platforming/Input/Actions/IA_Dash와 /Game/SoulCombat/Input/IA_Dash). type_id가 에셋 이름만 담아서 `create_node`는 항상 템플릿(Variant_Platforming) 쪽을 만든다. `declaring_class`로 못 가른다: IA 에셋 경로는 `is not valid Class for property 'declaring_class'` 에러, `/Script/EnhancedInput.InputAction`은 효과 없음. 같은 액션 노드가 이미 있으면 `create_node`는 새 노드 대신 기존 노드 ref를 돌려준다. 노드의 `InputAction`은 ObjectTools로 못 읽고 못 쓴다(`list_properties`에 errorMsg만).
- 확인: `get_node_infos` 출력 핀 `InputAction`(index 8)의 value, 또는 `AT get_dependencies {"asset_path":"/Game/SoulCombat/Core/BP_SCPlayerController"}`에 템플릿 IA 경로가 있는지.
- 우회(T3D 붙여넣기, 사람 개입 없음):
  1. `EditorAppToolset OpenEditorForAsset {"assetPath":"/Game/SoulCombat/Core/BP_SCPlayerController"}` → `SlateInspectorToolset Windows {"action":"select","index":<BP 창>}` → 창이 작으면 `Click` Maximize 버튼 → `tab "EventGraph"` 클릭 → 그래프 패널 splitter를 `Snapshot {"maxDepth":40}`.
  2. 잘못된 노드 제목 `text "EnhancedInputAction IA_Dash"`를 `Click` → `PressKey {"key":"Ctrl+C"}` → PowerShell `Get-Clipboard -Raw`.
  3. 텍스트에서 `/Game/Variant_Platforming/Input/Actions/IA_Dash.IA_Dash`(InputAction=와 핀 DefaultObject 두 곳)를 `/Game/SoulCombat/Input/IA_Dash.IA_Dash`로 바꾸고, `Name="..._13" ExportPath="..."`를 `Name="K2Node_EnhancedInputAction_20"`으로 바꾼다 → `BT delete_node`로 옛 노드 삭제 → `Set-Clipboard`.
  4. 다시 `Snapshot` → `text "BLUEPRINT"`(워터마크) `Click` → `PressKey Ctrl+V` → `K2Node_EnhancedInputAction_20` 생성, InputAction 핀 값 `/Game/SoulCombat/Input/IA_Dash.IA_Dash`, 핀 9개 정상, 위치는 붙여넣기 지점(4240,4000).
  5. `connect_pins`(Started index 1 → PressCombatInput execute index 0) → `set_node_position`으로 원래 자리 → `compile_blueprint {"warnings_as_errors":true}` → `save_assets`. 이후 `get_dependencies`에 Variant_Platforming 없음.
- 예방: 새 IA 이름이 템플릿 IA와 겹치는지 먼저 `find_node_types`로 본다(결과가 두 개면 위 우회가 필요). 이번 프로젝트에서 겹친 것은 IA_Dash뿐이었다(IA_Jump/IA_Move/IA_MouseLook은 의도대로 /Game/Input/Actions 템플릿 액션).

### 중간 테스트 맵 (3-7)

- `AT duplicate {"path":"/Engine/Maps/Templates/Template_Default","new_path":"/Game/SoulCombat/Maps/L_CombatField"}` → `save_assets` → (현재 레벨 `is_dirty` false 확인) `SceneTools load_level` → 모달 없음. Template_Default에는 이미 `PlayerStart_0`가 있어 따로 추가하지 않았다. `WorldSettings_1`에 `{"DefaultGameMode":"/Game/SoulCombat/Core/BP_SCGameModeBase.BP_SCGameModeBase_C"}` → 저장 → `get_dependencies`에 `/Game/SoulCombat/Core/BP_SCGameModeBase`가 나온다.

### 게임 흐름과 UI 허브 (6단계 1부: BP_SCGameInstance, 컨트롤러 UI 허브, BP_FieldGameMode)

- **GameInstance BP**: `BT create {"folder_path":"/Game/SoulCombat/Core","asset_name":"BP_SCGameInstance","asset_type":{"refPath":"/Script/Engine.GameInstance"}}` → EventGraph가 비어 있다(기본 이벤트 없음). `Game|OpenLevel(byName)`(입력 `LevelName` Name, `bAbsolute` 기본 true, `Options`)는 WorldContext 핀 없이 바로 쓰이고 컴파일 경고 없음. 문자열 조립: `(Utilities|String|ToString(Name) x)`, `(Utilities|String|Append :A a :B "#")`(A/B 2핀, 문자열 리터럴은 핀 기본값), `(Utilities|String|StringToName s)`.
- **네이티브 BlueprintNativeEvent 오버라이드(반환값 있음)**: `BT add_function_graph {"blueprint":<BP_FieldGameMode>,"graph_name":"ChoosePlayerStart"}` → 오버라이드 그래프가 생기고 FunctionEntry(출력 `Player` Controller)와 FunctionResult(`ReturnValue` Actor)가 **이미 연결된 채** 들어 있다. 본문은 `(fn ChoosePlayerStart (Player) ... (return s))`로 쓰면 된다(기존 FunctionResult_0은 DSL이 지우고 분기마다 Return 노드를 새로 만듦, 출력 정의는 유지). 출력 없는 BP 부모 함수(OnHitFrame)와 달리 반환값 있는 네이티브 이벤트는 함수 그래프로 오버라이드된다. 부모 호출은 여전히 MCP로 못 만든다.
  - 쓴 DSL: `(bind starts (Actor|GetAllActorsOfClass :ActorClass "/Script/Engine.PlayerStart")) (for s starts (if (== (Class|PlayerStart|GetPlayerStartTag :self s) (Variables|Flow|GetFieldStartTag)) (return s))) (if (> (Utilities|Array|Length starts) 0) (return (Utilities|Array|Get(acopy) starts 0)) (else (return)))` → 배열 타입이 `Array of Player Start Object References`로 바뀌고, `for` 뒤 문장은 ForEachLoop `Completed`에 붙는다. `Name == Name`은 `Utilities|Name|Equal(Name)`으로 만들어진다.
  - 새 GameModeBase 자식 BP의 EventGraph에는 연결 없는 BeginPlay/Tick(`K2Node_Event_0/1`)이 있어 `delete_node`로 지웠다.
- **위젯 생성(DSL)**: `(bind w (UserInterface|CreateWidget :Class "/Game/SoulCombat/UI/WBP_DungeonEntry.WBP_DungeonEntry_C" :OwningPlayer self))` → 반환 핀이 해당 WBP 타입이 되어 `(Class|WBPDungeonEntry|Setup :self w ...)`, 위젯 변수 Set, 함수 반환(`(return w)`)에 바로 연결된다. 이어서 `(UserInterface|Viewport|AddtoViewport :self w :ZOrder 10)`, `(Widget|RemovefromParent :self w)`.
- 입력 모드/커서(PlayerController BP): `(Input|SetInputModeUIOnly :PlayerController self :InWidgetToFocus w)`, `(Input|SetInputModeGameAndUI :PlayerController self :InWidgetToFocus w)`, `(Input|SetInputModeGameOnly :PlayerController self)`, `(Variables|MouseInterface|SetShowMouseCursor :bShowMouseCursor true)`. 게임 인스턴스: `(bind gi (Utilities|Casting|CastToBP_SCGameInstance :Object (Game|GetGameInstance)) (:then (Class|BPSCGameInstance|EnterDungeon :self gi :LevelName x)) (:CastFailed))`.
- 다른 WBP 함수 ID: `Class|WBPPlayerHUD|BindtoPawn`(표시 이름, `to` 소문자), `Class|WBPPlayerHUD|ShowInteractPrompt :Key :Action`, `Class|WBPDungeonClear|Setup :ClearSeconds`. `read_graph_dsl`은 WBP Setup을 `Class|WBPAttributeBar|Setup`, HUD 함수를 `CallFunction|ShowBossBar`로 틀리게 읽지만 실제 노드는 맞다(get_node_infos self 타입으로 확인).
- **함수 안에서 위젯 디스패처 바인딩**: `Default|Assign<Disp>`는 `find_node_types`에서 **EventGraph에만** 나온다(함수 그래프에서는 BindEventto/Call/Unbind만). 그래서 EventGraph에 인자 없는 커스텀 이벤트를 만들고(`add_event {"event_name":"BindEntryWidget"}`) 거기서 `(event Custom|BindEntryWidget (bind w (Variables|UI|GetEntryWidget)) (Default|AssignOnConfirmed :self w) (Default|AssignOnCancelled :self w))`로 바인딩, 함수(OpenDungeonEntry)에서는 위젯을 변수에 저장한 뒤 `(CallFunction|BindEntryWidget)`로 호출했다. 자동 생성된 `OnConfirmed_Event` 등의 본문은 두 번째 write로 `(event Custom|OnConfirmed_Event (CallFunction|HandleEntryConfirmed))`. 이번에는 두 번의 write 뒤 스트레이 `*_Event_N`이 생기지 않았다(EventGraph에 read_graph_dsl을 쓰지 않음).
- **기존 체인 뒤에 잇기**: 이미 있는 BeginPlay 체인(EI 이벤트와 같은 그래프)은 DSL로 다시 쓰지 않고, 새 로직을 함수(InitHUD)로 만든 뒤 `create_node {"type_id":"CallFunction|InitHUD"}` → 마지막 노드의 `then` → 새 노드 `execute`를 `connect_pins`로 이었다. 같은 EventGraph에 다른 이벤트(`EventOnPossess`, 커스텀 이벤트)를 write_graph_dsl로 추가해도 기존 BeginPlay/EI 노드 연결은 그대로였다(get_node_infos로 전후 비교).
- OnPossess 오버라이드: `add_event {"event_name":"ReceivePossess"}` → type_id `AddEvent|EventOnPossess`, 출력 `PossessedPawn`. DSL 헤드 `(event EventOnPossess (PossessedPawn) ...)`.
- 오브젝트 변수를 None으로: `(Variables|UI|SetEntryWidget)`(값 생략). Object `==`는 `Utilities|Equal(Object)`.
- **프로젝트 설정**: `ConfigSettingsToolset.ConfigSettingsToolset` `SetSectionProperties {"containerName":"Project","categoryName":"Project","sectionName":"Maps","propertiesJson":"{\"GameInstanceClass\":{\"refPath\":\"/Game/SoulCombat/Core/BP_SCGameInstance.BP_SCGameInstance_C\"},\"GlobalDefaultGameMode\":{\"refPath\":\"/Game/SoulCombat/Core/BP_SCGameModeBase.BP_SCGameModeBase_C\"}}"}` → true, `SoulCombat/Config/DefaultEngine.ini`의 `[/Script/EngineSettings.GameMapsSettings]`에 바로 기록된다. 읽기는 `GetSectionPropertyValues`(같은 섹션, `propertyNames` 배열), 맵 키는 `GameDefaultMap`, `EditorStartupMap`.
- **배치 스크립트(arrange_nodes 대신)**: `arrange_nodes`가 함수 Entry를 오른쪽으로 보내거나 순수 노드를 흩뜨려서, ProgrammaticToolset 스크립트로 직접 배치했다. exec 출력을 DFS로 따라가며 첫 exec 출력은 같은 줄(x += 추정 너비 + 80), 나머지 exec 출력(else, then_1, Completed, CastFailed)은 새 줄. 각 줄의 순수 노드(연결된 비-exec 입력을 재귀 수집)는 그 줄 exec 노드 아래 한 줄(y = 줄 위 + 최대 exec 높이 + 40)에 소비 노드 왼쪽부터 차례로 둔다. 줄 간격 60, 이벤트 체인 간격 120. 추정 크기(너비: 노드 종류별 기본값과 7 × (가장 긴 입력 핀 이름 + 가장 긴 출력 핀 이름) + 90 중 큰 값, 높이 50 + 28 × 핀 행)로 겹침 0 확인. 순수 노드 체인이 길고 exec 노드가 적은 함수(ReturnToField)는 왼쪽 음수 x로 밀리므로 수동 배치했다.

### 던전 문과 게이트 (6단계 2부: BP_DungeonDoor, BP_DungeonGate)

- **메시 피벗 확인**: `editor_toolset.toolsets.static_mesh.StaticMeshTools` `get_bounds {"mesh":{"refPath":"/Game/LevelPrototyping/Meshes/SM_Cube.SM_Cube"}}` → `min (0,0,0) max (100,100,100)`: SM_Cube는 **모서리 피벗**이다. 크기 (sx,sy,sz)를 중심 (cx,cy), 바닥 z0에 두려면 `RelativeLocation = (cx - sx/2, cy - sy/2, z0)`, `RelativeScale3D = (sx/100, sy/100, sz/100)`. SM_Plane은 `(-50,-50,0)~(50,50,0)`(중앙 피벗, XY 평면, 법선 +Z). 세워서 +X를 보게 하려면 `"RelativeRotation":{"pitch":-90,"yaw":0,"roll":0}` → 로컬 X가 높이(-Z), 로컬 Y가 폭이 되므로 높이 400 × 폭 500은 `"RelativeScale3D":{"x":4,"y":5,"z":1}`.
- **루트를 이름 있는 SceneComponent로**: `ActorTools add_component {"owner":<BP>,"component_type":{"refPath":"/Script/Engine.SceneComponent"},"name":"Root"}` → `set_parent_component {"component":{"refPath":"...BP_X_C:DefaultSceneRoot_GEN_VARIABLE"},"parent":{"refPath":"...BP_X_C:Root_GEN_VARIABLE"}}` → true → `compile_blueprint` → `get_components {"actor":{"refPath":"/Game/.../BP_X.Default__BP_X_C"}}`에 Root만 남음(CDO 경로는 `패키지.Default__BP_X_C`. `BP_X_C:Default__...`는 `is not valid Actor` 에러). 이후 `add_component`는 Root 아래로 붙는다. 새 Actor BP의 StaticMesh 컴포넌트는 Mobility가 이미 `Movable`로 읽혔다.
- 컴포넌트 값: `{"Mobility":"Movable"}`, `{"bHiddenInGame":true}`, Box `{"BoxExtent":{"x":40,"y":240,"z":200}}`, Sphere `{"SphereRadius":450}`, BP 컴포넌트(AC_Interactable) 템플릿 `...BP_DungeonGate_C:Interactable_GEN_VARIABLE`에 `{"PromptKey":"F","PromptText":"게이트 열기"}` → 부모 AC_Interactable CDO 값은 그대로.
- **처음엔 꺼 둔 오버랩 트리거**: `{"BodyInstance":{"collisionProfileName":"OverlapAllDynamic","collisionEnabled":"NoCollision"}}`도 true로 읽히지만, 이름 있는 프로필은 로드 시 프로필 값(QueryOnly)으로 다시 채워질 수 있어 `{"BodyInstance":{"collisionProfileName":"Custom","collisionEnabled":"NoCollision","objectType":"ECC_WorldDynamic"}}`로 바꿨다. 기존 반응(전부 Overlap, Pawn 포함)은 `collisionResponses.responseArray`에 그대로 남는다. 그래도 BeginPlay에서 `(Collision|SetCollisionEnabled :self (Variables|Default|GetPortalTrigger) :NewType "NoCollision")`로 한 번 더 끈다. 켤 때는 `:NewType "QueryOnly"`.
- 노드 ID: `Components|MoveComponentTo`(입력 exec `Move`/`Stop`/`Return`, DSL 호출은 `Move`에 연결. 인자 `:Component :TargetRelativeLocation :bEaseOut :bEaseIn :OverTime`, 출력 `then`은 이동이 **끝난 뒤** 나간다), `Development|SetHiddeninGame :self comp :NewHidden false`(표시 이름은 SetHiddenInGame), `Class|SceneComponent|GetRelativeLocation :self comp`(변수 Get 노드로 만들어짐), `Transformation|SetRelativeLocation :self comp :NewLocation v :bTeleport true`, `Game|GetPlayerPawn :PlayerIndex 0`, `Game|GetPlayerController :PlayerIndex 0`, `Transformation|GetActorForwardVector`, `Transformation|GetActorRotation`, `Transformation|SetActorLocationAndRotation :self pawn :NewLocation :NewRotation :bTeleport true`, `Pawn|SetControlRotation :self pc :NewRotation rot`(참조 핀이라 bind한 값을 연결), 다른 컴포넌트 bool 변수 `Class|ACInteractable|SetEnabled :self ia :bEnabled false`(VariableSet 노드로 만들어짐).
- `(- d)`(단항 마이너스, float)는 `Math|Float|float-float`(A 기본값 0, B=d) 노드가 된다. 컴파일 경고 없음.
- **같은 컴포넌트를 여는/닫는 두 MoveComponentTo 노드는 서로 다른 latent 액션**이라 이동 중 반대 명령이 오면 둘이 겹친다. 문은 목표 위치 변수(TargetLocation)를 두고 커스텀 이벤트 `MoveDoor` 하나의 MoveComponentTo 노드를 OpenDoor/CloseDoor가 같이 쓰게 했다.
- 반환 위젯의 디스패처 바인딩(EventGraph): `(bind w (Class|BPSCPlayerController|OpenDungeonEntry :self pc :Title t :Description d :LevelName n)) (Default|AssignOnCancelled :self w)` → `OnCancelled_Event` 자동 생성·연결. `find_node_types "AssignOnCancelled"`는 `EventDispatchers|AssignOnCancelled` 2개와 `Default|AssignOnCancelled`를 돌려주는데 `Default|`가 WBP 쪽이다. 본문은 두 번째 write_graph_dsl로 `(event Custom|OnCancelled_Event ...)`. 컴포넌트 디스패처도 같은 방식: `(Default|AssignOnInteracted :self (Variables|Default|GetInteractable))` → `(event Custom|OnInteracted_Event (Interactor) ...)`.
- **find_nodes entry_points_only에 latent 노드가 섞인다**: 이 옵션이 이벤트뿐 아니라 `Components|MoveComponentTo` 호출 노드도 돌려준다. 배치 스크립트 루트는 이벤트 노드 이름을 직접 지정한다.
- 이번에도 read_graph_dsl(Assign 2개가 있는 EventGraph) 한 번에 `OnInteracted_Event_0`, `OnCancelled_Event_0`이 생겼다 → 연결 0 노드 검사로 찾아 delete_node → 재컴파일 → 저장.
- BP 변수 기본값 고치기(이미 있는 변수): `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/Dungeon/BP_DungeonGate.Default__BP_DungeonGate_C"},"values":"{\"ReturnDistance\":300}"}` → true, `compile_blueprint` 뒤에도 CDO 값 유지. 컴포넌트 템플릿 값은 `...BP_X.BP_X_C:<Name>_GEN_VARIABLE`에 같은 방식(`{"SphereRadius":400}`). 그래프를 건드리지 않으니 모달·스트레이 노드 없음.

### 레벨 로직 액터 배치와 맵 설정 (7단계 2부: 게이트·문 배치)

- **레벨 액터 목록**: ProgrammaticToolset로 `SceneTools find_actors {"name":"","tag":"","collision_channels":[]}` → 각 액터에 `ActorTools get_label`, `get_actor_transform`, `get_actor_bounds`. 스크립트에서 반환 dict는 `_StrictDict`라 `.get(key, default)`가 에러다(`tr['location']`처럼 직접 접근).
- **PlayerStart 태그**는 액터 Tags(`ActorTools get_tags`는 `[]`)가 아니라 프로퍼티다: `OT get_properties {"instance":{"refPath":"/Game/SoulCombat/Maps/L_CombatField.L_CombatField:PersistentLevel.PlayerStart_0"},"properties":["PlayerStartTag"]}` → `{"PlayerStartTag":"FieldStart"}`.
- **BP 액터 배치**: `SceneTools add_to_scene_from_class {"actor_type":{"refPath":"/Game/SoulCombat/Dungeon/BP_DungeonGate.BP_DungeonGate_C"},"name":"DungeonGate","xform":{"location":{"x":0,"y":2200,"z":20},"rotation":{"pitch":0,"yaw":-90,"roll":0}}}` → `...PersistentLevel.BP_DungeonGate_C_0`. `name`이 그대로 라벨이 된다(`get_label` 확인, `set_label` 불필요). 폴더는 `SceneTools set_actor_folder {"actor":<ref>,"folder_path":"Field/Gate"}`(없으면 만들어짐, `get_actors_in_folder`로 확인).
- **인스턴스 변수(인스턴스 편집 가능 BP 변수)**: 레벨 액터 ref에 `OT set_properties {"instance":<액터 ref>,"values":"{\"bStartOpen\":true}"}` → true, `get_properties`로 확인.
- **액터 bounds는 모든 컴포넌트 합**: 게이트 bounds에는 InteractSphere(반경 400)가 들어가 y 1650~2450으로 나온다. 문(BP_DungeonDoor)은 메시 하나라 bounds = 문짝 크기(50×600×500)로, 벽 틈(`*_Wall_*_a/_b` bounds의 x 범위, y -300~300)과 그대로 비교할 수 있었다. 문 원점 = 벽 중심 x(예: Start 동쪽 벽 x 600~650 → 625), y 0, z 0, yaw 0.
- **WorldSettings 게임 모드**: `OT set_properties {"instance":{"refPath":"<맵>.<맵>:PersistentLevel.WorldSettings_1"},"values":"{\"DefaultGameMode\":\"/Game/SoulCombat/Core/BP_FieldGameMode.BP_FieldGameMode_C\"}"}` → 읽으면 `{"refPath":...}`.
- **시작 맵**: `ConfigSettingsToolset SetSectionProperties {"containerName":"Project","categoryName":"Project","sectionName":"Maps","propertiesJson":"{\"EditorStartupMap\":{\"refPath\":\"/Game/SoulCombat/Maps/L_CombatField.L_CombatField\"},\"GameDefaultMap\":{\"refPath\":\"/Game/SoulCombat/Maps/L_CombatField.L_CombatField\"}}"}` → true, DefaultEngine.ini에 바로 기록.
- **PIE 확인**: `find_actors`에 `actor_type` `/Script/Engine.GameModeBase`, `/Script/Engine.PlayerController`, BP 캐릭터 클래스를 주면 PIE 월드(`UEDPIE_0_...`) 액터가 나온다. 컨트롤러 BP 변수도 읽힌다: `OT get_properties {"instance":<PIE PC>,"properties":["HUD"]}` → `/Engine/Transient.UnrealEdEngine_0:BP_SCGameInstance_C_0.WBP_PlayerHUD_C_0`(위젯 존재 확인). PIE 로그는 `Creating play world package` 줄 뒤만 보고 LogAudio 경고(장치 문제)는 제외한다.
- 스크린샷 툴(CaptureViewport 등)은 base64를 응답으로만 돌려주고 파일로 저장하는 툴이 없다(AssetTools write_file은 텍스트 전용). 컨텍스트를 아끼려면 프로퍼티·로그 검사로 대신한다.

### 그래프 정리·주석 패스 (9단계 파일럿: BP_DungeonDoor, AC_CombatComponent, GA_Player_BasicAttack)

전체 절차는 `docs/comment-pass-recipe.md`. 도구 `Tools/graph_layout.py`(dump/layout/rows/apply/same-logic), `Tools/graph_comments.py`(preview/ui-run/ui-shot/ui-close).
- **MCP를 HTTP로 직접 부르기(8000번 메인 에디터)**: `python Tools/mcp_http.py --port 8000 --out f.txt call <toolset> <tool> '<json>'` — 덤프·스냅샷·스크린샷처럼 큰 결과를 파일로 받는다. Git Bash에서는 `export MSYS_NO_PATHCONV=1`(안 하면 `/Game/...` 인자가 `C:/Program Files/Git/Game/...`으로 바뀌어 `is not valid Blueprint` 에러).
- **그래프 덤프(그래프를 바꾸지 않음)**: ProgrammaticToolset 스크립트 한 번에 `list_graphs` → 그래프마다 `find_nodes {"graph":G,"title":"","entry_points_only":false}` → `get_node_infos {"nodes":[...]}`. 핀 `type_id`는 exec가 `"Exec"`, 그 밖에 `"Boolean"`, `"Actor Object Reference"` 등. 두 덤프의 노드·연결·핀 값 비교로 "위치만 바뀌었는지" 검증한다(`graph_layout.py same-logic`).
- **그래프 패널 포커스**: SlateInspector `Click {"ref":"<text BLUEPRINT>","button":"right"}` → `PressKey {"key":"Escape"}` → 이제 `Ctrl+V`/`Ctrl+Z`/`Home`이 그래프에 간다. 왼쪽 클릭은 워터마크 밑 노드의 체크박스를 눌러 **bool 핀 기본값을 뒤집었다**(CanMove Return true→false). 그래프 탭 `Click`만으로는 포커스가 안 가서 Ctrl+V가 무시됐다.
- **붙여넣은 것만 검증**: 붙여넣은 직후 `PressKey Ctrl+C` → 선택된 붙여넣기 결과(주석 + 균형추)만 복사된다. Ctrl+A 불필요.
- **선택 해제**: Escape는 안 된다. 더미 knot T3D를 붙여넣고 `delete_node` → 선택이 빈다.
- **Home 스크린샷**: `PressKey Home` 뒤 1.5초 기다린 다음 `Screenshot`(맞춤 애니메이션). 최소 줌은 -12 근처라 높이 ~8000 넘는 그래프는 잘린다 → 체인을 여러 열로 배치.
- **주석 속성 바꾸기(텍스트·위치 제외)**: `ObjectTools set_properties {"instance":{"refPath":"<BP>.<BP>:<Graph>.EdGraphNode_Comment_X"},"values":"{\"bCommentBubbleVisible_InDetailsPanel\":false}"}` → true, 축소 시 말풍선이 바로 사라짐(PostEditChange가 bCommentBubbleVisible도 맞춘다). T3D로 붙일 때는 `bCommentBubbleVisible=False`를 직접 써야 한다(InDetailsPanel만 쓰면 말풍선이 남는다). 안쪽(중첩) 박스는 끄고 최상위 박스만 켠다.
- **주석 되돌리기/지우기**: 붙여넣은 직후 포커스 상태에서 `PressKey Ctrl+Z` 한 번 = 붙여넣기 전체 취소(노드 위치·연결 그대로, same-logic 확인). 나중에 하나만 지우기: 읽을 수 있는 줌에서 `Snapshot` → `text "■ ..."`(주석 제목) ref 왼쪽 클릭 → `PressKey Delete`.
- **Snapshot**: `maxDepth` 4~6이면 창 이미지만 나온다. 40으로. My Blueprint `listitem` ref는 스냅샷마다 번호가 바뀐다(찾은 직후 클릭, 더블클릭 `{"doubleClick":true}`로 함수 그래프 탭 열기). 에셋 탭 닫기 = 그 `tab "<에셋>"` 아래 `button` Click(활성 탭일 때만 보임).
- 자동 배치(`graph_layout.py layout`): exec 첫 출력 같은 행, 나머지 새 행(분기는 긴 가지를 같은 행), 새 행은 가로로 안 겹치는 가장 위 자리, 순수 노드는 소비 노드 왼쪽 아래. 노드 크기 추정은 스크린샷 실측(줌 비율로 역산)과 폭은 ±20%, 핀 많은 노드 높이는 +10%.
- **주석 패스: 블록 박스가 조금(16~48px) 겹칠 때**: `--breaks`는 가로 간격만 늘린다. 세로로 겹치면 `graph_layout.py layout` 결과 JSON의 `pos`와 `rects`를 같이 옮긴다(예: y>=1296인 노드 전부 y+128). 그다음 preview → apply. 가로로 겹치면 x>=N 노드 x+96. 스크래치 스크립트로 두 딕셔너리를 같은 값만큼 바꾸면 된다(GA_ActionBase, GA_Player_Dash).
- **주석 패스: `compile_blueprint`의 `blueprint` 인자**는 패키지 경로(`/Game/.../GA_X`)면 `Parameter error: ... is not a valid object path`가 난다. 오브젝트 경로 `/Game/.../GA_X.GA_X`로 준다(`save_assets`는 패키지 경로 그대로).
- **주석 패스: ui-run mismatch 16px**: 붙인 주석 좌표가 spec보다 16 어긋나는 경우가 있다(그리드 스냅 추정, GA_SCBase GetAvatarCharacter y, GA_Player_Guard x). 박스 사이 여백이 16 이상이면 겹침이 없으니 그대로 둔다.
- **주석 패스: 작은 함수 스크린샷**: 그래프가 작으면 Home이 줌 1:1에서 멈춰 박스 윗부분(제목)이 패널 밖으로 잘려 찍힌다. 그래프는 정상이다. 다시 찍어도(`ui-shot`) 같다.
- **주석 패스: CDO 값을 여러 개 읽을 때 없는 프로퍼티 이름 하나가 스크립트 전체를 실패시킨다**: ProgrammaticToolset 안에서 `OT get_properties {"instance":{"refPath":"<BP>.Default__<BP>_C"},"properties":[...]}`에 없는 이름(예: GA_ActionBase 자식에 `Section`, 실제 이름은 `StartSection`)이 있으면 `try/except`로 감싸도 스크립트 결과 전체가 `GetObjectProperties ... could not be read: Section` 에러로 바뀐다. 이름을 모르면 먼저 덤프의 VariableGet 제목(`GetX`)에서 이름을 확인하고, 한 BP당 `properties` 배열 하나로 읽는다(GA_Skill_GroundSlam/WaveSlash, GA_Boss_Slam/Charge, AC_Interactable, BP_WaveProjectile, BP_TelegraphCircle 7개를 한 스크립트로 읽음).
- **주석 패스: 실행 핀 없는 계산 함수(순수 노드만 있는 함수)**: `graph_layout.py layout`은 FunctionEntry를 오른쪽(소비 노드 쪽)에 두고 순수 노드 체인을 왼쪽 아래로 편다(BP_TelegraphCircle UpdateDiscScale). 겹침은 없고 헤더 박스 하나로 충분했다.
- **주석 패스: 세로로 쌓인 두 블록 겹침(GA_Boss_Charge)**: Sequence의 then_0 블록(위)과 then_1 블록(아래 행)이 32px 겹쳤다. `--breaks`는 가로만 벌리므로 layout JSON에서 아래 행 노드(y>=600) 전부 y+96 이동(pos·rects 같이, `nudge.py <layout> y 600 96` 식 스크래치 스크립트) → preview problems [] → apply.
- **주석 패스: Home(전체 맞춤)이 줌 1:1에서 안 움직임(BP_Enemy_Boss EventGraph)**: ui-run·ui-shot 모두 스크린샷이 확대 화면으로 찍혔다(스냅샷 `text "Zoom 1:1"`). 선택이 빈 상태의 Home만 안 됐고, 워터마크 오른쪽 클릭 + Escape 뒤 `SlateInspectorToolset PressKey {"key":"Ctrl+A"}` → `PressKey {"key":"Home"}` → 3초 뒤 `Zoom -5`로 맞춰졌다. 그다음 더미 knot 붙여넣기 + `delete_node`로 선택만 풀고(뷰는 그대로) Home 없이 `Screenshot {"ref":""}`. 스크래치 스크립트에서 `graph_comments.acquire_clipboard_lock()` → `set_clipboard(knot_block("K2Node_Knot_Desel",0,0))` → `ui_paste_and_read(graph_ref, anchor, "K2Node_Knot_Desel", False, 8000)` → `save_shot(out, 8000)`로 했다(잠금 포함). 로직 영향 없음(same-logic same).
- **주석 패스: 분기 false 쪽 Set 노드가 많은 큰 함수(BP_EnemyAIController Think, 65노드)**: 자동 배치가 "중지" Set 노드(bChasing=false) 7개를 아래 빈 행에 흩어 놓아, 블록 박스(사각형)가 서로의 노드를 덮는다. `--breaks`로 블록을 가로로 나눈 뒤 layout JSON의 `pos`와 `rects`를 같은 값으로 직접 고쳤다: 각 Set 노드를 자기 Branch 바로 아래(그 블록 순수 노드 아래 y)로, 루프 Completed 쪽 노드 묶음은 루프 블록 오른쪽 +320 열로. 고친 뒤 rects끼리 겹침을 스크립트로 검사 → preview problems [] → apply.
- **주석 패스: 제목 자동 줄바꿈으로 박스가 노드를 덮음(BP_SCGameInstance EnterDungeon)**: `graph_comments.py`의 글자 폭 추정(영문·숫자 0.58×font)이 실측보다 약 20% 좁아, `"maxw": 0`인 좁은 헤더 박스에서 에디터가 줄을 더 나눠 제목 영역이 노드 위로 내려왔다. 추정을 0.75×font로 고치고(도구 수정), 헤더(`"all": true`) 박스에는 `maxw`를 빼서 긴 줄만큼 넓어지게 했다. 잘못 붙인 주석 지우기: `SlateInspectorToolset Click {"ref":"<tab \"EnterDungeon\">"}` → `Snapshot {"ref":"w116","maxDepth":40}`에서 `text "■ EnterDungeon(LevelName)..."` ref → `Click {"ref":"x3296"}` → `PressKey {"key":"Delete"}` → `BlueprintTools find_nodes`로 노드 2개 그대로 확인(주석은 find_nodes에 안 나온다).
- **주석 패스: `--fit-all`(ui-run, ui-shot)**: 선택이 빈 Home은 **노드만** 맞춰서 헤더 박스 제목이 패널 위로 잘린다(BP_FieldGameMode ChoosePlayerStart, Zoom -2). `graph_comments.py`에 옵션을 추가: 워터마크 오른쪽 클릭 → Escape → `Ctrl+A` → `Home` → 3초 → 더미 knot 붙여넣기·delete_node로 선택만 해제(뷰 유지) → Home 없이 Screenshot. 예: `python Tools/graph_comments.py ui-run spec.json /Game/SoulCombat/Core/BP_SCPlayerController.BP_SCPlayerController:HandleMove --window w116 --layout x.layout.json --shot out.png --fit-all`. A2 2부의 25개 그래프 모두 이 옵션으로 찍어 잘림이 없었다(작은 그래프는 줌 1:1에서 전체가 보임).
- **주석 패스: 이벤트 체인이 많은 EventGraph는 블록별로 다시 쌓기(`Tools/graph_arrange.py`)**: `graph_layout.py layout`의 자동 열 나누기(wrap)는 면적 기준이라 같은 기능의 체인(예: 컨트롤러 EI 이벤트 10개, 게이트 겹침 이벤트)이 여러 열에 섞인다. `python Tools/graph_arrange.py <layout.json> <arrange.json> <out.layout.json>`로 블록마다 체인 root 목록을 열로 쌓고(체인 안 상대 위치 유지, 16 그리드), 블록 간격 480. 한 블록에 박스를 둘 이상 둘 체인 사이는 `vgap`/`cgap` 352. 결과 JSON을 그대로 preview → apply. 예시 `docs/comment-specs/BP_SCPlayerController__EventGraph.arrange.json`, `BP_DungeonGate__EventGraph.arrange.json`.
- **주석 패스: Enhanced Input·Assign 노드가 있는 EventGraph**: `graph_layout.py dump`(find_nodes + get_node_infos)와 T3D 붙여넣기만 쓰면 스트레이 `*_Event_N`이 생기지 않았다(BP_SCPlayerController, BP_DungeonGate same-logic same, 노드 수 48/92 그대로).
- **흐름 테스트 수정 B2: Burst 큐 소켓 비우기(GC_Hit, GC_Guard_Block)**: `OT get_properties {"instance":{"refPath":"/Game/SoulCombat/GAS/Cues/GC_Hit.GC_Hit"},"properties":["defaultPlacementInfo"]}`로 구조체 전체를 읽고, `socketName`만 `"None"`으로 바꾼 **전체 구조체**를 `set_properties {"values":"{\"defaultPlacementInfo\":{\"socketName\":\"None\",\"attachPolicy\":\"DoNotAttach\",\"attachmentRule\":\"KeepWorld\",\"bOverrideRotation\":false,\"bOverrideScale\":true,\"rotationOverride\":{\"pitch\":0,\"yaw\":0,\"roll\":0},\"scaleOverride\":{\"x\":1,\"y\":1,\"z\":1}}}"}` → true. FName 비우기는 문자열 `"None"`이고 읽을 때도 `"None"`. 컴파일·저장 뒤에도 유지, `gameplayCueTag` 그대로.
- **흐름 테스트 수정 B3: BP 컴포넌트 템플릿 Nanite 끄기(BP_TelegraphCircle Disc)**: 메시 에셋(템플릿 SM_Cylinder)을 건드리지 않고 컴포넌트에서만 끈다. `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/Combat/BP_TelegraphCircle.BP_TelegraphCircle_C:Disc_GEN_VARIABLE"},"values":"{\"bDisallowNanite\":true}"}` → true → `compile_blueprint {"warnings_as_errors":true}` → `save_assets` → get_properties `bDisallowNanite true`. 그래프는 바뀌지 않는다.
- **주석 박스가 남아 있는지 확인(MCP 밖)**: 주석 노드는 `find_nodes`(노드 클래스 `/Script/UnrealEd.EdGraphNode_Comment` 지정해도)에 안 나오고, `<그래프 ref>.EdGraphNode_Comment_N` 추측 경로도 `is not valid Object`다. 저장된 .uasset에서 `EdGraphNode_Comment` 이름 개수와 주석 제목의 UTF-16LE 바이트(예: `"■ Tick: 예고원 키우기".encode("utf-16-le")`)를 찾아 확인했다.

### 최종 QA 정적 점검 (8단계 1부)

- **전체 BP 컴파일 한 스크립트**: ProgrammaticToolset에서 `AT find_assets {"folder_path":"/Game/SoulCombat","name":""}` → `AT get_asset_class {"asset_path":a}`가 `_C`로 끝나는 것만 → 부모 먼저 정렬 → `BT compile_blueprint {"blueprint":{"refPath":a+"."+name},"warnings_as_errors":true}`. 72개 모두 `null`(성공), 스크립트 중단 없음. 깨끗하고 최신인 BP는 이 컴파일 뒤에도 `is_dirty` false였고, `GetLogEntries {"pattern":"\[Compiler\]","category":""}`도 0줄이었다(에러·경고가 없으면 [Compiler] 줄이 안 남는다).
- **의존성 스캔**: 같은 목록에 `AT get_dependencies {"asset_path":a}` → `/Script/`와 `/Game/SoulCombat`를 빼고 경로별로 참조 에셋 이름을 모으면 템플릿 의존 표가 한 번에 나온다. `/Game/_Scratch` 접두사를 따로 모아 0건인지 본다.
- **배치 액터의 BP 컴포넌트 값 읽기**: 레벨 액터 ref 뒤에 `.컴포넌트이름`을 붙인다. `OT get_properties {"instance":{"refPath":"/Game/SoulCombat/Maps/L_CombatField.L_CombatField:PersistentLevel.BP_Enemy_Grunt_C_0.Combat"},"properties":["bRespawnOnDeath","bDestroyOnDeath"]}` → 값이 나온다. 이름은 `ActorTools get_components {"actor":<액터 ref>}`로 확인.
- **방 참조 stale 검사**: `SceneTools find_actors {"name":"","tag":"","collision_channels":[],"actor_type":{"refPath":"/Script/Engine.Actor"}}`의 refPath 집합을 만들고, 방마다 `OT get_properties {"properties":["EntryDoor","ExitDoor","Enemies"]}`로 읽은 refPath가 그 집합에 있는지 본다. 빈 참조는 `None`으로 읽힌다(Start 방 EntryDoor, Boss 방 ExitDoor는 설계상 None). 부모 클래스(`BP_DungeonRoom_C`, `BP_EnemyBase_C`)를 actor_type으로 주면 자식 BP 액터도 모두 나온다.
- `ObjectTools list_properties`를 레벨 액터에 쓰면 로그에 `LogJson: Warning: Property "OnEndPlay" ... unhandled during Json schema generation` 경고가 델리게이트마다 찍힌다. 콘텐츠 문제가 아니다.
- **반투명 MI + Nanite 메시 경고(BP_DungeonGate 포털)**: 시작 로그 `Invalid material [MI_SC_Portal] used on Nanite static mesh [SM_Plane]` → B3과 같이 컴포넌트에서만 끈다. `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/Dungeon/BP_DungeonGate.BP_DungeonGate_C:PortalPlane_GEN_VARIABLE"},"values":"{\"bDisallowNanite\":true}"}` → true → `compile_blueprint` → `save_assets ["/Game/SoulCombat/Dungeon/BP_DungeonGate"]`. 배치된 인스턴스(`...BP_DungeonGate_C_0.PortalPlane`)도 true로 읽혔고, 맵을 다시 로드했을 때 경고가 없었다.

### 키 입력 없는 PIE 전투 테스트 (8단계 최종 QA 2부)

- **테스트 맵**: `AT duplicate {"path":"/Game/SoulCombat/Maps/L_CombatField","new_path":"/Game/_Scratch/L_CombatTest"}` → `save_assets` → (현재 레벨 `is_dirty` false 확인) `load_level`. 방해되는 액터는 복제 맵에서만 바꾼다(예: 잡몹 `OT set_properties {"bStartDormant":true}`).
- **드라이버 액터(BP)**: 폰의 컴포넌트를 찾아 실제 입력 경로를 부른다. `(bind c (Actor|GetComponentbyClass :self p :ComponentClass "/Game/SoulCombat/Components/AC_CombatComponent.AC_CombatComponent_C"))` → `(bind ok (Class|ACCombatComponent|PressInput :self c :InputTag Tag))`(출력 `bActivated`), `(Class|ACCombatComponent|ReleaseInput :self c :InputTag Tag)`. 단계 사이는 `(Utilities|FlowControl|Delay 0.35)`을 문장처럼 이어 쓰면 된다(뒤 문장이 Completed에 붙음). 단계마다 커스텀 이벤트(`add_event`)로 나누고 끝에서 `(CallFunction|StepB)`로 넘긴다.
- **측정 기록**: 배열 변수(`add_variable ... "container_type":"ARRAY"`)에 `(Utilities|Array|Add (Variables|Default|GetTimes) (Utilities|Time|GetGameTimeinSeconds))`로 쌓고, PIE가 끝난 뒤 `OT get_properties {"instance":{"refPath":"/Game/_Scratch/UEDPIE_0_L_CombatTest.L_CombatTest:PersistentLevel.BP_TestPlayerDriver_C_0"},"properties":["Labels","Times",...]}`로 읽는다(PIE 멈추기 전에). 태그 문자열: `(GameplayTags|GetDebugStringfromGameplayTagContainer (GameplayTags|GetOwnedGameplayTags asc))`(ASC를 인터페이스 핀에 바로 연결). 속성: `(bind (found v) (Ability|Attribute|GetFloatAttributefromAbilitySystemComponent :AbilitySystem asc :Attribute "<속성 리터럴>"))`. `Actor|GetAllActorsOfClass`는 impure라 먼저 bind한다.
- **이벤트 리스너(Actor BP에서도 동작)**: `(Ability|Tasks|WaitforAttributeChanged :TargetActor a :Attribute H :OnlyTriggerOnce false (:then) (:Changed (CallFunction|Rec :Label (Utilities|String|Append :A "EV HP old=" :B (Utilities|String|ToString(Float) _oldvalue)))))`, `(Ability|Tasks|WaitGameplayTagAddtoActor :TargetActor a :Tag "(TagName=\"State.HitStun\")" :OnlyTriggerOnce false (:then) (:Added ...))`. 비동기 노드는 커스텀 이벤트 하나에 하나씩 두고(중첩하면 `_oldvalue` 범위가 헷갈린다) 시작 이벤트에서 차례로 `CallFunction`한다. 폴링 간격과 상관없이 피해와 경직 시점이 정확히 남는다.
- 주기 샘플: `(Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "SampleJ" :Time 0.25 :bLooping true)` → 끝나면 `(Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "SampleJ")`.
- **함정: 변수 이름 `Tags`**: Actor BP에 `add_variable {"name":"Tags"}` → Actor.Tags와 겹쳐 `Tags_0`으로 만들어진다. `list_variables`로 확인하고 다른 이름(TagLog)을 쓴다.
- **함정: PIE 3fps**: 에디터가 백그라운드면 로그에 `Bringing World ... up for play (max tick rate 3)`가 찍히고 Delay/WaitDelay가 0.333초 프레임 경계에서 끝난다. 수치·태그 검증은 되지만 입력 간격 같은 타이밍 검증은 거칠다. Bash 포그라운드 `sleep`은 막혀 있어, 기다릴 때는 `run_in_background` sleep이나 `get_properties`(Phase/Done 변수) 폴링을 쓴다.
- **함정: 컨트롤러 없는 Character는 LaunchCharacter가 무시된다**: 훈련 더미(AutoPossessAI Disabled)는 PIE에서 CharMoveComp `MovementMode`가 `MOVE_None`이었다(`OT get_properties {"instance":{"refPath":"<PIE 액터>.CharMoveComp"},"properties":["MovementMode","bRunPhysicsWithNoController"]}`). 수정: `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/Characters/Enemies/BP_TrainingDummy.Default__BP_TrainingDummy_C:CharMoveComp"},"values":"{\"bRunPhysicsWithNoController\":true}"}` → 컴파일 → 저장. 그 뒤 PIE에서 `MOVE_Walking`이 되고 넉백과 띄우기가 동작했다.
- **함정: 템플릿 값을 바꿀 때 이미 열려 있는 레벨의 인스턴스**: 위 수정 뒤 열려 있던 L_CombatTest의 더미 인스턴스는 계속 false로 읽혔다(레벨도 dirty가 됨). 그 상태로 레벨을 저장하면 false가 인스턴스 오버라이드로 남을 수 있다. 인스턴스에도 같은 값을 직접 쓰고 저장하거나, 저장하지 않고 다시 로드한다. 닫혀 있던 L_CombatField는 다시 로드하자 3개 모두 true였다(오버라이드 없음).
- 반투명 MI + Nanite 경고가 PIE 중에 스폰되는 액터에서만 나는 경우(BP_WaveProjectile Visual): 1부와 같이 `...BP_WaveProjectile_C:Visual_GEN_VARIABLE`에 `{"bDisallowNanite":true}`.

### PIE 스크린샷을 파일로, 흐름 회귀 테스트 (8단계 최종 QA 3부)

- **PIE 뷰포트 스크린샷(컨텍스트에 base64를 넣지 않음)**: 레벨 뷰포트는 SlateInspector 스냅샷에서 `splitter [pos=31,102 size=2016,928] [ref=sp4]`였다. 찾는 법: ProgrammaticToolset에서 `Snapshot {"ref":"","maxDepth":60}` → `progressbar`/HUD 텍스트가 들어 있는 splitter를 고른다(이 에디터 레이아웃에서 `sp4`). 촬영과 저장은 한 스크립트 안에서 한다:
  `r = execute_tool("SlateInspectorToolset.SlateInspectorToolset.Screenshot", json.dumps({"ref":"sp4"}))["returnValue"]` → `execute_tool("editor_toolset.toolsets.asset.AssetTools.write_file", json.dumps({"file_path":"<프로젝트>/SoulCombat/Saved/QA/x.b64.txt","content":r["data"]}))` → 반환은 `len(r["data"])`만. 로컬에서 `python -c "import base64; open('x.png','wb').write(base64.b64decode(open('x.b64.txt','rb').read().strip()))"`. 결과는 PIE 게임 화면 + UMG HUD(2016×928, 위에 뷰포트 툴바 한 줄)다. `CaptureViewport`는 에디터 월드를 찍는다.
- **함정: `write_file` 확장자**: 절대 경로(프로젝트 `Saved/` 아래)는 되지만 확장자는 `.csv .html .json .md .py .txt`만 된다. `.b64`는 `Unsupported file extension` 에러이므로 `.b64.txt`로 쓴다. 폴더는 자동으로 만들어진다.
- **순간을 잡으려면 폴링과 촬영을 한 스크립트에**: MCP 호출 사이의 모델 대기 시간이 수십 초라, 폴링 결과를 본 뒤 다음 호출로 찍으면 장면이 이미 지나간다(스킬 쿨타임이 끝나 있었음). 스크립트 안의 `time.sleep()`은 PIE를 멈추지 않는다(게임은 계속 진행). 예: `while ...: r = get_properties(driver, ["Phase","Labels"]); if [l for l in r["Labels"] if l.startswith("e R press")]: break; time.sleep(0.2)` → 바로 Screenshot. 이렇게 E·R 쿨타임 숫자(3.7, 5.3)가 보이는 HUD를 찍었다.
- **함정: 스크립트 안의 무효 PIE 경로는 try로 못 막는다**: 클리어 창 카운트다운을 읽는 루프가 레벨 이동(위젯 파괴) 뒤 `get_properties`를 부르자 try/except가 있어도 스크립트 전체가 실패하고 앞의 결과도 사라졌다. 루프 탈출 조건을 먼저 둔다(예: 텍스트가 '1초'로 시작하면 break). 죽어서 Destroy된 적(`bDestroyOnDeath`)도 같은 에러이므로, 적은 `find_actors`(부모 클래스 BP_EnemyBase_C)로 살아 있는 것만 읽는다.
- **PIE 위젯 경로**: HUD는 `PC.HUD` → `/Engine/Transient.UnrealEdEngine_0:BP_SCGameInstance_C_N.WBP_PlayerHUD_C_0`이다. 자식 위젯은 `<HUD>.WidgetTree_0.RoomBanner`, 그 안의 TextBlock은 `<HUD>.WidgetTree_0.RoomBanner.WidgetTree_0.TitleText`이고 `get_properties ["Text"]`로 읽는다(한글 그대로). 표시 여부는 위젯의 `["Visibility"]`(`Collapsed`/`HitTestInvisible`). GameInstance 번호 N은 PIE마다 늘어나므로 `PC.HUD`에서 다시 얻는다.
- **B4 수정 뒤 UMG 버튼 클릭**: 입장 창(`bIsFocusable` true)에서는 SlateInspector `Snapshot {"ref":"sp4","maxDepth":60}`의 `button "입장"` ref를 `Click` 한 번만 해도 OnClicked가 불렸다. 흐름 테스트 때처럼 `PressKey Enter`를 이어서 보낼 필요가 없다(보내면 이미 레벨 이동 중).
- **레벨 액터의 BP 변수가 인스턴스 편집이 아니면** `set_properties`가 `could not be set: Interval`로 실패한다(BP_TestKiller). 테스트 동안 끄려면 `SceneTools remove_from_scene` → 테스트 → `add_to_scene_from_class`로 다시 넣고 맵을 저장한다.
- 보스 스크린샷은 보스가 붙어 있으면 카메라가 보스 몸에 파묻힌다. 촬영 직전에 `set_actor_transform`으로 보스를 (9000,0), 플레이어를 (8300,0) Yaw 0으로 떨어뜨리고 0.4초 간격으로 여러 장 찍어 고른다.

### 기존 그래프 국소 수정과 주석 하나 교체 (콤보 입력 큐 수정)

- **DSL 없이 노드 끼워 넣기**: `BT create_node {"graph":G,"type_id":"Variables|Combo|State|SetQueuedInputs","pos":{"x":960,"y":176}}` → `get_node_infos`로 핀 index 확인 → `break_pins`(옛 exec 연결) → `connect_pins` 두 번. 체인 전체를 다시 쓰지 않으니 나머지 노드·위치·주석이 그대로다(덤프 비교로 확인).
- **정수 연산 노드(Promotable)**: `find_node_types "Math|Integer|"`에는 `int+int`류가 안 나온다. `create_node "Utilities|Operators|Add"`(또는 `Greater(>)`, `Subtract`)로 와일드카드 노드를 만들고 A 핀에 int 출력을 `connect_pins`하면 `Math|Integer|int+int`/`integer>integer`/`int-int`로 바뀐다. 그다음 `set_pin_value {"pin":<B>,"value":"1"}`(타입이 정해진 뒤에 설정). Min은 `Math|Integer|Min(Integer)`(`K2Node_CommutativeAssociativeBinaryOperator`, 입력 A=0, B=1).
- **함정: 커스텀 이벤트의 출력 index 0은 `OutputDelegate`**, exec `then`은 index 1이다. `connect_pins {"output_pin":{"node":<K2Node_CustomEvent>,"direction":"EGPD_Output","index_id":0},...}`는 `Could not connect pin OutputDelegate to execute` 에러(스크립트 중단, 앞의 delete_node는 이미 실행됨).
- **변수 삭제**: Get/Set 노드를 모두 `delete_node`한 뒤 `BT remove_variable {"blueprint":BP,"name":"bInputBuffered"}` → null, 컴파일 경고 없음.
- **주석 박스 좌표 읽기**: 그래프 포커스(워터마크 오른쪽 클릭 + Escape) → `PressKey Ctrl+A` → `PressKey Ctrl+C` → `graph_comments.get_clipboard()` + `parse_t3d()` → `EdGraphNode_Comment`의 NodePosX/Y/Width/Height/NodeComment. 끝나면 더미 knot 붙여넣기 + `delete_node`로 선택 해제.
- **주석 하나만 지우기(줌 -11에서는 제목이 겹쳐 클릭 불가)**: knot T3D를 붙여넣고(`K2Node_Knot_Focus`) `set_node_position`으로 지울 박스 안(제목 근처)에 옮긴 뒤 `PressKey Home`(선택된 knot에 맞춰 줌 1:1) → 2초 → `delete_node` knot → `Snapshot {"ref":"<BP 창>","maxDepth":40}`에서 주석 제목 `text` ref → `Click`(왼쪽) → **`PressKey Ctrl+C` + 클립보드 파싱으로 그 주석 하나만 선택됐는지 확인** → `PressKey Delete`. 스냅샷 텍스트는 콘솔 인코딩 때문에 한글이 깨져 보여도, ASCII 부분(예: `bInputBuffered`)으로 찾으면 된다.
- **같은 자리에 새 주석**: spec에 좌표를 직접 준다 `[{"text":"■ ...","x":1840,"y":2560,"w":1344,"h":992,"color":"logic","bubble":false}]`(안쪽 박스는 bubble false) → `graph_comments.py preview` → `ui-run <spec> <그래프 ref> --window <창> --shot <png> --fit-all`(layout 없이도 된다). 제목 줄 수는 `title_height(text,18,w)`로 미리 재서 박스 위쪽 여백(노드까지 거리)보다 작게 줄바꿈한다.
- **작은 영역 확인 스크린샷**: 위의 knot → Home → delete_node 뒤 `save_shot`(`SlateInspectorToolset Screenshot {"ref":""}`)으로 줌 1:1 화면을 찍으면 새 노드 겹침을 눈으로 볼 수 있다(추정 크기보다 실제 Promotable 노드가 훨씬 작다).
# UE5.8.3 네이티브 주석 API 추가 확인

2026-09-30 현재 엔진 `Source/Editor/BlueprintEditorLibrary/Private/BlueprintEditorLibrary/BlueprintGraphEditor.h`에는 `AddCommentNode`, `AddCommentToNodes`, `ListCommentNodes`, `RemoveCommentNode`가 UFUNCTION으로 있다. MCP 전용 주석 툴의 부재는 엔진 API 부재가 아니다. 제작 브리지에서 다음 메서드를 실사용해 새 그래프8개의 주석을 만들고 전후 same-logic을 확인했다. 아래 방식은 PIE를 종료한 편집 단계에서만 사용한다.

```python
import unreal
blueprint = unreal.load_asset('/Game/SoulCombat/Core/BP_SCPlayerController')
editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(blueprint, 'ResumeGame')
nodes = list(editor.list_all_nodes())
editor.add_comment_to_nodes('월드를 재개하고 메뉴 참조·커서·게임 입력을 복원', nodes, 70)
```

명시 컴파일·저장과 전후 논리 비교는 계속 필요하다. UI 클립보드 주석 도구는 사용할 수 있는 대체 방식이며, 기존 기록은 해당 작성 당시의 도구 경로로 읽는다. PIE 런타임 객체의 테스트 설정 변경에는 `set_editor_property(..., notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)`를 사용해 에디터 변경 알림에 의한 재생성과 게임 수명 처리를 구분한다.

### 네이티브 주석 노드의 NodeGuid와 쿠킹

UE 5.8.3의 `BlueprintGraphEditor.cpp` 1292~1316행에서 `AddCommentNode`는 `CreateNewGuid()`를 호출하지 않는다. `AddCommentToNodes`도 이 함수를 사용한다. 편집 세션에서 엄격 컴파일와 저장이 통과해도 새 쿠킹 프로세스의 `EdGraphNode::PostLoad`가 GUID 누락 경고를 낼 수 있다. 이번 첫 제작본 쿠킹에서는 주석25개·BP9개에 해당 경고가 발생했다.

`EdGraphNode.cpp` 698~703행은 패키지를 로드할 때 빠진 GUID를 자동 생성한다. 이를 디스크에 남기려면 새 편집 세션에서 대상 패키지를 다시 읽고 `unreal.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False)`로 강제 저장한다. 자동 생성이 dirty로 표시되지 않을 수 있어 기본 dirty-only 저장만으로 복구를 단정하지 않는다. `NodeGuid`는 편집 노출 플래그가 없는 보호 속성이라 Python·MCP setter가 접근 검사에 차단된다. 엔진 코드나 게임 실행 로직을 변경할 필요는 없다.

이번 보정은 재로드한9개 BP를 강제 저장했고, 모든64개 그래프의925개 실행 노드에서 타입·위치·전체 핀/값/연결의 전후 동일성을 확인했다. 이후77개 전체 엄격 컴파일와 dirty0을 확인했다. 최종 쿠킹의 경고 수는 `11-production-validation.md`에 별도로 기록한다. 새 주석을 추가한 후에는 편집기 컴파일뿐 아니라 새 프로세스의 쿠킹 로그도 확인한다.

## DSL `bind`와 순수 Getter의 평가 시점 함정

2026-09-30 통합 담당이 실제 PIE에서 확인한 사례다. DSL의 `bind`는 출력 핀 연결에 이름을 붙이며, 그 줄에서 값을 복사해 보관하는 스냅샷을 보장하지 않는다. 특히 순수(pure) Getter를 `bind`한 뒤 그 Getter가 읽는 변수를 바꾸면, 이후 실행 노드가 입력을 평가할 때 변경된 값을 읽을 수 있다. 텍스트에서 먼저 `bind`했다는 사실만으로 Blueprint의 읽기·쓰기 순서가 고정되지는 않는다.

`HitAlongPath`에서는 이전 위치의 순수 Getter를 Trace의 Start에 연결한 상태로 `SetPreviousTraceLocation(current)`를 먼저 실행했다. 이후 SphereTrace가 Start 입력을 평가하자 이전 위치가 이미 현재 위치로 바뀌어 `Start == End`가 됐다. 적 명중 12조건 중 Side2 두 조건이 실패했고, 새 PIE에서 `off620`과 `off1125`의 실제 피해는 각각 0이었다. 진단용 이전 위치→현재 위치 Trace는 `PlayerHit`였지만 같은 끝점으로 축소된 `CollapsedTrace`는 miss였다. 직접 `BeginChargePath → 액터를 구간 끝 위치로 이동 → HitAlongPath`를 호출한 핵심 6조건에서도 첫 구간·둘째 구간·역방향 구간 3조건은 실패했고 endpoint·outside 3조건은 통과했다. 따라서 끝점만 검사하는 성공 사례로 이동 구간의 판정까지 통과했다고 판단하면 안 된다.

읽은 값을 유지해야 하면 실제 실행 핀이 있는 함수 로컬 Set으로 `이전 위치 읽기 → 로컬 값 저장 → 공유 변수 변경 → 저장한 로컬 값 소비` 순서를 명시한다. 스냅샷이 필요 없는 경우에는 `Trace 실행 → 이전 위치를 현재 위치로 갱신` 순서로 연결해 소비 전에 값을 덮어쓰지 않는다. 이번에는 `Trace → SetPreviousTraceLocation → ForEach` 순서로 실행 핀 3개만 보정했다. 같은 핵심 검사 6조건이 모두 통과했고, 히트스톱이 활성화된 자연 적 공격 12조건과 최종 통합 회귀 178조건도 통과했다. 데이터 핀·기본값·피해 규칙은 유지했다. 실제 피해 측정의 `BeforeHitHealth`는 함수 로컬 변수에 실행 핀 Set으로 피해 전 Health를 저장하므로 이번 순수 Getter 재평가 문제와 구분한다.

나중에 학습용으로 재현할 때는 Getter를 `bind`한 뒤 원본 변수를 바꾸는 순서를 앞뒤로 바꾸고 Trace의 Start·End를 비교하면 되며, 이 재현 학습은 현재 게임 제작의 선행 조건이 아니다.

