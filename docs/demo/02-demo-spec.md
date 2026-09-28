# 02. ActionDemo 사양

UE 5.8의 Unreal MCP로 **Claude가 블루프린트를 어디까지 직접 만들 수 있는지** 확인하기 위한 작은 액션 데모다. 게임 자체보다 "무엇이 MCP만으로 됐고 무엇이 사람 손을 탔는지" 기록하는 것이 목적이다.

## 원칙

- **C++는 `UDemoAttributeSet` 하나뿐이다.** GAS의 AttributeSet은 5.8에서도 C++로만 만들 수 있기 때문이다. 나머지는 전부 BP로, MCP를 통해 만든다.
- **에셋은 템플릿 것을 재사용한다.** 캐릭터와 애니메이션은 Third Person 템플릿의 Combat, Platforming 변형에서 가져온다. 템플릿 원본은 건드리지 않고 `/Game/Demo`로 복제해서 쓴다.
- **추가 다운로드는 필요할 때만 한다.** Fab 무료 에셋(Niagara 팩 등)은 로그인이 필요해서 MCP가 받을 수 없다. 필요하면 사람이 Fab 창에서 추가한다.

## 조작

| 입력 | 동작 | 어빌리티 |
| --- | --- | --- |
| WASD, 마우스 | 이동, 카메라 | 템플릿 그대로 |
| Space | 점프 | 템플릿 그대로 |
| 좌클릭 | 평타 콤보 (최대 3~4타) | GA_Attack |
| Left Shift | 회피 대시 (무적 0.4초) | GA_Dodge |
| Q | 돌진 베기 | GA_Skill_DashStrike |
| E | 대지 강타 (범위 + 띄우기) | GA_Skill_GroundSlam |
| R | 각성 (8초 공격력 1.5배) | GA_Skill_Awaken |

## 수치

| 항목 | 플레이어 | 훈련용 더미 |
| --- | --- | --- |
| MaxHealth | 500 | 1000 |
| MaxMana | 100 | 0 |
| AttackPower | 20 | 0 |
| 마나 회복 | 초당 5 | 없음 |
| 사망 후 | 3초 뒤 부활 | 3초 뒤 부활 |

| 어빌리티 | 마나 | 쿨타임 | 데미지 (공격력 배수) | 범위 | 넉백 / 띄우기 (cm/s) |
| --- | --- | --- | --- | --- | --- |
| 평타 1~3타 | 0 | 없음 | 1.0 / 1.1 / 1.3, 마지막 타 1.8 | 반경 150, 전방 100 | 250 / 마지막 타만 400 |
| 회피 | 0 | 0.8초 | 없음 | 없음 | 본인 대시 1500 |
| 돌진 베기 | 20 | 4초 | 2.5 | 반경 220, 전방 150 | 700 / 150 |
| 대지 강타 | 30 | 6초 | 2.0 | 반경 400, 전방 50 | 150 / 800 |
| 각성 | 40 | 15초 | 없음 (8초 동안 공격력 ×1.5) | 없음 | 없음 |

## 캔슬 규칙 (소울워커식)

- 스킬은 평타를 캔슬한다. 스킬 어빌리티의 Cancel Abilities with Tag에 `Ability.Attack`.
- 회피는 평타와 스킬을 캔슬한다. 회피의 Cancel Abilities with Tag에 `Ability.Attack`, `Ability.Skill`.
- 스킬 사용 중에는 평타가 막힌다. 스킬이 `State.Casting`을 부여하고 평타가 그 태그에 막힌다.
- 죽으면 모든 어빌리티가 막힌다. 모든 어빌리티의 Activation Blocked Tags에 `State.Dead`.

## 게임플레이 태그

| 분류 | 태그 |
| --- | --- |
| 입력 | InputTag.Attack, InputTag.Dodge, InputTag.Skill1, InputTag.Skill2, InputTag.Skill3 |
| 어빌리티 | Ability.Attack, Ability.Dodge, Ability.Skill.DashStrike, Ability.Skill.GroundSlam, Ability.Skill.Awaken |
| 쿨타임 | Cooldown.Dodge, Cooldown.Skill1, Cooldown.Skill2, Cooldown.Skill3 |
| 상태 | State.Dead, State.Invulnerable, State.Casting, State.Awakened |
| 이벤트 | Event.Hit, Event.Montage.ComboCheck |
| 데이터 | Data.Damage |
| 큐 | GameplayCue.Hit, GameplayCue.Slam, GameplayCue.Awaken |

`State.Invulnerable`, `State.Dead`는 C++ AttributeSet이 이름으로 찾는다. 철자가 틀리면 무적과 사망 처리가 안 된다.

## 에셋 목록 (`/Game/Demo`)

| 폴더 | 에셋 | 설명 |
| --- | --- | --- |
| Data | DT_Attr_Player, DT_Attr_Dummy | 행 구조체 AttributeMetaData. 행 이름은 `DemoAttributeSet.Health` 형식 |
| Effects | GE_Damage | Instant. IncomingDamage에 SetByCaller(Data.Damage) 더하기. 큐 GameplayCue.Hit |
| Effects | GE_Cost_Skill1/2/3 | Instant. Mana -20 / -30 / -40 |
| Effects | GE_Cooldown_Dodge, GE_Cooldown_Skill1/2/3 | Has Duration 0.8 / 4 / 6 / 15초. Cooldown.* 태그 부여 |
| Effects | GE_DodgeInvuln | 0.4초 동안 State.Invulnerable 부여 |
| Effects | GE_Awaken | 8초. AttackPower 곱하기 1.5. State.Awakened 부여. 큐 GameplayCue.Awaken |
| Effects | GE_ManaRegen | Infinite, 주기 1초. Mana +5 |
| Effects | GE_RestoreFull | Instant. Health를 MaxHealth로, Mana를 MaxMana로 덮어쓰기 (속성 기반 크기) |
| Cues | GC_Hit, GC_Slam | GameplayCueNotify_Burst. 타격 위치에 이펙트 |
| Cues | GC_Awaken | GameplayCueNotify_Looping. 몸에 붙는 오라 |
| Anims | AN_DemoGameplayEvent | BP AnimNotify. EventTag 변수를 소유자에게 게임플레이 이벤트로 보낸다 |
| Anims | AM_Demo_Combo, AM_Demo_Slam, AM_Demo_Dodge | 템플릿 몽타주 복제본에 AN_DemoGameplayEvent를 추가한 것 |
| Abilities | GA_DemoBase | 모든 GA의 부모. 데미지, 범위 탐색, 넉백 함수 |
| Abilities | GA_Attack, GA_Dodge, GA_Skill_DashStrike, GA_Skill_GroundSlam, GA_Skill_Awaken | 실제 어빌리티 |
| Core | AC_DemoAbilitySystem | BP 액터 컴포넌트. 스탯 초기화, 어빌리티 부여, 사망과 부활 |
| Core | BP_DemoGameMode | 기본 폰 BP_DemoPlayer |
| Characters | BP_DemoPlayer | 템플릿 BP_ThirdPersonCharacter의 자식 |
| Characters | BP_TrainingDummy | Character 자식. 머리 위 HP 바 |
| Input | IA_Demo_Attack, IA_Demo_Dodge, IA_Demo_Skill1/2/3, IMC_Demo | 좌클릭, Left Shift, Q, E, R |
| UI | WBP_DemoHUD, WBP_DummyHealth | HP, MP 바와 스킬 쿨타임 슬롯 / 더미 HP 바 |
| Maps | L_DemoArena | 바닥, 조명, 플레이어 시작점, 더미 3개 |

## 완료 기준

1. PIE에서 좌클릭 연타로 콤보가 이어지고, 더미의 HP 바가 줄어든다.
2. Q, E, R이 마나를 쓰고, 쿨타임 동안 HUD 슬롯이 어두워진다.
3. E를 맞은 더미가 공중에 뜬다.
4. 회피 중에는 데미지를 받지 않는다(더미가 공격하지 않으므로 콘솔로 확인).
5. 더미가 죽으면 3초 뒤 살아난다.
6. `docs/demo/04-mcp-test-log.md`에 모든 단계의 결과가 적혀 있다.
