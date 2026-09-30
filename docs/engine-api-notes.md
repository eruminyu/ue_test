# 엔진 API 검증 노트 (UE 5.8)

SoulCombat 설계(`docs/01-game-spec.md`)에 쓰이는 엔진 API와 템플릿 에셋을 UE 5.8 설치 소스와 `.uasset` 디코딩으로 확인했다. 판정 기준은 다음과 같다.

- TRUE: 주장대로 동작한다.
- PARTIAL: 일부만 맞고, BP 대안이 있다.
- FALSE: 주장이 틀렸다.

항목마다 주장, 판정, 근거(파일:줄), Blueprint 구현 시사점을 적었다.

경로 약어

- `GA/` = `Engine/Plugins/Runtime/GameplayAbilities/Source/GameplayAbilities/`
- `Eng/` = `Engine/Source/Runtime/Engine/`
- `UMG/` = `Engine/Source/Runtime/UMG/`
- `Runtime/` = `Engine/Source/Runtime/`(GameplayTags, GameplayTasks, AIModule, SlateCore)
- `Content/` = `SoulCombat/Content/`(템플릿 에셋)
- 엔진 설치 위치: `C:/Program Files/Epic Games/UE_5.8/`

---

## 1. ASC / 어빌리티

### A1. Give Ability: TRUE
- **주장**: `UAbilitySystemComponent::K2_GiveAbility(TSubclassOf<UGameplayAbility>, Level, InputID)`는 BlueprintCallable이고 `FGameplayAbilitySpecHandle`을 반환한다.
- **근거**
  - `GA/Public/AbilitySystemComponent.h:968-969`: `BlueprintCallable, BlueprintAuthorityOnly`, DisplayName "Give Ability", `Level = 0`, `InputID = -1`.
  - 구현은 `GA/Private/AbilitySystemComponent_Abilities.cpp:387-402`이며, BuildAbilitySpecFromClass를 거쳐 GiveAbility(Spec)을 부른다.
  - 권한이 없으면 빈 핸들을 반환한다(`:301-306`).
  - InstancedPerActor는 부여 시점에 인스턴스를 만든다(`:319-323`).
  - "Give Ability And Activate Once"도 있다(`AbilitySystemComponent.h:980`).
- **BP**
  - 노드는 'Give Ability'(Target=ASC)다. 반환된 핸들을 변수에 저장해 TryActivateAbility에 넘긴다.
  - Level 기본값이 0이므로 ScalableFloat 커브를 쓸 계획이면 1로 명시한다.
  - 싱글 플레이에서는 항상 권한이 있다.

### A2. TryActivateAbility의 실패 조건: TRUE
- **주장**: `TryActivateAbility(Handle, bAllowRemoteActivation)`는 BlueprintCallable이다. 쿨다운 중이거나, 비용을 낼 수 없거나, ActivationBlockedTags에 걸리면 false를 반환한다.
- **근거**
  - `GA/Public/AbilitySystemComponent.h:1039-1040`. 주석(`:1035-1037`)에 "false positive가 있을 수 있다"고 적혀 있다.
  - 호출 경로: `GA/Private/AbilitySystemComponent_Abilities.cpp:1682` InternalTryActivateAbility → `:1817` CanActivateAbility.
  - `GA/Private/Abilities/GameplayAbility.cpp:457-560`의 검사 순서:
    1. `:486` 활성화 억제
    2. `:508` CheckCooldown
    3. `:518` CheckCost
    4. `:528` 태그 조건(`:407` Blocked, `:408` ActivationBlockedTags, `:419` ActivationRequiredTags)
    5. `:539` 입력 차단
    6. `:549` BP의 K2_CanActivateAbility
  - CheckCooldown(`:1064-1104`)은 쿨다운 GE의 GetGrantedTags 중 하나라도 ASC에 있으면 실패한다. 태그를 주지 않는 쿨다운 GE는 경고만 남긴다.
  - CheckCost(`:1115-1136`)는 `GA/Private/GameplayEffect.cpp:5497-5528` CanApplyAttributeModifiers를 쓴다.
    - Additive 모디파이어만 보고 `CurrentValue + CostValue < 0`이면 실패한다.
    - 새 Spec을 만들어 검사하므로 SetByCaller 값이 없다.
- **BP**
  - 쿨다운 GE는 Has Duration으로 만들고 'Grant Tags to Target Actor'로 Cooldown 태그를 준다.
  - 비용 GE는 Instant, AddBase에 음수 ScalableFloat를 쓴다. SetByCaller, Override, Multiply 비용은 사전 검사에 반영되지 않는다.
  - TryActivate가 true를 돌려줘도 그래프의 CommitAbility가 실패할 수 있다. CommitAbility가 false면 End Ability로 끝낸다.
  - 비용 검사는 AttributeSet이 있어야 한다. InitStats를 먼저 부른다.

### A3. 이미 실행 중인 InstancedPerActor GA 재활성화: TRUE
- **주장**: 실행 중인 InstancedPerActor GA에 TryActivateAbility를 하면 실패한다. bRetriggerInstancedAbility가 true면 실행 중인 인스턴스를 끝내고 다시 시작한다.
- **근거**
  - `GA/Private/AbilitySystemComponent_Abilities.cpp:1831-1852`: `Spec->IsActive()`일 때 `bRetriggerInstancedAbility`면 `EndAbility(..., bWasCancelled=false)` 후 재시작하고, 아니면 `return false`.
  - 이 검사는 CanActivateAbility(`:1817`) 뒤에 있다.
  - `GA/Public/Abilities/GameplayAbility.h:701-703`: `bRetriggerInstancedAbility`는 생성자에서 설정하지 않으므로 false다.
  - InstancedPerExecution에는 이런 검사가 없다.
- **BP**
  - 재트리거는 Cancel이 아니라 End이므로 OnEndAbility의 bWasCancelled가 false다.
  - 기본 InstancingPolicy인 InstancedPerExecution은 연타할 때마다 인스턴스가 겹쳐 실행된다. 공격, 대시, 스킬 GA는 'Instanced Per Actor'로 바꾼다.
  - 콤보 연계는 재트리거보다 실행 중인 GA 안에서 WaitGameplayEvent로 받는 편이 안전하다.

### A4. InitStats와 DataTable 행 이름: TRUE
- **주장**: InitStats(AttributeSet 클래스, DataTable)는 BP에서 호출할 수 있다. 행 이름은 `<접두사 뺀 클래스 이름>.<속성>`이고, Base와 Current 값을 모두 설정한다.
- **근거**
  - `GA/Public/AbilitySystemComponent.h:179-183`: BP에 노출된 것은 `K2_InitStats(TSubclassOf<UAttributeSet>, const UDataTable*)`(DisplayName "InitStats")이고 반환값이 없다.
  - `GA/Private/AbilitySystemComponent.cpp:86-105` InitStats는 GetOrCreateAttributeSubobject를 부른다(`:107-120`). 세트가 없으면 NewObject로 만들고 AddSpawnedAttribute를 한다.
  - `GA/Private/AttributeSet.cpp:436-474`
    - 행 이름은 `"%s.%s"`(Owner 클래스 이름, 속성 이름) 형식이다.
    - 행은 `FindRow<FAttributeMetaData>`로 찾는다.
    - 값은 `SetBaseValue(BaseValue); SetCurrentValue(BaseValue);`로 쓴다.
  - `GA/Public/AttributeSet.h:271-286`: FAttributeMetaData는 {BaseValue, MinValue, MaxValue}다.
  - 대안은 ASC의 DefaultStartingData(`AbilitySystemComponent.h:208-209`, OnRegister `AbilitySystemComponent.cpp:205-213`)다.
- **BP**
  - 행 구조체는 AttributeMetaData이고, 행 이름은 `SCAttributeSet.Health`, `SCAttributeSet.MaxHealth` 형식이다(U 접두사 없음).
  - BaseValue 열만 쓰이고 Min/Max 열은 무시된다.
  - PreAttributeChange 클램프를 거치지 않으므로 Max 행과 현재값 행을 모두 넣는다.
  - AttributeSet 생성까지 해 주므로 C++ 없이 세트를 붙이는 방법이 된다. Give Ability나 GE 적용보다 먼저 호출한다.

### A5. 인터페이스 없는 액터에서 ASC 찾기: TRUE
- **주장**: Get Ability System Component(Actor)는 IAbilitySystemInterface가 없으면 FindComponentByClass로 대신 찾는다.
- **근거**
  - `GA/Public/AbilitySystemBlueprintLibrary.h:73-75`(BlueprintPure, DefaultToSelf), `.cpp:77-80`.
  - `GA/Public/AbilitySystemGlobals.h:87`: `LookForComponent = true`.
  - `GA/Private/AbilitySystemGlobals.cpp:239-249`: 주석 "BP-only actors"와 함께 `FindComponentByClass`로 넘어간다.
  - GE 타깃 데이터(`GA/Private/GameplayAbilityTargetTypes.cpp:46`), WaitGameplayEvent와 WaitAttributeChange의 외부 타깃, EffectContext(`GameplayEffectTypes.cpp:210`)도 같은 경로를 쓴다.
  - ASC는 `bWantsInitializeComponent = true`(`AbilitySystemComponent.cpp:56`)이고, InitializeComponent에서 `InitAbilityActorInfo(Owner, Owner)`를 자동으로 부른다(`AbilitySystemComponent_Abilities.cpp:78-84`).
  - PlayerController는 이 시점에 한 번만 잡는다(`GameplayAbilityTypes.cpp:36-48`).
  - InitAbilityActorInfo와 RefreshAbilityActorInfo는 BP에 노출되지 않는다(`AbilitySystemComponent.h:1523, 1546`).
- **BP**
  - 인터페이스 없이 BP로 붙인 ASC로 충분하고, ActorInfo 초기화 노드도 필요 없다.
  - ActorInfo.PlayerController는 null로 남으므로 이 값에 의존하지 않는다.
  - 캐릭터당 ASC는 하나만 둔다. 첫 번째 것만 찾는다.

### A6. SendGameplayEventToActor, AbilityTriggers, WaitGameplayEvent: TRUE
- **주장**: 인터페이스 없는 액터에도 이벤트가 전달되고, GameplayEvent 트리거와 WaitGameplayEvent가 반응한다. OnlyMatchExact 기본값과 부모/자식 태그 매칭 규칙을 확인한다.
- **근거**
  - `GA/Private/AbilitySystemBlueprintLibrary.cpp:82-105`는 폴백 검색으로 ASC를 찾아 `HandleGameplayEvent`를 부른다. ASC가 없으면 Error 로그만 남긴다.
  - `GA/Private/AbilitySystemComponent_Abilities.cpp:2564-2605` HandleGameplayEvent
    - 트리거는 이벤트 태그부터 `RequestDirectParent()`로 올라가며 찾으므로 계층 매칭이다.
    - `GenericGameplayEventCallbacks`는 정확 일치로 찾는다.
    - 컨테이너 델리게이트는 `MatchesAny`로 찾는다.
  - 트리거 등록은 `:592-611`(TriggerSource=GameplayEvent만)에 있다.
  - 발동 경로는 `:2496-2528`이다. HasNetworkAuthorityToActivateTriggeredAbility(`:2699-2715`)를 거쳐 InternalTryActivateAbility를 부르므로 쿨다운, 비용, 태그, InstancedPerActor 중복 검사가 모두 적용된다.
  - ActivateAbilityFromEvent를 구현했으면 그것이 우선 불린다(`GameplayAbility.cpp:904-915`).
  - 기본 TriggerSource는 GameplayEvent다(`GameplayAbilityTriggerType.h:31-33`).
  - `GA/Public/Abilities/Tasks/AbilityTask_WaitGameplayEvent.h:31`: `OnlyTriggerOnce=false`, `OnlyMatchExact=true`. `.cpp:33-40, 55-60`.
- **BP**
  - 트리거는 항상 계층 매칭이다. 트리거가 Event.Hit이면 Event.Hit.Heavy에도 발동하고, 반대는 안 된다.
  - WaitGameplayEvent는 기본적으로 정확 일치다. false로 두면 부모 태그로 듣고 자식 이벤트를 받는다.
  - 이벤트 발동도 차단 태그와 중복 검사를 따른다. 그래서 사망 GA에 State.Dead를 차단 태그로 넣지 않는다.
  - 이벤트 처리와 활성화는 동기로 일어난다.

### A7. Loose 태그와 HasMatchingGameplayTag: TRUE
- **주장**: AddLooseGameplayTags, RemoveLooseGameplayTags, HasMatchingGameplayTag는 BP에서 호출할 수 있고, 인터페이스 없는 액터에도 동작한다.
- **근거**
  - `GA/Public/AbilitySystemBlueprintLibrary.h:484-498`: `AddLooseGameplayTags(Actor, Tags, bShouldReplicate)`, Remove 쌍, `.cpp:1348-1370`. ASC가 없으면 false를 반환한다.
  - ASC 자체의 AddLooseGameplayTag(s)는 UFUNCTION이 아니고 카운트 방식이다(`AbilitySystemComponent.h:656-679`).
  - `Runtime/GameplayTags/Classes/GameplayTagAssetInterface.h:13`: `CannotImplementInterfaceInBlueprint`. `:37-58` HasMatchingGameplayTag, HasAll/HasAny(부모 확장).
  - ASC가 이 인터페이스를 구현한다(`AbilitySystemComponent.h:109, 581-593`).
  - GetGameplayTagCount는 BlueprintPure다(`:688-689`).
- **BP**
  - 태그 추가와 제거는 라이브러리 노드에 Actor를 넣어 호출한다.
  - 카운트 방식이라 두 번 추가하면 두 번 제거해야 한다. State.Dead 같은 상태 태그는 추가하기 전에 확인한다.
  - Has Matching Gameplay Tag의 Target은 반드시 ASC다. 캐릭터 액터는 타깃이 될 수 없다.
  - 부모 태그로 물어도 매칭된다.

### A8. 어빌리티 전부 취소: PARTIAL
- **주장**: CancelAbilities(WithTags, WithoutTags, Ignore) 같은 BP 노드로 모든 어빌리티를 취소할 수 있다(사망용).
- **근거**
  - `GA/Public/AbilitySystemComponent.h:1051-1061`의 CancelAbility, CancelAbilityHandle, CancelAbilities, CancelAllAbilities는 모두 UFUNCTION이 아니다. BP에 노출된 cancel 계열은 InputCancel/TargetCancel(`:1394, 1415`)뿐이다.
  - 대안 1: `GA/Public/GameplayEffectComponents/CancelAbilityTagsGameplayEffectComponent.h:24` "Cancel Abilities with Tags"(ComponentMode 기본값 OnApplication, `:71`).
    - `.cpp:76-93`: 빈 컨테이너는 nullptr로 넘겨 전부 취소한다(`AbilitySystemComponent_Abilities.cpp:1339-1343`).
    - Instant GE에서도 OnApplied가 불린다(`AbilitySystemComponent.cpp:1165`).
  - 대안 2: GA의 CancelAbilitiesWithTag(`GameplayAbility.cpp:999`).
  - 대안 3: ClearAllAbilities(BlueprintCallable, `AbilitySystemComponent.h:983-984`). 부여된 어빌리티를 모두 제거한다.
  - 대안 4: K2_CancelAbility는 자기 자신만 취소한다(`GameplayAbility.h:302`).
  - 취소는 CanBeCanceled를 따른다(`GameplayAbility.cpp:741-743`).
- **BP**
  - A안: Instant GE에 'Cancel Abilities with Tags' 컴포넌트를 넣고 태그를 비워 두어 전부 취소한다. State.Dead는 Loose 태그로 준다.
  - B안: 트리거 발동형 GA_Death에서 CancelAbilitiesWithTag=Ability로 취소한다.
  - ClearAllAbilities는 부활할 때 다시 부여해야 하므로 최후의 수단으로 둔다.

### A9. UGameplayAbility 프로퍼티 이름과 기본값: TRUE
- **주장**: UE 5.8 UGameplayAbility의 정확한 UPROPERTY 이름(AbilityTags인지 AssetTags인지 등), EditDefaultsOnly 여부, 그리고 InstancingPolicy, bRetriggerInstancedAbility, NetExecutionPolicy의 기본값을 확인한다.
- **근거**
  - `GA/Public/Abilities/GameplayAbility.h:474-476`: 프로퍼티 이름은 `AbilityTags`(5.5부터 deprecated)이고 Details 표시는 "AssetTags (Default AbilityTags)"다. `AssetTags`라는 UPROPERTY는 없다.
  - `:690-771`은 모두 `EditDefaultsOnly`이고 BlueprintRead 지정이 없다.
    - ReplicationPolicy(690), InstancingPolicy(694), bRetriggerInstancedAbility(702), NetExecutionPolicy(714), NetSecurityPolicy(718)
    - CostGameplayEffectClass(722), AbilityTriggers(726), CooldownGameplayEffectClass(730)
    - CancelAbilitiesWithTag(738), BlockAbilitiesWithTag(742)
    - ActivationOwnedTags(746), ActivationRequiredTags(750), ActivationBlockedTags(754)
    - Source/Target Required/Blocked Tags(758-771)
  - `GA/Private/Abilities/GameplayAbility.cpp:102`: `InstancingPolicy = InstancedPerExecution`.
  - NetExecutionPolicy는 0(LocalPredicted, `GameplayAbilityTypes.h:59-75`)이고 bRetrigger는 false다.
  - NonInstanced는 deprecated이며 InstancedPerActor로 처리된다(`GameplayAbilityTypes.h:46`, `GameplayAbility.cpp:109-118`).
- **BP**
  - 이 값들은 모두 Class Defaults에서만 편집하고, 그래프에서는 읽거나 쓸 수 없다.
  - MCP나 Python에서는 C++ 이름(AbilityTags, ActivationOwnedTags 등)으로 설정한다. snake_case 이름은 확인하고 쓴다.
  - 상태를 가진 GA는 Instanced Per Actor로 바꾼다.
  - LocalPredicted는 싱글에서 플레이어, AI, 무컨트롤러 폰 모두 문제없다.

### A10. Cancel, Block, ActivationOwnedTags 동작: TRUE
- **주장**: 활성화될 때 CancelAbilitiesWithTag는 에셋 태그가 맞는 다른 실행 중 GA를 취소한다. BlockAbilitiesWithTag는 실행 중에 그 태그를 가진 GA의 활성화를 막는다. ActivationOwnedTags는 실행 중에 소유자 ASC에 붙는다.
- **근거**
  - PreActivate: `GA/Private/Abilities/GameplayAbility.cpp:990` ActivationOwnedTags 추가(Loose, +1), `:999` ApplyAbilityBlockAndCancelTags. 주석(`:1001`)에 따라 자기 자신은 취소하지 않는다.
  - EndAbility: `:870` ActivationOwnedTags 제거, `:885-889` 블록 해제.
  - `GA/Private/AbilitySystemComponent_Abilities.cpp:1329-1348`: 활성 Spec만 보고 `GetAssetTags().HasAny`로 판정한다. Ignore 인스턴스는 건너뛴다(`:1360`).
  - `:1431-1452`, `GameplayAbility.cpp:407`: HasAny는 대상 GA의 에셋 태그를 부모까지 확장한다. 그래서 Ability.Skill은 Ability.Skill.DashSlash를 잡지만 반대는 안 된다.
  - SetShouldBlockOtherAbilities는 BlueprintCallable이다(`:727-738`).
- **BP**
  - Cancel과 Block은 다른 GA의 AssetTags를 본다. 모든 GA에 계층형 AssetTags를 넣는다.
  - Block은 이미 실행 중인 GA를 끊지 않는다. 끊으려면 Cancel을 쓴다.
  - ActivationOwnedTags는 어빌리티가 끝날 때까지 유지된다. 활성 시간 중 일부만 주는 태그는 여기에 넣을 수 없다.

### A11. GA BP 헬퍼 노드: TRUE
- **주장**: UGameplayAbility에 다음 BP 헬퍼가 있다.
  - CommitAbility(bool), K2_EndAbility, K2_CancelAbility
  - GetAvatarActorFromActorInfo, GetAbilitySystemComponentFromActorInfo
  - MakeOutgoingGameplayEffectSpec, K2_ApplyGameplayEffectSpecToTarget, BP_ApplyGameplayEffectToOwner
  - K2_ExecuteGameplayCue(/WithParams), GetCooldownTimeRemaining
- **근거**: `GA/Public/Abilities/GameplayAbility.h`의 C++ 이름과 BP 표시 이름.
  - `:317-318` K2_CommitAbility → 'CommitAbility'. `:321-334` Commit/Check Cooldown/Cost.
  - `:589-590` 'End Ability', `:302-303` 'CancelAbility'(자기 자신만).
  - `:153-166` GetOwningActor/GetAvatarActor/GetAbilitySystemComponent FromActorInfo.
  - `:206-207` MakeOutgoingGameplayEffectSpec(Class, Level=1).
  - `:611-640` ApplyGameplayEffectToOwner, ApplyGameplayEffectSpecToOwner, ApplyGameplayEffectToTarget, ApplyGameplayEffectSpecToTarget.
  - `:666-683` 'Execute GameplayCue On Owner', 'Execute GameplayCueWithParams On Owner', Add/Remove GameplayCue.
  - `:536` SendGameplayEvent, `:810-823` MontageJumpToSection/SetNextSectionName/Stop, `:291` SetShouldBlockOtherAbilities, `:309` SetCanBeCanceled.
  - `:272-273` GetCooldownTimeRemaining은 인스턴스가 아니면 0이다(`GameplayAbility.cpp:2236-2239`, `:1147-1168`).
  - 타깃 데이터: `AbilitySystemBlueprintLibrary.h:234` AbilityTargetDataFromActor.
  - ASC 쪽 대안: `AbilitySystemComponent.h:336-337, 371-372`.
- **BP**
  - GA의 기본 흐름: ActivateAbility → CommitAbility(false면 End) → 몽타주와 WaitGameplayEvent → End Ability.
  - 피해 적용: MakeOutgoingGameplayEffectSpec → Assign Tag Set By Caller Magnitude(Data.Damage) → AbilityTargetDataFromActor → ApplyGameplayEffectSpecToTarget.
  - HUD 쿨다운 표시에는 GetCooldownTimeRemaining을 쓰지 않는다(B6 참고).

### A12. InitGlobalData 자동 호출: TRUE
- **주장**: 5.8에서는 UAbilitySystemGlobals::InitGlobalData()가 자동으로 불리므로, 타깃 데이터와 GameplayCue를 C++ 없이 쓸 수 있다.
- **근거**
  - `GA/Private/GameplayAbilitiesModule.cpp:24-42`: 처음 요청될 때 NewObject → AddToRoot → InitGlobalData(`:38`).
  - `GA/Private/AbilitySystemGlobals.cpp:63-70`: 주석 "we call InitGlobalData automatically in UE5.3+". 본문 `:74-89`.
  - 큐 경로가 비어 있으면 `/Game`을 추가하고 경고를 남긴다(`:645-649`).
  - `GA/Public/GameplayAbilitiesDeveloperSettings.h:29, 60-61`: GameplayCueNotifyPaths(ConfigRestartRequired).
  - 추가 확인: 현재 `SoulCombat/Config/DefaultGame.ini`는 `[/Script/GameplayAbilities.AbilitySystemGlobals] +GameplayCueNotifyPaths=/Game/SoulCombat/GAS/Cues`를 쓴다.
    - 이 프로퍼티는 5.5부터 deprecated지만 여전히 `UPROPERTY(config)`다(`GA/Public/AbilitySystemGlobals.h:359-361`).
    - `GetGameplayCueNotifyPaths`가 DeveloperSettings 경로와 합친다(`GA/Private/AbilitySystemGlobals.cpp:184-187`).
    - 따라서 현재 설정도 유효하다.
- **BP**
  - C++ 초기화 코드는 필요 없다.
  - 큐 경로를 바꾸면 에디터를 재시작한다.
  - GC 노티파이 BP는 `/Game/SoulCombat/GAS/Cues`에 두고, 태그는 GameplayCue.* 아래로 만든다.

---

## 2. 태스크 / 이펙트 / 큐

### B1. PlayMontageAndWait 연쇄와 인터럽트: TRUE
- **주장**: 같은 어빌리티에서 첫 몽타주가 재생 중일 때 두 번째 PlayMontageAndWait(다른 에셋)를 시작하면, 첫 태스크가 OnInterrupted를 낸다.
  - 이 호출이 동기인지 나중인지 확인한다.
  - EndAbility가 bStopWhenAbilityEnds로 무엇을 하는지 확인한다.
  - 몽타주 4개를 안전하게 연결하는 BP 패턴을 정한다.
- **근거**
  - 호출 경로
    1. `GA/Private/Abilities/Tasks/AbilityTask_PlayMontageAndWait.cpp:138` Activate
    2. `GA/Private/AbilitySystemComponent_Abilities.cpp:3047` Montage_Play
    3. `Eng/Private/Animation/AnimInstance.cpp:2770, 3671-3690` StopAllMontagesByGroupName
    4. `Eng/Private/Animation/AnimMontage.cpp:1600` QueueMontageBlendingOutEvent
  - bQueueMontageEvents가 false면 이벤트가 즉시 발생한다(`AnimInstance.cpp:2452-2462`). true인 구간은 Montage_Advance(`:2275`)부터, 노티파이 처리 뒤 TriggerQueuedMontageEvents(`:947-963, 2576-2579`)까지다.
  - 따라서 발생 시점은 다음과 같다.
    - (a) 입력, WaitDelay, 타이머 같은 일반 코드에서 두 번째 몽타주를 시작하면 첫 태스크의 OnInterrupted가 두 번째 Montage_Play 안에서 **동기로** 불린다. ASC의 LocalAnimMontageInfo 설정(`:3072`)이나 두 번째 태스크의 델리게이트 바인딩(`AbilityTask_PlayMontageAndWait.cpp:146-155`)보다 먼저다.
    - (b) 노티파이나 몽타주 이벤트 안에서 시작하면 같은 프레임의 노티파이 처리 뒤에 불린다.
  - 첫 태스크는 OnInterrupted만 내고 EndTask한다(`AbilityTask_PlayMontageAndWait.cpp:40-51`, CVar `AbilitySystem.PlayMontage.AggressiveEndTask` 기본 true). OnBlendOut은 인터럽트가 아닐 때만 나고(`:54`), OnCompleted는 오지 않는다(`:85-103`).
  - 이전 몽타주는 Montage Group이 같거나 둘 다 루트 모션일 때만 멈춘다(`AnimInstance.cpp:2766-2770, 2784-2795`).
  - 위험: 첫 태스크의 OnInterrupted에서 EndAbility를 부르면, 두 번째 태스크는 아직 ActiveTasks에 없다(`Runtime/GameplayTasks/Private/GameplayTask.cpp:285-295`). 그래서 바인딩 없이 반환하고(`AbilityTask_PlayMontageAndWait.cpp:141-144`), 몽타주 2는 어빌리티 없이 계속 재생된다.
  - EndAbility는 모든 태스크에 TaskOwnerEnded를 부른다(`GA/Private/Abilities/GameplayAbility.cpp:852-858`). 이어서 OnDestroy에서 bStopWhenAbilityEnds면 StopPlayingMontage를 한다(`:198-215`).
    - 자기 몽타주가 현재 몽타주일 때만 멈춘다.
    - 델리게이트를 먼저 해제하므로 콜백이 없다(`:241-254`).
  - CancelAbility는 OnGameplayAbilityCancelled를 먼저 방송한다(`GameplayAbility.cpp:759-767`, 태스크 `:67-83`).
  - 태스크 델리게이트는 Ability->IsActive()일 때만 방송된다(`GA/Private/Abilities/Tasks/AbilityTask.cpp:197-199`).
- **BP 패턴**
  - int 변수 ComboStep을 두고, PlayMontageAndWait N을 부르기 직전에 ComboStep=N으로 설정한다.
  - 각 태스크의 OnInterrupted와 OnCancelled는 Branch(ComboStep==N)를 거쳐 End Ability로 연결한다.
  - 중간 태스크의 OnBlendOut/OnCompleted는 Branch(ComboStep==N이고 다음 입력 없음)를 거쳐 End Ability로 연결한다. 마지막 태스크의 OnBlendOut은 End Ability로 연결한다.
  - GetCurrentMontage로 가드하지 않는다. 동기로 불리는 경우 막 null이 되어 있다(`AbilitySystemComponent_Abilities.cpp:3531-3538`).
  - bStopWhenAbilityEnds=true, bAllowInterruptAfterBlendOut=false로 둔다. 모든 몽타주는 같은 그룹(DefaultGroup.DefaultSlot)에 둔다.

### B2. StartSection과 연결되지 않은 섹션: TRUE
- **주장**: PlayMontageAndWait의 StartSection은 그 섹션으로 바로 건너뛴다. 섹션이 연결돼 있지 않으면 몽타주는 그 섹션 끝에서 끝나고 OnBlendOut/OnCompleted가 온다.
- **근거**
  - `GA/Private/AbilitySystemComponent_Abilities.cpp:3081-3084`: Montage_Play 다음에 Montage_JumpToSection을 부른다. 시작 시간은 StartSection이 덮어쓴다(`AbilityTask_PlayMontageAndWait.h:61`).
  - `Eng/Private/Animation/AnimMontage.cpp:2619-2638`: 다음 섹션이 없고 bEnableAutoBlendOut이면, 남은 시간이 BlendOut 시간 안으로 들어올 때 인터럽트가 아닌 Stop을 한다. 그래서 OnBlendOut 뒤에 OnCompleted가 온다(`AbilityTask_PlayMontageAndWait.cpp:52-55, 87-92`).
  - 주의 1: 에디터에서 섹션을 추가하면 이전 섹션에 자동으로 연결된다(`AnimMontage.cpp:366-374`).
  - 주의 2: bEnableAutoBlendOut=false면 섹션 끝에서 정지한 채(`:2735-2748`) 아무 이벤트도 오지 않는다.
- **BP**
  - 한 몽타주의 섹션으로 콤보를 만들 수 있다.
  - 같은 몽타주라도 새 PlayMontageAndWait를 시작하면 이전 태스크는 인터럽트된다.
  - 인터럽트 이벤트 없이 다음 섹션으로 넘기려면 GA 노드 'MontageJumpToSection'(`GameplayAbility.h:810-811`)이나 'MontageSetNextSectionName'(`:814-815`)을 쓴다.

### B3. WaitDelay, WaitGameplayEvent, WaitInputRelease: TRUE
- **주장**: WaitInputRelease는 ASC 입력 바인딩(AbilitySpecInputReleased)에 의존하는데, BP의 TryActivateAbility는 이 값을 설정하지 않는다.
- **근거**
  - WaitDelay(`GA/Private/Abilities/Tasks/AbilityTask_WaitDelay.cpp:26-50`)는 월드 타이머를 쓴다.
  - WaitGameplayEvent(`AbilityTask_WaitGameplayEvent.cpp:28-64`): A6 참고.
  - WaitInputRelease(`AbilityTask_WaitInputRelease.cpp:55-81`)는 `AbilityReplicatedEventDelegate(InputReleased)`만 듣는다.
    - 이 이벤트는 AbilityLocalInputReleased(InputID)만 호출한다(`AbilitySystemComponent_Abilities.cpp:2846-2873`).
    - TryActivateAbility는 `Spec.InputPressed`를 설정하지 않는다. 설정하는 곳은 `:2817`, `:2916`, `:2106`뿐이다.
    - bTestAlreadyReleased=true면 즉시 발생한다(`WaitInputRelease.cpp:62-69`).
  - 5.8 신규: ASC의 `PressInputID(int32)` / `ReleaseInputID(int32)`가 BlueprintCallable이다(`AbilitySystemComponent.h:1370-1379`, `.cpp:2875-2883`). 어빌리티가 비활성이면 PressInputID가 활성화까지 한다.
  - Generic confirm/cancel ID 기본값은 INDEX_NONE이다(`AbilitySystemComponent.cpp:66-67`).
- **BP**
  - TryActivateAbility로 켠 GA에서는 WaitInputRelease를 쓰지 않는다.
  - 떼기 감지는 게임플레이 이벤트로 하거나, Give Ability(InputID=N) 후 Enhanced Input Started에서 'Press Input ID', Completed에서 'Release Input ID'를 부른다.

### B4. 쿨다운 GE와 Grant Tags 컴포넌트: TRUE
- **주장**: 쿨다운은 TargetTagsGameplayEffectComponent가 붙은 GE로 만든다. GetCooldownTags와 CheckCooldown은 이 컴포넌트가 주는 태그(GetGrantedTags/CachedGrantedTags)를 읽는다. InheritableOwnedTagsContainer는 deprecated다.
- **근거**
  - `GA/Private/Abilities/GameplayAbility.cpp:1216-1220`: GetCooldownTags는 `CDGE->GetGrantedTags()`를 반환한다. CheckCooldown은 `:1064-1104`.
  - `GA/Public/GameplayEffect.h:2176`: CachedGrantedTags. 이 값은 OnGameplayEffectChanged(`GameplayEffect.cpp:391-412`)에서 채워지며, PostLoad(`:375-379`)와 PostCDOCompiled(`:485-515`)에서 불린다.
  - 컴포넌트가 캐시에 반영하는 곳: `GA/Private/GameplayEffectComponents/TargetTagsGameplayEffectComponent.cpp:32-36, 80-84`.
  - 런타임에 태그를 붙이는 곳: `GameplayEffect.cpp:4663/4677`.
  - deprecated 표시: `GameplayEffect.h:2349-2351`. 변환은 `GameplayEffect.cpp:683-702`.
  - Instant GE에 이 컴포넌트를 넣으면 검증 에러가 난다(`TargetTagsGameplayEffectComponent.cpp:55-60`).
  - GetCooldownTimeRemaining은 MatchAnyOwningTags를 쓴다(`GameplayEffect.cpp:6112-6127`).
- **BP**
  - 설정: DurationPolicy=HasDuration, 'Grant Tags to Target Actor'의 Add Tags=Cooldown.<스킬>. 이 GE를 CooldownGameplayEffectClass에 지정하고, 그래프에서 CommitAbility를 부른다.
  - 태그 검사가 계층형이라 스킬마다 고유한 잎 태그를 쓴다.
  - 스크립트로 설정한 뒤에는 GE를 컴파일하고 저장해 캐시를 다시 만든다.

### B5. GE 프로퍼티 이름과 컴포넌트 클래스: TRUE
- **주장**: UE 5.8 GameplayEffect의 프로퍼티 이름(DurationPolicy, DurationMagnitude, Period, Modifiers, GEComponents, GameplayCues, StackingType 등)과 GE 컴포넌트 클래스(TargetTags, AssetTags, RemoveOther, Immunity)의 정확한 클래스 경로를 확인한다.
- **근거**: `GA/Public/GameplayEffect.h`
  - 기본 프로퍼티
    - 2256 DurationPolicy(Instant/Infinite/HasDuration, `:686-694`), 2260 DurationMagnitude
    - 2268 Period, 2272 bExecutePeriodicEffectOnApplication
    - 2280 Modifiers, 2284 Executions, 2332 GameplayCues
    - 2409 StackingType(5.7부터 deprecated, UPROPERTY는 유지), 2413 StackLimitCount
    - 2466 `protected` GEComponents(DisplayName "Components")
  - FGameplayModifierInfo(`:565-596`): Attribute, ModifierOp, ModifierMagnitude.
  - MagnitudeCalculationType(`:275, 371-376`): ScalableFloat, AttributeBased, CustomCalculationClass, SetByCaller.
  - **5.8에서 EGameplayModOp 이름이 바뀌었다**(`GA/Public/GameplayEffectTypes.h:118-149`). 예전 이름 Additive, Multiplicitive, Division은 숨은 별칭으로만 남았다.

    | 값 | 이름 |
    | --- | --- |
    | 0 | AddBase |
    | 1 | MultiplyAdditive |
    | 2 | DivideAdditive |
    | 3 | Override |
    | 4 | MultiplyCompound |
    | 5 | AddFinal |

  - 컴포넌트 클래스 경로(`/Script/GameplayAbilities.`)

    | 클래스 | 에디터 표시 이름 | 주요 필드 |
    | --- | --- | --- |
    | TargetTagsGameplayEffectComponent | "Grant Tags to Target Actor" | InheritableGrantedTagsContainer |
    | AssetTagsGameplayEffectComponent | "Tags This Effect Has (Asset Tags)" | InheritableAssetTags |
    | RemoveOtherGameplayEffectComponent | "Remove Other Effects" | RemoveGameplayEffectQueries |
    | ImmunityGameplayEffectComponent | "Immunity to Other Effects" | ImmunityQueries |

    그 밖에 BlockAbilityTags, TargetTagRequirements, AdditionalEffects, CancelAbilityTags 컴포넌트도 있다.
- **BP / Python**
  - snake_case 이름은 duration_policy, duration_magnitude, period, modifiers, executions, gameplay_cues, stacking_type, stack_limit_count, ge_components다.
  - 태그 컨테이너 필드는 added, removed, combined_tags다.
  - 모디파이어 연산은 5.8 이름을 쓴다. 더하기는 ADD_BASE, 설정은 OVERRIDE다.
  - 스크립트로 수정한 뒤에는 컴파일하고 저장한다.

### B6. UI에서 쿨다운 남은 시간 읽기: PARTIAL
- **주장**: ASC와 쿨다운 태그로 남은 시간과 전체 시간을 읽는 BP 방법이 있다. 후보는 GetActiveEffectsWithAllTags, BP 라이브러리의 GetActiveGameplayEffectRemainingDuration/TotalDuration/StartTime, GetActiveEffectsTimeRemaining, GetGameplayEffectDuration이다.
- **근거**
  - `GA/Public/AbilitySystemComponent.h:815-820`: GetActiveEffects(Query)와 GetActiveEffectsWithAllTags는 BP에서 쓸 수 있다.
  - 그러나 GetActiveEffectsWithAllTags는 `MakeQuery_MatchAllEffectTags`다(`AbilitySystemComponent.cpp:1769-1772`). 이 쿼리는 **에셋 태그만** 본다(`GameplayEffect.cpp:6133-6143`). OwningTagQuery는 에셋 태그와 Grant 태그를 같이 본다(`:6112-6127`).
  - 그래서 Grant 태그만 있는 쿨다운 GE는 GetActiveEffectsWithAllTags로 찾을 수 없다.
  - BP 비노출: GetActiveEffectsTimeRemaining, GetActiveEffectsDuration, GetGameplayEffectDuration 등(`AbilitySystemComponent.h:412-419, 805-827`).
  - BP 노출: `GA/Public/AbilitySystemBlueprintLibrary.h:547-561`의 GetActiveGameplayEffectStartTime/ExpectedEndTime/TotalDuration/RemainingDuration(Handle). 구현은 `.cpp:1256-1311`.
  - FGameplayEffectQuery는 BlueprintType이다(`GameplayEffect.h:1470-1497`). 태그 쿼리 노드는 `Runtime/GameplayTags/Classes/BlueprintGameplayTagLibrary.h:220` MakeGameplayTagQuery_MatchAnyTags다.
  - 비동기 노드: WaitGameplayTagAddToActor, WaitGameplayTagRemoveFromActor, WaitGameplayTagCountChangedOnActor, WaitGameplayEffectAppliedToActor(`GA/Public/Abilities/Async/*`).
- **BP 레시피**
  1. MakeGameplayTagQuery_MatchAnyTags(CooldownTag)
  2. Make GameplayEffectQuery(OwningTagQuery)
  3. ASC 'Get Active Gameplay Effects for Query'
  4. Remaining = GetActiveGameplayEffectRemainingDuration, Total = GetActiveGameplayEffectTotalDuration
  - 대안: 쿨다운 GE에 같은 태그로 AssetTags 컴포넌트도 넣으면 GetActiveEffectsWithAllTags도 동작한다. **현재 SoulCombat은 이 대안을 사용한다.** `02-build-plan.md`와 2026-09-30의 실제 `WBP_SkillSlot.Refresh` 그래프에서도 확인했다. 위 OwningTagQuery 레시피는 Grant 태그만 두는 설계의 선택지이며, 현재 HUD가 잘못되었다는 의미는 아니다.
  - 조회 부담을 줄여야 할 때는 Wait Gameplay Tag Add/Remove To Actor로 타이머를 시작하고 멈추는 방법을 검토한다. 현재 구현은 Refresh에서 조회한다.
  - Infinite GE는 -1을 반환한다.

### B7. Wait For Attribute Changed와 Get Float Attribute: TRUE
- **주장**: UAbilityAsync_WaitAttributeChanged('Wait for Attribute Changed')는 IAbilitySystemInterface가 없는 액터에서도 동작한다. Get Float Attribute와 GetFloatAttributeFromAbilitySystemComponent 노드도 마찬가지다.
- **근거**
  - `GA/Private/Abilities/Async/AbilityAsync_WaitAttributeChanged.cpp:9-30`: `AbilityAsync.cpp:45-48`을 거쳐 A5의 폴백을 쓴다. 활성화 시점에 ASC가 없으면 즉시 EndAction한다.
  - 헤더 `.h:26-27`: 출력은 Changed(Attribute, NewValue, OldValue)다.
  - Get Float Attribute(`GA/Public/AbilitySystemBlueprintLibrary.h:177-190`, `.cpp:265-284`)는 AttributeSet이 없으면 0과 bSuccessfullyFoundAttribute=false를 반환한다.
  - ASC::GetGameplayAttributeValue는 BlueprintPure다(`AbilitySystemComponent.h:205-206`).
  - DefaultStartingData는 Attributes와 DefaultStartingTable이 **둘 다** 있어야 세트를 만든다(`AbilitySystemComponent.cpp:206-211`).
- **BP**
  - BP로 붙인 ASC로 동작한다.
  - 노드가 실행될 때 ASC와 AttributeSet(InitStats)이 이미 있어야 한다.
  - 반환된 AsyncAction은 변수에 저장해 두었다가 Destruct에서 Cancel한다.

### B8. 인터페이스 없는 대상의 GameplayCue 위치: PARTIAL
- **주장**: IAbilitySystemInterface가 없는 대상 액터에서 Burst, Static, Looping 큐가 EffectContext의 히트 결과나 Origin으로 올바른 대상과 위치를 얻는다. BP에서는 FGameplayCueParameters.Location, K2_ExecuteGameplayCueWithParams, UAbilitySystemBlueprintLibrary::ExecuteGameplayCueOnActor로 위치를 넘길 수 있다. Burst의 기본 생성 조건과 배치가 위치를 어떻게 쓰는지 확인한다.
- **근거**
  - 라우팅: 인터페이스가 없어도 큐는 처리된다(`GA/Private/GameplayCueManager.cpp:203-238`). ASC에서 나온 큐의 대상은 AvatarActor다(`AbilitySystemComponent.cpp:1448, 1507-1511`).
  - GE에서 만든 큐 파라미터는 EffectContext만 복사하고 Location은 채우지 않는다(`AbilitySystemGlobals.cpp:409-449`).
  - Burst의 스폰 위치 우선순위(`GA/Private/GameplayCueNotifyTypes.cpp:225-282, 312-349`)
    1. blocking HitResult
    2. 0이 아닌 CueParameters.Location
    3. TargetComponent(메시)의 SocketName 소켓 트랜스폼
    - EffectContext Origin은 쓰이지 않는다.
  - 기본 배치는 DoNotAttach, Scale 1이다(`:136-148, 212-223`).
  - 'Execute GameplayCue On Actor (Burst)'는 UAbilitySystemBlueprintLibrary가 아니라 **UGameplayCueFunctionLibrary**에 있다(`GA/Public/GameplayCueFunctionLibrary.h:36-37`, `.cpp:26-48`). MakeGameplayCueParametersFromHitResult는 `.cpp:15-24`.
  - 라이브러리의 MakeGameplayCueParameters와 EffectContextAddHitResult는 `AbilitySystemBlueprintLibrary.h:311-351, 411`.
  - GA의 'Execute GameplayCueWithParams On Owner'는 **시전자** ASC에서 실행된다(`GameplayAbility.cpp:1729-1738`).
- **BP**
  - 적 피격 이펙트는 'Execute GameplayCue On Actor (Burst)'(Target=피격 적, Parameters.Location/Normal)로 재생한다.
  - GE로 재생하는 큐는 EffectContextAddHitResult로 히트 결과를 컨텍스트에 넣는다.
  - 둘 다 없으면 메시 원점(발밑)에 스폰된다. GC의 DefaultPlacementInfo.SocketName을 폴백으로 지정한다.

### B9. Looping 큐와 제거: TRUE
- **주장**: Looping 큐(GameplayCueNotify_Looping 액터)는 Infinite/HasDuration GE의 GameplayCues나 BP의 AddGameplayCue(GA의 K2_AddGameplayCue, AddGameplayCueToOwner)로 붙일 수 있다. BP에서 보이는 노드 이름과 GE가 끝날 때의 제거를 확인한다.
- **근거**
  - GE가 붙을 때 OnActive와 WhileActive, 제거되거나 만료될 때 Removed 이벤트가 난다(`GA/Private/GameplayEffect.cpp:4555-4557, 4709-4735, 5024-5047, 4853-4868`).
  - GA 노드(`GameplayAbility.h:666-682`): 'Add GameplayCue To Owner'(bRemoveOnAbilityEnd), 'Remove GameplayCue From Owner'.
    - bRemoveOnAbilityEnd면 EndAbility에서 제거된다(`GameplayAbility.cpp:1757-1775, 871-876`).
  - 액터 노드: 'Add/Remove GameplayCue On Actor (Looping)'(`GameplayCueFunctionLibrary.h:42-49`).
  - Looping 액터 기본값: bAutoDestroyOnRemove=true, AttachToTarget(`GameplayCueNotify_Looping.cpp:12-20, 108-110`). 제거 처리는 `GameplayCueNotify_Actor.cpp:290-304`.
  - 주의: "같은 태그가 아직 있으면 제거를 건너뛰는" 보호(`:219, 250-258`)는 대상이 IGameplayTagAssetInterface를 구현할 때만 동작한다. BP ACharacter는 구현하지 않는다.
- **BP**
  - 버프와 오라는 GE의 GameplayCues로 붙이면 만료될 때 자동으로 제거된다.
  - 어빌리티 수명 동안만 필요한 FX는 'Add GameplayCue To Owner'(bRemoveOnAbilityEnd=true)로 붙인다.
  - 같은 큐 태그를 두 출처에서 동시에 붙이지 않는다.

---

## 3. 엔진 게임플레이

### C1. PlaySlotAnimationAsDynamicMontage: TRUE
- **주장**: UAnimInstance::PlaySlotAnimationAsDynamicMontage(와 그 변형)는 BlueprintCallable이고 UAnimMontage*를 반환한다.
- **근거**
  - `Eng/Classes/Animation/AnimInstance.h:590-591`(BlueprintCallable, UAnimMontage* 반환). 변형 `:594-595`(_WithBlendArgs), `:598-599`(_WithBlendSettings).
  - GAS의 PlayMontageAndWait는 UAnimMontage 에셋만 받는다(`GA/Public/Abilities/Tasks/AbilityTask_PlayMontageAndWait.h:66-67`).
- **BP**
  - SlotNodeName은 AnimBP에 실제로 있는 슬롯(DefaultSlot)이어야 한다.
  - GA 안에서는 몽타주 에셋이 필요하다. 동적 몽타주는 GA 밖 연출에서만 쓴다.

### C2. LaunchCharacter, 입력 벡터, Jump, Landed: TRUE
- **주장**: ACharacter::LaunchCharacter, GetLastInputVector/GetLastMovementInputVector, Jump/StopJumping, Landed 이벤트의 BP 이름을 확인한다.
- **근거**
  - `Eng/Classes/GameFramework/Character.h:907-908` LaunchCharacter, `:827-837` Jump/StopJumping.
  - `:958-959` OnLanded(BlueprintImplementableEvent), `:947-948` LandedDelegate. ReceiveLanded는 없다.
  - `Eng/Private/Character.cpp:301-306`: OnLanded를 부른 뒤 LandedDelegate를 방송한다.
  - `Eng/Classes/GameFramework/Pawn.h:508-530`: GetPendingMovementInputVector, GetLastMovementInputVector, ConsumeMovementInputVector.
  - `PawnMovementComponent.h:77-78`: GetLastInputVector.
  - `Eng/Private/Components/CharacterMovementComponent.cpp:1237-1246`: HandlePendingLaunch는 **항상** `SetMovementMode(MOVE_Falling)`로 바꾼다.
- **BP**
  - 노드 이름: Launch Character, Jump, Stop Jumping, 'Event On Landed', 'Bind Event to Landed Delegate'.
  - 같은 프레임의 입력은 Get Pending Movement Input Vector로 읽는다.
  - Z가 0인 Launch도 잠깐 공중 상태가 되고 곧 OnLanded가 온다.

### C3. NavMesh 없는 AI 이동: TRUE
- **주장**: AIController에 빙의된 ACharacter는 NavMesh가 없어도 매 틱 APawn::AddMovementInput을 호출하면 움직인다.
- **근거**
  - `Eng/Private/Components/CharacterMovementComponent.cpp:1662, 1751-1757`: IsLocallyControlled면 ControlledCharacterMove를 한다.
  - Standalone에서는 AIController도 로컬로 판정된다(`Eng/Private/Controller.cpp:90-97`, `Pawn.cpp:272-275`).
  - 이동 가속은 `CMC.cpp:6441-6457`에서 계산한다. 입력 누적은 `Pawn.cpp:820-830, 859-864`이고 IgnoreMoveInput이면 막힌다.
  - MoveTo는 NavigationSystem이 필요하다(`Runtime/AIModule/Private/AIController.cpp:846-848, 886-888`).
  - `Pawn.cpp:53`: `AutoPossessAI = PlacedInWorld`. SpawnActor로 만든 폰은 PlacedInWorldOrSpawned나 Spawned일 때만 컨트롤러를 받는다(`:153-155`).
- **BP**
  - Add Movement Input으로 추적한다. AI MoveTo와 SimpleMoveTo는 쓰지 않는다.
  - 런타임에 스폰하는 적은 Auto Possess AI를 'Placed in World or Spawned'로 바꾸거나 Spawn Default Controller를 부른다.
  - 이동만 막으려면 Set Ignore Move Input을 쓴다.

### C4. OpenLevel과 PlayerStart 선택: TRUE
- **주장**: OpenLevel 뒤에 특정 PlayerStart에서 스폰시킬 수 있다. BP에서 'LevelName#PortalName' 형식을 쓸 수 있고, ChoosePlayerStart/FindPlayerStart를 BP에서 오버라이드할 수 있다.
- **근거**
  - `Eng/Private/GameplayStatics.cpp:981-1006` OpenLevel.
  - `Eng/Private/URL.cpp:184-219`: `#` 뒤는 Portal로 처리된다. `:589-592`.
  - `UnrealEngine.cpp:16647`, `LevelActor.cpp:1087`: Portal이 Login으로 전달된다.
  - `Eng/Private/GameModeBase.cpp`
    - `:772-790, 838-849`: InitNewPlayer → FindPlayerStart(Player, Portal)
    - `:1149-1165`: **PlayerStartTag == Portal**이면 그 스타트를 쓰고, 아니면 ChoosePlayerStart
    - `:1241-1261`: RestartPlayer는 StartSpot을 재사용한다.
  - `:1106-1111`: 기본 ChoosePlayerStart는 PIE의 PlayerStartPIE를 먼저 고르고, **그 외에는 비어 있는 PlayerStart 중 무작위**로 고른다.
  - `Eng/Classes/GameFramework/GameModeBase.h:404-427`: ChoosePlayerStart와 FindPlayerStart는 BlueprintNativeEvent, K2_FindPlayerStart는 BlueprintPure다.
  - `PlayerStart.h:27-28`: PlayerStartTag.
- **BP**
  - 'Open Level (by Name)'에 `L_Dungeon#FromTown` 형식으로 넣는다. Absolute는 true로 둔다. 옵션은 `Foo=1#Tag`처럼 쓴다.
  - 오버라이드가 필요하면 FindPlayerStart가 아니라 ChoosePlayerStart를 오버라이드한다.

### C5. CustomTimeDilation과 SetGlobalTimeDilation: TRUE
- **주장**: AActor::CustomTimeDilation을 BP에서 설정할 수 있고(히트스탑), UGameplayStatics::SetGlobalTimeDilation이 있다.
- **근거**
  - `Eng/Classes/GameFramework/Actor.h:796-798`: BlueprintReadWrite.
  - 액터 틱과 컴포넌트 틱에 곱해진다(`Actor.cpp:379`, `Actor.h:4890-4891`). CMC, 애님, ASC 틱이 모두 느려진다.
  - 액터의 latent Delay는 `GetDeltaSeconds()`를 쓰므로 영향을 받지 않는다(`Actor.cpp:2025`).
  - SetGlobalTimeDilation: `GameplayStatics.h:385-393`. 값은 0.0001~20으로 클램프된다(`WorldSettings.cpp:345-348`, `BaseGame.ini:200-201`).
  - 타이머와 Delay는 전역 딜레이션의 영향을 받는다(`LevelTick.cpp:1596, 1816`).
- **BP**
  - 개별 히트스탑은 Custom Time Dilation을 0.05로 두고 Delay 뒤 1.0으로 되돌린다.
  - WaitDelay와 Delay는 CustomTimeDilation으로 느려지지 않는다. 그래서 애니메이션만 느려지고 WaitDelay 타이밍은 그대로 흘러간다.

### C6. WidgetComponent: TRUE
- **주장**: UWidgetComponent::GetUserWidgetObject는 BP에 노출돼 있고, 프로퍼티 이름은 Space, DrawSize, WidgetClass다.
- **근거**
  - `UMG/Public/Components/WidgetComponent.h:180-181`: GetUserWidgetObject(UnsafeDuringActorConstruction).
  - 프로퍼티: `:447-460` Space, WidgetClass, DrawSize(protected, EditAnywhere). `:505-510` bDrawAtDesiredSize, Pivot.
  - SetWidgetSpace, SetDrawSize, SetWidget은 BP 노드가 있다. SetWidgetClass는 C++ 전용이다(`:337-338`).
  - 컴포넌트 BeginPlay의 InitWidget(`UMG/Private/Components/WidgetComponent.cpp:748-751`)이 액터 BeginPlay보다 먼저 실행된다(`Eng/Private/Actor.cpp:4825, 4846`).
- **BP**
  - Space, WidgetClass, DrawSize는 디테일 패널에서 설정한다. Python에서는 `space`, `widget_class`, `draw_size`다.
  - 액터 BeginPlay에서 Get User Widget Object → Cast를 써도 된다. Construction Script에서는 쓰지 않는다.

### C7. 기본 UMG 폰트의 한글: TRUE
- **주장**: 5.8 기본 UMG 폰트(Roboto)로 PIE에서 한글이 렌더링된다.
- **근거**
  - 기본 폰트는 Roboto다(`UMG/Private/Components/TextBlock.cpp:35-36`, `Widget.cpp:1760-1765`, `Engine/Config/BaseEngine.ini:97-98`).
  - Roboto 컴포지트 폰트에 FallbackTypeface `/Engine/EngineFonts/Faces/DroidSansFallback`이 있다.
  - 코드포인트가 없으면 폴백 폰트를 쓴다(`Runtime/SlateCore/Private/Fonts/FontCacheCompositeFont.cpp:664-680`).
  - DroidSansFallback은 한글 음절 11172자를 모두 포함한다. 엔진에 Noto CJK 폰트는 없다.
- **BP**: 폰트를 추가하지 않아도 한글이 깨지지 않는다. Bold를 지정해도 한글은 굵게 나오지 않아 라틴 글자와 굵기가 섞여 보인다.

### C8. 입력 모드, 커서, 뷰포트, DisableInput: TRUE
- **주장**: SetInputMode 계열 BP 함수 이름, bShowMouseCursor, AddToViewport/RemoveFromParent, 폰의 DisableInput 동작을 확인한다.
- **근거**
  - `UMG/Public/Blueprint/WidgetBlueprintLibrary.h:48-64`: SetInputMode_UIOnlyEx("Set Input Mode UI Only"), SetInputMode_GameAndUIEx, SetInputMode_GameOnly.
  - `Eng/Classes/GameFramework/PlayerController.h:526-527`: bShowMouseCursor.
  - `UMG/Public/Blueprint/UserWidget.h:341-358`: AddToViewport. RemoveFromViewport는 5.1부터 deprecated다. RemoveFromParent는 `Widget.h:775-776`.
  - `Actor.h:1435-1436` DisableInput은 폰에서 `bInputEnabled=false`만 한다(`Pawn.cpp:1177-1182`). BuildInputStack은 폰의 InputComponent만 뺀다(`PlayerController.cpp:2668-2679`).
  - `Controller.h:359-375`: SetIgnoreMoveInput, ResetIgnoreMoveInput, SetIgnoreLookInput.
- **BP**
  - 폰의 Disable Input은 **PlayerController BP에 있는 입력 이벤트를 막지 않는다**.
  - 창을 열 때: Set Input Mode UI Only + Show Mouse Cursor. 닫을 때: Remove from Parent → Set Input Mode Game Only.

### C9. SphereOverlapActors와 ObjectTypeQuery: TRUE
- **주장**: SphereOverlapActors의 인자는 ObjectTypes, ActorClassFilter, ActorsToIgnore이고, 기본 설정에서 ObjectTypeQuery3이 Pawn이다.
- **근거**
  - `Eng/Classes/Kismet/KismetSystemLibrary.h:1091-1092`. 구현은 `.cpp:1672-1705`이며 액터 목록은 AddUnique로 중복을 제거한다(`:1652-1665`).
  - ObjectTypeQuery 매핑은 C++에 고정돼 있다(`Eng/Private/Collision/CollisionProfile.cpp:370-382, 449/458`, `EngineTypes.h:1101-1108`): OTQ1 WorldStatic, OTQ2 WorldDynamic, **OTQ3 Pawn**, OTQ4 PhysicsBody, OTQ5 Vehicle, OTQ6 Destructible.
- **BP**
  - Make Array에 Pawn을 넣는다. Python에서는 ObjectTypeQuery3이다.
  - 커스텀 채널은 OTQ7부터 붙는다.
  - 맞은 대상의 ASC는 Get Ability System Component로 얻는다.

### C10. MoveComponentTo: TRUE
- **주장**: UKismetSystemLibrary::MoveComponentTo latent 노드를 문 열기에 쓸 수 있다.
- **근거**
  - `Eng/Classes/Kismet/KismetSystemLibrary.h:715-716`: Latent, 입력 실행 핀 Move/Stop/Return(`:53-62`).
  - `Eng/Private/KismetSystemLibrary.cpp:2682-2715`.
  - `InterpolateComponentToAction.h:77, 119, 145`: 스윕 없이 SetRelativeLocation/Rotation으로 움직인다.
  - Movable이 아니면 이동이 거부된다(`SceneComponent.cpp:3383-3402, 3439`).
- **BP**
  - 이벤트 그래프에서만 쓸 수 있다(latent).
  - 좌표는 상대 좌표다. 문 메시는 Movable로 둔다.
  - 스윕이 없어 **폰을 밀지 않고 통과한다**.
  - 완료 처리는 Completed 핀에 연결한다.

---

## 4. 템플릿 에셋

에셋은 이름 맵, 임포트/익스포트 맵, 태그 프로퍼티를 직접 디코딩해 확인했다(태그 형식: `Engine/Source/Runtime/CoreUObject/Private/UObject/PropertyTag.cpp:420-520`). 근거 위치는 파일과 바이트 오프셋이다.

### D1a. 몽타주 섹션과 노티파이: TRUE
- **주장**: AM_ComboAttack, AM_ChargedAttack, AM_Dash의 섹션 이름과 노티파이 클래스를 바이너리 `.uasset`에서 읽을 수 있다.
- **근거**
  - `Content/Variant_Combat/Anims/AM_ComboAttack`: 슬롯 DefaultSlot, BlendIn 0.1, BlendOut 0.2(Cubic).

    | 섹션 | 시작 | 시퀀스 | 길이 |
    | --- | --- | --- | --- |
    | Melee01 | 0.0 | MM_Attack_01 | 1.0 |
    | Melee02 | 1.0 | MM_Attack_02 | 1.0 |
    | Melee03 | 2.0 | MM_Attack_03 | 1.667 |

    | 몽타주 시간(섹션 기준) | 노티파이 |
    | --- | --- |
    | 0.467 (+0.467) | AN_AttackDamage_C(hand_r) |
    | 0.533 (+0.533) | AN_AttackCombo_C |
    | 1.467 (+0.467) | AN_AttackDamage_C(hand_l) |
    | 1.567 (+0.567) | AN_AttackCombo_C |
    | 2.4 (+0.4) | AN_AttackDamage_C(foot_r) |

    Melee03에는 콤보 노티파이가 없다. NotifyName 문자열(AN_Melee*)은 예전 표시 이름일 뿐이다.
  - `AM_ChargedAttack`: MM_ChargedAttack(1.833초), DefaultSlot, 블렌드 0.1/0.2.
    - 섹션: Default @0, Charge @0.333, Attack @0.8.
    - 노티파이: AN_ChargedAttack_C @0.333, @0.767. AN_AttackDamage_C(hand_r) @1.167(Attack 섹션 기준 +0.367).
  - `Content/Variant_Platforming/Anims/AM_Dash`: MM_Dash(0.967초), Default 섹션, DefaultSlot.
    - AnimNotifyState_DisableRootMotion 0.633~0.967.
    - AN_EndDash_C @0.633.
  - 노티파이 BP(부모 AnimNotify, Received_Notify)
    - AN_AttackCombo → BPI_Attacker 'Check Combo'
    - AN_ChargedAttack → 'Check Charged Attack'
    - AN_AttackDamage → 'Do Attack Trace'(Damage Source Bone)
    - AN_EndDash → GetOwner를 **BP_PlatformingCharacter로 캐스트**한 뒤 'End Dash'
  - BPI_Attacker는 `Variant_Combat/Blueprints`에 있는 BP 인터페이스다.
- **BP**
  - 섹션 이름(Melee01~03, Default, Charge, Attack)은 그대로 쓴다.
  - 캐릭터가 BPI_Attacker를 구현하면 전투 노티파이를 GAS 이벤트로 넘길 수 있다. 구현하지 않으면 조용히 무시된다.
  - AN_EndDash는 우리 캐릭터에서는 캐스트가 실패해 아무 일도 하지 않는다.

### D1b. 섹션 연결(NextSectionName)을 알 수 없다는 주장: FALSE
- **주장**: 섹션 연결(NextSectionName)은 바이너리에서 알아낼 수 없을 것이다.
- **근거**: NextSectionName은 태그된 NameProperty로 저장돼 있어 읽을 수 있다.
  - AM_ComboAttack: Melee01, Melee02, Melee03 모두 **None**(오프셋 11178, 11610, 12042). 섹션이 연결돼 있지 않다.
  - AM_ChargedAttack: Default → Charge, **Charge → Charge(자기 루프)**, Attack → None.
  - AM_Dash: Default → None.
  - 엔진 동작
    - `Eng/Private/Animation/AnimMontage.cpp:2619-2637`: 다음 섹션이 없으면 BlendOut 시간 전에 Stop한다.
    - `:2734-2748`: 섹션 끝에서 bPlaying=false가 된다.
    - Montage_JumpToSection과 Montage_SetNextSection은 BlueprintCallable이다(`Eng/Classes/Animation/AnimInstance.h:662-663, 678-679`).
- **BP**
  - Melee01만 재생하면 약 0.8초에 블렌드아웃이 시작된다. 이어 가려면 그 전에 Jump To Section이나 Set Next Section을 부른다.
  - Charge 섹션은 떼기 전까지 무한 루프한다.

### D2. AnimBP의 슬롯: TRUE
- **주장**: AnimBP인 ABP_Unarmed와 ABP_Manny_Combat에 DefaultSlot 슬롯이 있다(DefaultSlot/DefaultGroup 검색).
- **근거**
  - AnimGraphNode_Slot이 하나씩 있고 모두 SlotName이 'DefaultSlot'이다.
    - `Content/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed`(오프셋 180622)
    - `Content/Variant_Combat/Anims/ABP_Manny_Combat`(187471)
    - `Content/Variant_Platforming/Anims/ABP_Manny_Platforming`(233776)
  - ABP_Manny_Combat은 IsSlotActive도 호출한다.
  - DefaultGroup은 스켈레톤 `Content/Characters/Mannequins/Meshes/SK_Mannequin`에 있다(오프셋 142481). 그룹 구성은 [FullBody, DefaultSlot, UpperBody, …, Arms]이고, AdditiveGroup=[AdditiveHitReact]다.
  - RootMotionMode는 기본값 RootMotionFromMontagesOnly다(`Eng/Private/Animation/AnimInstance.cpp:202`).
- **BP**
  - DefaultSlot 몽타주는 세 AnimBP 모두에서 재생된다.
  - UpperBody, FullBody, AdditiveHitReact 슬롯은 AnimBP에 노드가 없다. 이 슬롯으로 만든 몽타주는 **보이지 않는다**. 즉 상체만 재생하는 몽타주는 쓸 수 없다.

### D3a. 사용 가능한 시퀀스와 루트 모션: TRUE
- **주장**: `Characters/Mannequins/Anims` 아래에 쓸 수 있는 시퀀스를 확인하고, MM_Attack_0x, MM_ChargedAttack, MM_Dash에 루트 모션이 켜져 있는지 확인한다.
- **근거**
  - 공격: MM_Attack_01(1.0s), 02(1.0s), 03(1.667s), MM_ChargedAttack(1.833s).
  - 대시와 점프: MM_Dash(0.967s), MM_WallJump, MM_Jump, MM_Land, MM_Fall_Loop.
  - 사망: MM_Death_Back_01, Front_01~03, Left_01, Right_01(0.93~1.13s).
  - 피격: Rifle/HitReact 폴더에만 있다(MM_HitReact_*, 8개).
  - bEnableRootMotion=true인 시퀀스: MM_Attack_01(17693), 02(17689), 03(17692), MM_ChargedAttack(17722), MM_Dash(16934).
  - Death, HitReact, WallJump는 false(기본값, `AnimSequence.h:320`)다.
- **BP**
  - 공격과 대시 몽타주는 루트 모션으로 캡슐을 움직인다. 재생 중 이동은 애니메이션이 정한다.
  - 거리를 바꾸려면 애님을 수정하거나 Root Motion Source를 써야 한다.
  - 사망 애님은 제자리에서 재생된다.

### D3b. 맨손 피격 시퀀스: PARTIAL
- **주장**: 맨손 캐릭터가 쓸 수 있는 피격 반응 시퀀스가 있다.
- **근거**
  - 피격 시퀀스는 `Rifle/HitReact`에 있는 8개뿐이고, 전부 additive(AAT_LocalSpaceBase)다.
    - RefPose ABPT_AnimFrame: Back_Med_01, Front_Hvy_01, Front_Lgt_02, Front_Med_01, Front_Med_02
    - RefPose ABPT_LocalAnimFrame: Front_Lgt_01, 03, 04
  - additive 몽타주는 일반 슬롯 위에 누적된다(`Eng/Private/Animation/AnimInstanceProxy.cpp:1979-1986, 2086-2094`).
  - 맨손용 비additive 피격이나 다운 시퀀스는 없다.
- **BP**
  - MM_HitReact_*로 DefaultSlot 몽타주를 만들면 이동 포즈 위에 움찔 동작이 얹힌다. 라이플 기준 델타라 팔이 어색할 수 있으니 PIE에서 확인한다.
  - 큰 피격(띄우기, 다운)은 MM_Death_*의 일부 구간을 비additive로 쓴다.
  - 한 트랙에 additive와 비additive 시퀀스를 섞지 않는다.

### D4. LevelPrototyping 메시와 머티리얼: TRUE
- **주장**: LevelPrototyping의 스태틱 메시와 머티리얼을 확인하고, M_PrototypeGrid와 MI_*가 색 파라미터를 노출하는지 확인한다.
- **근거**
  - 메시 기본 머티리얼
    - SM_Cube, SM_Cylinder, SM_Ramp 등: MI_PrototypeGrid_Gray
    - SM_ChamferCube, SM_Plane: MI_DefaultColorway
    - SM_Door: M_FlatCol
    - SM_CircularBand: M_SimpleGlow
    - SM_CircularGlow: M_GradientGlow
  - M_PrototypeGrid 파라미터
    - Vector: SurfaceColor(0.18), GridColor, SubGridColor, TopSurfaceColor, TopGridColor, TopSubGridGridColor, Line Dimensions
    - Scalar: Grid Size 100, Sub Grid Number 5, CircleSize, Roughness
    - Switch: Grid, ObjectAligned
  - M_FlatCol: 'Base Color'(공백 포함), Metallic, Roughness. MI_DefaultColorway의 부모다.
  - M_SimpleGlow: 'Color', 'Custom Prim Switch'. M_GradientGlow: 'Col', 'Blend'.
  - 'Color'나 'Tint'라는 이름의 그리드 파라미터는 없다.
  - BP_WobbleTarget은 존재하지 않는 `/Game/DemoTemplate/_Core/MI_Intro_Colorway`를 참조한다.
- **BP**
  - 바닥과 벽 색은 부모 M_PrototypeGrid에서 SurfaceColor/TopSurfaceColor/GridColor/SubGridColor를 바꾼다.
  - 단색 소품은 M_FlatCol의 'Base Color', 빛나는 것은 M_SimpleGlow의 'Color'를 바꾼다.
  - 파라미터 이름은 대소문자와 공백까지 정확히 쓴다. BP_WobbleTarget은 참조하지 않는다.

### D5. 엔진 템플릿 맵: TRUE
- **주장**: 바닥, 하늘, 디렉셔널 라이트가 있어 시작 레벨로 쓸 수 있는 엔진 템플릿 맵이 있다.
- **근거**
  - `Engine/Content/Maps/Templates`: Template_Default, OpenWorld, TimeOfDay_Default, VR-Basic.
  - `Engine/Config/BaseEngine.ini:2066-2067`: 'Basic'이 Template_Default에 연결돼 있다.
  - Template_Default 구성: DirectionalLight, SkyLight, SkyAtmosphere, VolumetricCloud, ExponentialHeightFog, SM_SkySphere, 바닥 SM_Template_Map_Floor(MI_ProcGrid), PlayerStart_0. **World Partition이 아니다.**
  - OpenWorld와 프로젝트의 Lvl_ThirdPerson, Lvl_Combat, Lvl_Platforming은 모두 World Partition이다(액터별 외부 파일 65~147개).
- **BP**
  - Template_Default를 복제하거나 'Basic' 새 레벨 템플릿으로 시작한다.
  - WP 맵은 MCP 편집과 git diff가 번잡해지므로 피한다.
  - 엔진 맵을 직접 수정하지 않는다.

### D6. 마네킹 머티리얼과 보스 색: TRUE
- **주장**: Manny/Quinn 머티리얼 인스턴스의 파라미터 이름으로, 새 MaterialInstanceConstant를 만들어 보스 색을 바꿀 수 있다.
- **근거**
  - `Content/Characters/Mannequins/Materials/M_Mannequin` 파라미터
    - Vector: 'Paint Tint'(그룹 01 - BaseColor), 'LogoTint', 'Blend Offset'
    - Scalar: MetalPaintRoughness/Metallic, EmissivePower 등
    - Switch: 'Logo?'
  - 인스턴스
    - MI_Manny_01_New(부모 M_Mannequin)
    - MI_Manny_02_New(부모 MI_Manny_01_New, Paint Tint를 상속)
    - MI_Quinn_01, MI_Quinn_02(부모 MI_Quinn_01)
  - 메시 슬롯
    - SKM_Manny_Simple: 0 'M_HeadLegs'=MI_Manny_01_New, 1 'M_Torso'=MI_Manny_02_New
    - SKM_Quinn_Simple: 0=MI_Quinn_01, 1=MI_Quinn_02
  - Paint Tint가 칠해진 영역 중 정확히 어디를 물들이는지는 확인하지 못했다(UNKNOWN).
- **BP**
  - 보스 색은 MI 두 개로 바꾼다(부모 MI_Manny_01_New와 MI_Manny_02_New, 'Paint Tint' 재정의). 메시 머티리얼 0번과 1번에 모두 지정한다.
  - 런타임에 색을 바꾸려면 Create Dynamic Material Instance → Set Vector Parameter Value 'Paint Tint'.
  - 결과는 PIE에서 눈으로 확인한다.

---

## 5. 사양과 일치하는 것(변경 없음)

- BP로 붙인 ASC만으로 이벤트, 태그, GE 적용, 속성 감시가 동작한다(A5, A6, A7, B7). `BP_CombatCharacterBase`에 인터페이스는 필요 없다.
- DataTable 행 이름 `SCAttributeSet.<속성>`과 AttributeMetaData 구조체가 맞다(A4).
- 입력 이벤트로 가드 떼기를 감지하는 방식이 맞다. WaitInputRelease를 쓰지 않는 것도 맞다(B3).
- AM_ChargedAttack `Charge` 섹션이 자기 루프라서 누르고 있는 동안 자세가 유지된다(D1b).
- 몬스터 이동을 NavMesh 없이 직접 입력으로 처리할 수 있다(C3).
- 대상 선정의 Pawn 스피어 오버랩이 맞다(C9).
- 큐 경로 설정이 유효하다(A12).
- 한글 UI 텍스트가 기본 폰트로 표시된다(C7).
- 템플릿 몽타주 3종은 모두 DefaultSlot을 써서 ABP_Manny_Combat에서 재생된다(D2).

---

## 설계에 반영할 점

`docs/01-game-spec.md`를 기준으로, 위 근거 때문에 바꾸거나 구체화해야 하는 곳만 적는다. 괄호 안은 근거 항목이다.

### 1. GA 인스턴싱 정책 (3장, 8장 GA_SCBase)
- `GA_SCBase`의 Class Defaults에서 **Instancing Policy = Instanced Per Actor**로 설정하고 자식 GA가 물려받게 한다.
  - 기본값 InstancedPerExecution에서는 콤보 중 좌클릭마다 `GA_Player_BasicAttack` 인스턴스가 새로 겹쳐 실행된다. 기본 공격의 Activation Blocked Tags에 State.Attacking이 없기 때문이다.
  - Per Actor면 실행 중에는 TryActivateAbility가 false를 돌려주고, 같이 보낸 InputTag 이벤트만 실행 중인 인스턴스가 받는다. 2장 입력 흐름은 이 동작을 전제로 한다. (A3, A9)
- `GA_HitReact`만 **bRetriggerInstancedAbility = true**로 둔다.
  - 이렇게 하지 않으면 경직 중에 다시 맞았을 때 Event.HitReact 트리거가 중복 검사에서 실패해, 경직과 넉백이 갱신되지 않는다. (A3, A6)

### 2. 입력 이벤트 순서 (2장 입력 흐름)
- `AC_CombatComponent.PressInput`은 **InputTag 이벤트를 먼저 보내고, TryActivateAbility를 나중에** 부른다.
  - 활성화와 이벤트 전달이 모두 동기라서, 순서가 반대면 콤보를 시작한 그 클릭이 새 인스턴스의 WaitGameplayEvent에 바로 들어가 "다음 타 입력"으로 잡힌다.
  - 다른 방법으로, GA가 콤보 입력 구간이 열릴 때에야 WaitGameplayEvent를 시작해도 된다. (A6)
- 가드 떼기는 사양대로 이벤트로 감지한다(EventMagnitude 0).
  - 그런데 `DefaultGameplayTags.ini`에 `Event.Input.Released.Guard`가 따로 있다. 사양(같은 InputTag + EventMagnitude)과 방식이 다르므로 하나로 통일한다.
  - 5.8 대안인 ASC Press/Release Input ID도 기록해 둔다. (B3)

### 3. 기본 공격 콤보 구조 (4장 콤보 규칙)
- AM_ComboAttack 섹션은 서로 연결돼 있지 않고(Melee01/02/03 → None), 자동 블렌드아웃은 섹션 끝 0.2초 전에 시작된다.
  - 1~3타는 **PlayMontageAndWait 하나**(StartSection Melee01)로 재생한다.
  - 연결 시점에는 GA 노드 **MontageJumpToSection**(Melee02, Melee03)으로 넘긴다. 이 방식은 인터럽트 이벤트가 나지 않는다. (B2, D1b)
- **연결 시점 상한**을 사양 수치에 적는다. 섹션 시작 기준으로 Melee01과 Melee02는 0.8초 전, Melee03은 1.467초 전이다. 이 시점이 지나면 이미 블렌드아웃이 시작돼 OnBlendOut이 오고 점프가 먹지 않는다. (B2, D1a)
- 3→4타는 몽타주가 바뀐다(AM_ChargedAttack `Attack`). 새 PlayMontageAndWait는 이전 태스크를 즉시(동기로) OnInterrupted로 끝낸다.
  - **ComboStep 가드 패턴**을 사양에 명시한다(B1 레시피).
  - 중간 태스크의 OnInterrupted를 End Ability에 직접 연결하면 4타 몽타주가 어빌리티 없이 재생된다. (B1)
- 새로 만드는 몽타주도 전부 DefaultSlot에 둔다. 상체 슬롯은 AnimBP에 노드가 없다. (D2)

### 4. 타격과 콤보 타이밍의 출처 (4장 "노티파이 또는 WaitDelay" 결정)
- 템플릿 몽타주에는 이미 노티파이가 있다(섹션 기준 시간). 몽타주를 편집할 필요는 없다.
  - 타격(Do Attack Trace): Melee01 +0.467, Melee02 +0.467, Melee03 +0.4, ChargedAttack `Attack` +0.367
  - 콤보(Check Combo): Melee01 +0.533, Melee02 +0.567
- `BP_CombatCharacterBase`가 템플릿 인터페이스 **BPI_Attacker를 구현**하고, 받은 호출을 Send Gameplay Event to Actor(Self)로 넘긴다.
  - 이벤트 태그(예: `Event.Montage.Hit`, `Event.Montage.ComboWindow`)는 현재 태그 파일에 없으므로 추가한다. (D1a)
- Melee03에는 콤보 노티파이가 없다. 3→4타 입력 구간만 GA 변수와 WaitDelay로 둔다. (D1a)
- 히트스탑을 CustomTimeDilation으로 넣으면 애니메이션만 느려지고 WaitDelay는 그대로 흘러 타이밍이 어긋난다. 그래서 타격 시점은 노티파이 기반을 권장한다. (C5)
- BPI_Attacker를 구현하면 다음 호출도 들어온다.
  - 가드 루프(`Charge`)에서 매 루프 'Check Charged Attack'이 불린다. 빈 구현으로 둔다.
  - Q(Melee03), R(Melee02), E(`Attack`)에서도 Do Attack Trace가 온다. 각 GA가 이 이벤트를 쓸지 무시할지 정한다. (D1a)

### 5. 가드 중 이동 (3장 "가드 중 이동 속도 50%", 4장 가드 애니메이션)
- MM_ChargedAttack은 루트 모션이 켜져 있다(RootMotionFromMontagesOnly). 또 ABP_Manny_Combat에는 전신 DefaultSlot 노드 하나뿐이다.
  - 이 몽타주가 재생되는 동안에는 이동이 루트 모션으로 정해져 입력 이동이 반영되지 않을 가능성이 크다.
  - 움직이더라도 하체가 고정된 자세로 미끄러진다.
- **"가드 중 제자리(CanMove=false)"로 바꾸기를 권장한다.** 걸으면서 가드하려면 AnimBP에 상체 슬롯이 필요한데, 이는 템플릿 수정 금지 원칙과 충돌한다. 입력이 막히는지는 PIE에서 확인한다. (D2, D3a)

### 6. 대시 (3장 표, 4장)
- **State.Invulnerable을 Activation Owned Tags에서 뺀다.**
  - ActivationOwnedTags는 어빌리티가 끝날 때까지 유지되므로 무적을 0.35초로 끊을 수 없다.
  - 무적은 새 GE(예: `GE_Invuln_Dash`: Has Duration 0.35초, Grant Tags State.Invulnerable)로 주고, 8장 GE 목록에 추가한다. (A10, B4)
- AM_Dash의 AN_EndDash는 BP_PlatformingCharacter로 캐스트하므로 우리 캐릭터에서는 아무 일도 하지 않는다. 루트 모션은 0.633초에 꺼진다.
  - `GA_Player_Dash`는 WaitDelay 0.633초(또는 OnBlendOut) 뒤 End Ability로 끝낸다. bStopWhenAbilityEnds가 몽타주를 멈춘다.
  - 대시 지속 시간 0.633초를 사양에 적는다. (D1a, D1b)

### 7. 피격 경직 (3장, 5장)
- `GA_HitReact`의 Activation Blocked Tags에 **State.Invulnerable을 추가**한다. 또는 ApplyHit가 무적인 대상에게 Event.HitReact를 보내지 않게 한다.
  - 이벤트로 발동할 때도 차단 태그만 검사한다. 지금 표대로면 대시 중에 맞으면 피해는 없어도 경직과 넉백이 걸린다. (A6)
- **State.HitStun은 한 곳에서만 준다.** `GA_HitReact`의 Activation Owned Tags로 주고, GA 안에서 WaitDelay 0.4초로 시간을 잰다.
  - `GE_HitStun`이 같은 태그를 Grant하면, 대시가 `GA_HitReact`를 취소해도 GE 태그가 남아 스킬과 이동이 계속 막힌다. 그러면 "경직 중 대시 탈출"이 반만 된다.
  - `GE_HitStun`은 빼거나, 태그를 주지 않게 만든다. (A10, B4)
- **피격 몽타주를 에셋 목록에 추가한다.** 맨손 피격 애니메이션은 없고, `Rifle/HitReact`의 MM_HitReact_* 8개(모두 additive)뿐이다.
  - 예: `AM_SC_HitReact`(DefaultSlot, MM_HitReact_Front_Lgt_*)
  - 띄우기(E 700, 보스 600) 같은 큰 피격은 MM_Death_*의 일부 구간으로 비additive 몽타주를 만든다. (D3b)
- 피격 몽타주도 같은 DefaultGroup이라, 재생하면 실행 중인 스킬 몽타주와 가드 몽타주가 멈춘다. 둘 중 하나를 정한다. (B1)
  - HitReact의 Cancel 목록에 Ability.Skill과 Ability.Guard를 넣는다(몽타주 동작과 일치).
  - 스킬 시전 중에 State.SuperArmor를 준다.

### 8. 사망 처리 (5장 사망)
- ASC의 CancelAbilities와 CancelAllAbilities는 BP에 노출되지 않는다.
  - **`GE_Death`**(Instant, 'Cancel Abilities with Tags' 컴포넌트, 태그를 비워 전부 취소)를 8장 GE 목록에 추가하고, `AC_CombatComponent`가 자신에게 적용한다.
- 사망 순서
  1. Has Matching Gameplay Tag(State.Dead)로 이미 붙어 있는지 확인한다.
  2. Add Loose Gameplay Tags(State.Dead).
  3. GE_Death를 적용한다.
- 부활할 때는 Remove Loose Gameplay Tags를 한 번 부른다(카운트 방식).
- SetCanBeCanceled(false)를 쓰는 GA는 사망 때도 끊기지 않으므로 쓰지 않는다. (A7, A8)

### 9. 비용과 쿨타임 수치의 위치 (1장 데이터 주도 원칙, 4장)
- 1장의 "어빌리티 수치는 GA 변수" 원칙에서 **비용과 쿨타임은 제외**한다. 두 값은 GE 에셋에 고정한다.
- `GE_Cost_*`: Instant, **AddBase**, 음수 ScalableFloat(Stamina −25, Mana −20/−30/−25).
  - SetByCaller, Override, Multiply 비용은 사전 검사에 반영되지 않아 SP가 모자라도 발동된다. (A2)
- `GE_Cooldown_*`: Has Duration + 'Grant Tags to Target Actor'. 잎 태그 Cooldown.Dash, Cooldown.Skill.1~3, Cooldown.Enemy.Attack.1~3을 쓴다.
  - 스크립트로 설정했으면 GE를 컴파일하고 저장한다. (B4)
- GE 모디파이어 연산은 5.8 이름으로 적는다(AddBase, MultiplyAdditive, MultiplyCompound, Override).
  - 공격력 ×1.3 버프 두 개(`GE_Buff_Attack`, `GE_Boss_Enrage`)가 겹칠 때 결과는 연산 선택에 따라 달라진다. 정하고 PIE에서 확인한다. (B5)

### 10. HUD 쿨타임 (7장 WBP_SkillSlot)
- Get Active Effects With All Tags는 에셋 태그만 보므로, Grant 태그만 있는 쿨타임 GE를 찾지 못한다.
- `WBP_SkillSlot`은 B6 레시피대로 만든다.
  - OwningTagQuery(CooldownTag) → 'Get Active Gameplay Effects for Query' → GetActiveGameplayEffectRemainingDuration/TotalDuration.
  - 갱신 시작과 종료는 Wait Gameplay Tag Add/Remove To Actor로 한다.
- GA의 GetCooldownTimeRemaining은 HUD에서 쓰지 않는다. (B6, A11)

### 11. ASC 초기화 순서 (8장 AC_CombatComponent, 4장 스탯 표)
- `AC_CombatComponent`의 BeginPlay 순서
  1. InitStats(USCAttributeSet, DT_Attr_*)
  2. Give Ability(Level 1)
  3. `GE_Regen_Player` 적용
  4. Team, SuperArmor 등 Loose 태그 추가
- InitStats가 AttributeSet을 만들어 주므로 비용 검사와 HUD 바인딩보다 먼저 와야 한다.
- 컴포넌트의 BeginPlay가 액터의 BeginPlay보다 먼저 실행되므로, 액터 BeginPlay에서 HP 위젯을 바인딩하면 된다. (A4, B7, C6)
- DataTable은 BaseValue만 읽고 클램프 없이 쓴다. Health와 MaxHealth, Mana와 MaxMana, Stamina와 MaxStamina **행을 모두** 넣는다. Min/Max 열은 무시된다는 점을 사양에 적는다. (A4)

### 12. 필드 복귀 스폰 (6장, 8장 BP_SCGameInstance, BP_FieldGameMode)
- `ReturnToField`는 **Open Level `L_CombatField#GateReturn`**(Absolute=true)으로 충분하다.
  - 엔진 FindPlayerStart가 `#` 뒤 문자열을 PlayerStartTag와 비교한다.
  - GameInstance의 복귀 플래그는 필요 없다. (C4)
- 필드에는 PlayerStart가 두 개라서, `#` 없이 열면 기본 ChoosePlayerStart가 비어 있는 것 중 **무작위**로 골라 GateReturn에서 시작할 수 있다.
  - 시작점(0,0)에 태그 `FieldStart`를 주고, `BP_FieldGameMode`에서 **ChoosePlayerStart를 오버라이드**해 `FieldStart`를 반환한다.
  - FindPlayerStart는 오버라이드하지 않는다. (C4)

### 13. UI 입력 차단 (6장 WBP_DungeonEntry, 7장)
- 입력 이벤트가 `BP_SCPlayerController`에 있으므로 폰의 Disable Input으로는 막히지 않는다.
- 창을 열 때: **Set Input Mode UI Only** + Show Mouse Cursor=true.
- 창을 닫을 때: Remove from Parent → Set Input Mode Game Only → Show Mouse Cursor=false. RemoveFromViewport는 쓰지 않는다. (C8)

### 14. 몬스터 스폰 (4장 AI, 5장 부활, 6장 스파링 잡몹)
- 부활이나 웨이브에서 SpawnActor를 쓴다면, `BP_EnemyBase`의 **Auto Possess AI를 Placed in World or Spawned**로 설정한다.
  - 기본값(PlacedInWorld)에서는 스폰된 몬스터에 컨트롤러가 없어 이동과 AI가 멈춘다.
  - 미리 배치해 둔 휴면 몬스터는 기본값으로도 된다. (C3)

### 15. 넉백, 돌진과 루트 모션 (4장 Q, 넉백/띄우기, 점프)
- LaunchCharacter는 Z가 0이어도 Falling으로 바꾸고, 곧 OnLanded가 온다.
  - `GA_Player_Jump`의 "착지하면 종료"는 자기 Jump 이후의 착지만 받게 만든다.
  - AnimBP의 공중 판정이 깜빡이는지 PIE에서 확인한다. (C2)
- MM_Attack_01~03과 MM_ChargedAttack은 루트 모션이라 재생 중 이동은 애니메이션이 정한다.
  - Q의 "전방 돌진(1800)"을 LaunchCharacter로 주면 Melee03 루트 모션과 겹친다.
  - 다음 중 하나를 정해 사양에 적는다(PIE 확인 필요).
    - 몽타주 전에 이동을 끝낸다.
    - Root Motion Source 태스크를 쓴다.
    - Melee03 자체의 이동만 쓴다. (C2, D3a)

### 16. GameplayCue 위치와 수명 (5장 GC_Hit, 4장 가드, 6장 버프)
- 스피어 오버랩에는 HitResult가 없어서 `GC_Hit`(Burst)가 대상의 발밑(메시 원점)에 생긴다. 둘 중 하나를 한다.
  - ApplyHit에서 'Execute GameplayCue On Actor (Burst)'에 Location(대상 위치 + 높이)을 넘긴다.
  - `GC_Hit`의 SocketName(예: spine_03)을 지정한다.
- EffectContext Origin은 위치로 쓰이지 않는다. (B8)
- 큐 붙이는 방법
  - `GC_Guard_Active`: `GA_Player_Guard`에서 'Add GameplayCue To Owner'(bRemoveOnAbilityEnd=true)로 붙인다.
  - `GC_Buff_Attack`: `GE_Buff_Attack`의 GameplayCues로 붙인다(만료되면 자동 제거).
- 같은 큐 태그를 두 출처에서 동시에 붙이지 않는다. (B9)

### 17. 레벨과 머티리얼 (6장, 8장 Maps, Materials)
- `L_CombatField`와 `L_Dungeon_01`은 `/Engine/Maps/Templates/Template_Default`를 복제해 시작한다. 단일 파일이고 WP가 아니며, 바닥, 조명, 하늘, 안개, PlayerStart가 들어 있다.
  - 템플릿 `Lvl_*`과 OpenWorld는 World Partition이라 피한다.
  - 복제한 PlayerStart_0에 `FieldStart` 태그를 준다(12번). (D5)
- `MI_SC_*`의 부모와 파라미터를 사양에 적는다. (D4)
  - 바닥, 벽: M_PrototypeGrid(SurfaceColor, TopSurfaceColor, GridColor, SubGridColor)
  - 봉인석 등 단색 소품: M_FlatCol('Base Color')
  - 포털, 예고원: M_SimpleGlow('Color')
- **보스 색은 MI 두 개**로 바꾼다. `MI_SC_Boss_01`(부모 MI_Manny_01_New)과 `MI_SC_Boss_02`(부모 MI_Manny_02_New)에서 'Paint Tint'를 재정의한다.
  - 메시 슬롯이 두 개이고, _02가 부모의 틴트를 물려받기 때문이다.
  - 사양에 보스 메시(SKM_Manny_Simple)를 명시한다. (D6)

### 18. 문 (6장 BP_DungeonGate, BP_DungeonDoor)
- Move Component To는 스윕 없이 움직여서 폰을 밀지 않고 통과한다.
  - 문 메시는 Movable로 둔다.
  - 방 트리거는 문보다 충분히 안쪽에 둔다. 그래야 문이 닫힐 때 플레이어가 문 안에 끼지 않는다. (C10)
