# 03. MCP 작업 계획 (PC의 Claude Code 세션용)

이 문서는 PC에서 도는 Claude Code 세션이 Unreal MCP로 ActionDemo를 만드는 순서다. 사양은 `02-demo-spec.md`, 규칙은 저장소 루트의 `CLAUDE.md`를 따른다.

각 단계가 끝날 때마다 `04-mcp-test-log.md`의 해당 행을 채운다. **목표는 데모 완성보다 "MCP로 된 것과 안 된 것"을 정확히 기록하는 것이다.**

툴 이름은 5.8.0 에디터를 조사한 공개 카탈로그 기준의 예상값이다. 실제 이름과 인자는 `list_toolsets`와 `describe_toolset`으로 먼저 확인한다. 핫픽스마다 바뀔 수 있다.

## 결과 판정 기준

| 판정 | 뜻 |
| --- | --- |
| 성공 | 전용 MCP 툴만으로 끝났다 |
| Python | 전용 툴이 없거나 실패해서 ProgrammaticToolset의 Python 실행으로 해결했다 |
| 부분 | 결과물은 나왔지만 사람이 에디터에서 고쳐야 했다 |
| 실패 | MCP로는 못 했고 사람이 직접 만들었다 |

## 단계 0. 연결과 환경 확인

- `list_toolsets`로 툴셋 목록과 개수를 기록한다. BlueprintTools, GameplayTagsToolset, GASToolsets, DataTableTools, UMGToolSet, EditorAppToolset, AutomationTestToolset, ProgrammaticToolset이 있는지 본다.
- `describe_toolset`으로 BlueprintTools를 한 번 읽고, 그래프 DSL(`get_graph_dsl_docs`) 문법을 확인한다.
- 에디터 언어가 영어인지 확인한다. 아니면 사용자에게 `OpenEditor_EN.bat`으로 다시 열어 달라고 한다.
- `DemoAttributeSet` 클래스가 로드됐는지 확인한다(속성 피커나 클래스 검색으로).

## 단계 1. 템플릿 조사 (읽기 전용)

에셋을 검색하고 결과를 `docs/demo/assets.md`에 경로 목록으로 남긴다.

1. 플레이어 BP: `BP_ThirdPersonCharacter`의 경로, 메시, AnimBP, 입력 이벤트 구성.
2. Combat 변형: 전투 캐릭터 BP, 콤보 몽타주, 차지 공격 몽타주, 섹션 이름 목록, 애님 노티파이 종류와 시간.
3. Platforming 변형: 대시 몽타주.
4. 몽타주를 재생하는 AnimBP에 DefaultSlot이 있는지. 없으면 Combat 변형이 쓰는 AnimBP를 쓴다.
5. Combat 변형의 공격 판정 방식. BP 인터페이스로 캐릭터를 호출하는 노티파이라면, 몽타주를 고치지 않고 BP_DemoPlayer가 그 인터페이스를 구현하는 쪽으로 단계 5를 바꾼다.
6. 쓸 만한 Niagara 시스템(타격, 먼지, 오라). 없으면 단계 4에서 만든다.
7. 템플릿 입력 에셋(IA_Move, IA_Look, IA_Jump, IMC_Default)과 플레이어 컨트롤러 BP.

## 단계 2. 게임플레이 태그

`02-demo-spec.md`의 태그 표를 GameplayTagsToolset으로 전부 추가한다. 추가 후 `ListTags`로 다시 읽어 철자를 검증한다. 특히 `State.Invulnerable`, `State.Dead`, `Data.Damage`.

## 단계 3. 스탯 데이터

- DataTableTools로 `DT_Attr_Player`, `DT_Attr_Dummy`를 만든다. 행 구조체는 `AttributeMetaData`.
- 행 이름은 `DemoAttributeSet.MaxHealth`, `DemoAttributeSet.Health`, `DemoAttributeSet.MaxMana`, `DemoAttributeSet.Mana`, `DemoAttributeSet.AttackPower`. BaseValue는 사양의 수치.

## 단계 4. 게임플레이 이펙트와 큐

GE는 `GameplayEffect`를 부모로 BP를 만들고 CDO 속성을 설정한다. 5.x에서는 부여 태그가 GE 컴포넌트(Target Tags Gameplay Effect Component)로 들어간다. **이 인스턴스드 서브오브젝트 배열을 MCP로 편집할 수 있는지가 핵심 확인 항목이다.**

| 에셋 | 설정 |
| --- | --- |
| GE_Damage | Instant. Modifier: DemoAttributeSet.IncomingDamage, Add, SetByCaller 태그 Data.Damage. Gameplay Cues: GameplayCue.Hit |
| GE_Cost_Skill1/2/3 | Instant. Modifier: Mana, Add, -20 / -30 / -40 |
| GE_Cooldown_Dodge, Skill1/2/3 | Has Duration 0.8 / 4 / 6 / 15. Target Tags 컴포넌트로 Cooldown.* 부여 |
| GE_DodgeInvuln | Has Duration 0.4. State.Invulnerable 부여 |
| GE_Awaken | Has Duration 8. AttackPower Multiply 1.5. State.Awakened 부여. 큐 GameplayCue.Awaken |
| GE_ManaRegen | Infinite, Period 1. Mana Add 5 |
| GE_RestoreFull | Instant. Health Override = MaxHealth(속성 기반), Mana Override = MaxMana(속성 기반) |

큐:

- GC_Hit, GC_Slam: 부모 `GameplayCueNotify_Burst`. Gameplay Cue Tag 지정, Burst Effects에 Niagara(단계 1에서 찾은 것) 지정. 이펙트가 없으면 NiagaraToolsets로 간단한 스프라이트 폭발을 만들어 본다.
- GC_Awaken: 부모 `GameplayCueNotify_Looping`. 캐릭터에 붙는 루프 Niagara.

## 단계 5. 애님 노티파이와 몽타주

1. `AN_DemoGameplayEvent`: 부모 `AnimNotify` BP. 변수 `EventTag`(GameplayTag, 인스턴스 편집 가능). `Received_Notify` 오버라이드: MeshComp의 Owner에게 `Send Gameplay Event to Actor`(EventTag, Payload.Instigator = Owner) 후 true 반환. 함수 오버라이드 생성이 되는지 확인 항목이다.
2. 템플릿의 콤보, 차지 공격, 대시 몽타주를 `/Game/Demo/Anims`에 `AM_Demo_Combo`, `AM_Demo_Slam`, `AM_Demo_Dodge`로 복제한다.
3. 복제본에서 템플릿의 공격 판정 노티파이와 같은 시간에 `AN_DemoGameplayEvent(Event.Hit)`, 콤보 체크 노티파이와 같은 시간에 `AN_DemoGameplayEvent(Event.Montage.ComboCheck)`를 추가한다. 전용 툴이 없으면 Python(`unreal.AnimationLibrary`)으로 시도하고 판정을 Python으로 기록한다.

단계 1의 5번에서 BP 인터페이스 방식이 확인됐다면 2, 3번 대신 BP_DemoPlayer에서 그 인터페이스 함수를 구현해 같은 게임플레이 이벤트를 보내게 한다.

## 단계 6. 어빌리티

모든 GA 공통 기본값: Instancing Policy = Instanced Per Actor, Activation Blocked Tags에 State.Dead.

**GA_DemoBase** (부모 GameplayAbility). 변수 `DamageEffect` = GE_Damage. 함수:

- `GetAttackPower()`: Avatar의 `Get Float Attribute(DemoAttributeSet.AttackPower)`.
- `GetTargetsInRadius(Radius, ForwardOffset)`: Avatar 위치 + 전방 × ForwardOffset 중심 Sphere Overlap Actors(Pawn, Character, Avatar 제외). ASC가 있고 State.Dead가 없는 액터만 반환.
- `ApplyDamageTo(Target, Coefficient)`: `Make Outgoing Gameplay Effect Spec(DamageEffect)` → `Assign Tag Set By Caller Magnitude(Data.Damage, GetAttackPower × Coefficient)` → `Apply Gameplay Effect Spec to Target(Ability Target Data from Actor(Target))`.
- `LaunchTarget(Target, Away, Up)`: Character로 캐스트 후 `Launch Character((Target - Avatar)의 수평 방향 × Away + (0,0,Up), XY 덮어쓰기, Z 덮어쓰기)`.
- `HitTargets(Radius, ForwardOffset, Coefficient, Away, Up)`: 위 두 함수를 대상마다 호출.

**GA_Attack** (InputTag.Attack). Asset Tags: Ability.Attack. Blocked: State.Casting, State.Dead.

```text
ActivateAbility
  CommitAbility
  ComboIndex = 0, LastInputTime = -100
  PlayMontageAndWait(AM_Demo_Combo, StartSection = Sections[0])
    OnCompleted / OnBlendOut / OnInterrupted / OnCancelled -> EndAbility
  WaitGameplayEvent(InputTag.Attack, 반복) -> LastInputTime = GameTime
  WaitGameplayEvent(Event.Montage.ComboCheck, 반복)
    if GameTime - LastInputTime <= 0.45 and ComboIndex + 1 < Sections.Length:
      ComboIndex += 1, LastInputTime = -100
      MontageJumpToSection(Sections[ComboIndex])
  WaitGameplayEvent(Event.Hit, 반복)
    HitTargets(150, 100, Coefficients[ComboIndex], 250, 마지막 타면 400 아니면 0)
```

**GA_Dodge** (InputTag.Dodge). Asset Tags: Ability.Dodge. Cancel Abilities with Tag: Ability.Attack, Ability.Skill. Cooldown: GE_Cooldown_Dodge.

```text
ActivateAbility
  CommitAbility (실패하면 EndAbility)
  ApplyGameplayEffectToOwner(GE_DodgeInvuln)
  방향 = 마지막 이동 입력의 수평 방향, 없으면 전방
  SetActorRotation(방향), LaunchCharacter(방향 × 1500, true, false)
  PlayMontageAndWait(AM_Demo_Dodge) 끝나면 EndAbility (몽타주가 없으면 Delay 0.4)
```

**GA_Skill_DashStrike** (InputTag.Skill1). Asset Tags: Ability.Skill.DashStrike. Owned: State.Casting. Cancel: Ability.Attack. Cost GE_Cost_Skill1, Cooldown GE_Cooldown_Skill1.

```text
CommitAbility (실패하면 EndAbility)
LaunchCharacter(전방 × 1800)
PlayMontageAndWait(AM_Demo_Combo, 마지막 섹션) 끝나면 EndAbility
WaitGameplayEvent(Event.Hit) -> HitTargets(220, 150, 2.5, 700, 150)
```

**GA_Skill_GroundSlam** (InputTag.Skill2). Asset Tags: Ability.Skill.GroundSlam. Owned: State.Casting. Cancel: Ability.Attack. Cost/Cooldown Skill2.

```text
CommitAbility
PlayMontageAndWait(AM_Demo_Slam, 공격 섹션) 끝나면 EndAbility
WaitGameplayEvent(Event.Hit) -> HitTargets(400, 50, 2.0, 150, 800), ExecuteGameplayCue(GameplayCue.Slam)
```

**GA_Skill_Awaken** (InputTag.Skill3). Asset Tags: Ability.Skill.Awaken. Blocked: State.Awakened. Cost/Cooldown Skill3.

```text
CommitAbility
ApplyGameplayEffectToOwner(GE_Awaken)
EndAbility
```

그래프는 되도록 BlueprintTools의 DSL(`write_graph_dsl`)로 한 번에 쓰고, `compile_blueprint`로 에러를 확인한다. DSL이 bool 리터럴을 빠뜨리거나 이전 시도의 노드를 고아로 남긴다는 보고가 있으니, 쓰고 나서 `read_graph_dsl`로 다시 읽어 비교한다.

## 단계 7. 캐릭터와 입력

**AC_DemoAbilitySystem** (부모 ActorComponent). 변수: AttributeTable(DataTable), StartupAbilities(GameplayAbility 클래스 배열), StartupEffects(GameplayEffect 클래스 배열), RespawnDelay(3.0), bIsDead. 이벤트 디스패처: OnDied, OnRespawned, OnHealthChanged(New, Old).

```text
BeginPlay
  ASC = Owner.GetComponentByClass(AbilitySystemComponent)
  ASC.InitStats(DemoAttributeSet, AttributeTable)
  StartupAbilities 각각 ASC.GiveAbility(Class, 1)
  StartupEffects 각각 ASC.ApplyGameplayEffectToSelf(Class, 1, ASC.MakeEffectContext)
  WaitForAttributeChanged(Owner, DemoAttributeSet.Health) -> OnHealthChanged 방송, New <= 0 이고 살아 있으면 Die

Die: bIsDead = true, AddLooseGameplayTags(Owner, State.Dead), 이동 비활성화, OnDied 방송, Delay RespawnDelay -> Respawn
Respawn: RemoveLooseGameplayTags(State.Dead), GE_RestoreFull 적용, 걷기 모드 복구, bIsDead = false, OnRespawned 방송
PressAbility(InputTag, AbilityClass): SendGameplayEventToActor(Owner, InputTag), ASC.TryActivateAbilityByClass(AbilityClass)
```

**입력 에셋:** IA_Demo_Attack, IA_Demo_Dodge, IA_Demo_Skill1/2/3(Boolean)과 IMC_Demo(좌클릭, Left Shift, Q, E, R). IMC 매핑 배열은 ObjectTools로 안 된다는 보고가 있다. 안 되면 Python `map_key`로 한다.

**BP_DemoPlayer** (부모: 템플릿 BP_ThirdPersonCharacter).

- 컴포넌트 추가: AbilitySystemComponent, AC_DemoAbilitySystem(AttributeTable = DT_Attr_Player, StartupAbilities = GA 5종, StartupEffects = GE_ManaRegen).
- 메시 AnimBP가 몽타주 슬롯이 없으면 단계 1에서 찾은 AnimBP로 바꾼다.
- BeginPlay: 로컬 플레이어의 Enhanced Input 서브시스템에 IMC_Demo를 우선순위 1로 추가. WBP_DemoHUD를 만들어 뷰포트에 추가.
- 입력 이벤트: IA_Demo_* Started → `AC.PressAbility(InputTag.*, GA_*)`.

**입력 이벤트 노드는 별도 확인 항목이다.** MCP로 만든 Enhanced Input 이벤트 노드는 바인딩이 생기지 않아 조용히 안 불린다는 보고가 있다. 순서는 이렇다.

1. MCP로 만들고 `compile_blueprint`로 전체 컴파일한다.
2. 단계 10에서 PIE로 실제로 불리는지 확인한다.
3. 안 불리면 사용자에게 에디터에서 노드 5개를 직접 만드는 방법을 알려 주고, 판정을 "실패"로 기록한다.

**BP_TrainingDummy** (부모 Character).

- 메시: 템플릿 마네킹과 기본 AnimBP. 캡슐 크기 템플릿과 동일.
- 컴포넌트: AbilitySystemComponent, AC_DemoAbilitySystem(AttributeTable = DT_Attr_Dummy), WidgetComponent(WBP_DummyHealth, Screen 공간, 머리 위 120cm).
- OnHealthChanged → HP 바 갱신. OnDied → 메시 래그돌(Set Simulate Physics). OnRespawned → 메시를 캡슐에 다시 붙이고 원래 상대 위치로.

## 단계 8. UI

- **WBP_DemoHUD:** HP, MP 프로그레스 바와 숫자. Shift, Q, E, R 슬롯 4개. 틱마다 Owning Pawn의 속성을 읽고, `Cooldown.*` 태그가 있으면 슬롯을 어둡게.
- **WBP_DummyHealth:** HP 프로그레스 바 하나. 더미가 Percent를 넣어 준다.

## 단계 9. 게임 모드와 맵

- BP_DemoGameMode: Default Pawn = BP_DemoPlayer, Player Controller = 템플릿 플레이어 컨트롤러 BP.
- L_DemoArena: 바닥, 방향광, 스카이, PlayerStart, BP_TrainingDummy 3개((800,0), (800,400), (1200,-300)). World Settings의 GameMode Override = BP_DemoGameMode.
- ConfigSettingsToolset으로 Editor Startup Map, Game Default Map을 L_DemoArena로 설정해 본다.

## 단계 10. 검증

1. 모든 BP를 컴파일하고 에러, 경고를 기록한다.
2. `StartPIE` → 3초 대기 → `CaptureViewport`로 스크린샷(`docs/demo/screenshots/`에 저장).
3. GASToolsets 인스펙터로 플레이어의 부여된 어빌리티 5개, 속성값(500/100/20), 활성 이펙트(GE_ManaRegen)를 확인한다.
4. 키 입력 없이 어빌리티를 검증한다. Python으로 PIE 월드의 플레이어 ASC를 찾아 `try_activate_ability_by_class(GA_Skill_GroundSlam)`를 부르고, 더미 HP 감소와 Cooldown.Skill2 태그를 인스펙터로 확인한다.
5. `GetLogEntries`로 PIE 중 에러 로그를 수집한다.
6. `StopPIE`.
7. 사용자에게 직접 플레이를 부탁하고 `02-demo-spec.md`의 완료 기준 6개를 하나씩 확인받는다.

## 단계 11. 정리

- `04-mcp-test-log.md` 맨 위 요약표를 채운다.
- `ActionDemo/Content/Demo`, `ActionDemo/Config`, `docs/`를 커밋하고 푸시한다. 템플릿 원본 콘텐츠는 `.gitignore`로 제외돼 있다.
