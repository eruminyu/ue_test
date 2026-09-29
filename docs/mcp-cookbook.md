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
