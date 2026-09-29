# 게임 루프 자동 흐름 테스트 보고서 (7c 2/2, 에디터 B)

테스트 날짜는 2026-09-29이고, 에디터 B(`C:/Project/SoulCombat_B`, MCP 포트 8001)에서 했다. 키보드 입력 없이 MCP 호출만으로 필드 → 게이트 → 던전 5개 방 → 클리어 → 필드 복귀까지 한 바퀴를 확인했다.

진짜 맵과 `/Game/SoulCombat`의 BP는 **고치지 않았다**. 테스트는 모두 `/Game/_Scratch`의 복제 맵과 도우미 BP로 했다. 끝났을 때 PIE는 꺼져 있고, 더러운(dirty) 에셋은 0개다. 레벨은 원래대로 `L_Dungeon_01`을 열어 두었다.

## 만든 테스트 도구 (`/Game/_Scratch`)

| 에셋 | 내용 |
| --- | --- |
| `BP_TestKiller` (Actor) | 변수 `Interval` 1.0. 흐름은 BeginPlay → `SetTimerbyFunctionName("KillActive", Interval, looping)`이다.<br>`KillActive`는 `GetAllActorsOfClass(BP_EnemyBase_C)`로 적을 모은 뒤, `bActive`이고 `Combat.bIsDead`가 아닌 적마다 다음을 한다.<br>ASC → `MakeOutgoingSpec(GE_Damage, 1, MakeEffectContext)` → `AssignTagSetByCallerMagnitude(Data.Damage, 100000)` → `ApplyGameplayEffectSpecToSelf`.<br>컴파일(warnings_as_errors) 에러·경고 0, 저장했다. |
| `BP_TestGateDriver` (Actor) | 변수(인스턴스 편집): `Delay1` 1.5, `Delay2` 1.0, `Delay3` 1.5, `Delay4` 2.0, `FrontDistance` 250, `Mode` 0. 상태 변수: `Step`, `SeenInteractable`, `Gate`.<br>BeginPlay 흐름:<br>1. Delay1 → 게이트를 찾고 플레이어를 게이트 앞(위치 + 정면 × 250, z +100)으로 옮긴다. Step 1.<br>2. Delay2 → PC.CurrentInteractable을 기록하고 `Gate.Interactable.Interact(플레이어)`를 부른다. Step 2.<br>3. Delay3 → 플레이어를 포털 트리거 안(위치 − 정면 × 40, z +100)으로 옮긴다. Step 3.<br>4. Mode가 1이면 `PC.EntryWidget`의 `OnConfirmed`를, 2면 `OnCancelled`를 직접 방송한다(버튼 클릭 대용, 이번에는 쓰지 않음).<br>컴파일 에러·경고 0, 저장했다. |
| `L_DungeonFlowTest` | 진짜 `L_Dungeon_01`의 복제다. 방의 Enemies·문 참조가 복제 맵 액터로 바뀐 것을 확인했다. `TestKiller`는 (0,-400,50)에 두었다(3번 테스트 동안에만 뺐다가 다시 넣음). |
| `L_FieldFlowTest` | 진짜 `L_CombatField`의 복제다. `TestGateDriver`는 (600,1200,50)에 두었다. |

## 판정표

판정 기준: 통과(기대대로), 부분(기대와 일부 다름), 실패(기대와 다름). PIE 월드 경로는 `/Game/_Scratch/UEDPIE_0_L_DungeonFlowTest.L_DungeonFlowTest:PersistentLevel.<액터>`다.

### 1. 도우미 BP

| # | 확인 | 결과 | 판정 |
| --- | --- | --- | --- |
| 1-1 | BP_TestKiller 생성, 컴파일, 저장 | 노드 14개(KillActive), 에러·경고 0, is_dirty false | 통과 |
| 1-2 | 킬러 동작 | PIE에서 활성 적이 1초 안에 모두 사망(아래 2단계) | 통과 |

### 2. 던전 전체 흐름 (`L_DungeonFlowTest` + TestKiller)

| # | 확인 | 관찰 | 판정 |
| --- | --- | --- | --- |
| 2a-1 | 시작: GameMode | `BP_DungeonGameMode_C_0`, StartTime 0 | 통과 |
| 2a-2 | 시작: Room_Start 클리어 | `bStarted` false, `bCleared` false(3초 뒤에도 그대로). 배너 제목도 기본값 '방 제목' 그대로라 '시련의 회랑' 배너가 뜨지 않았다 | **실패(버그 B1)** |
| 2a-3 | 시작: Door_Start_Exit 열림 | `bIsOpen` true(문의 bStartOpen 덕분, 방 로직 때문이 아님) | 통과 |
| 2a-4 | 시작: 적 15 휴면 | 예: Mob1_Grunt_W1_1 `bActive` false, `bHidden` true. 플레이어 (0,0,92), HP 1000/1000, GE_Regen_Player | 통과 |
| 2b-1 | Room_Mob1 진입 (1300,0,100) | 순간이동으로 RoomTrigger 겹침이 발생해 방이 시작됐다 | 통과 |
| 2b-2 | 웨이브 1 → 2 → 클리어 | 8~13초 뒤 첫 폴링에서 이미 `CurrentWave` 3(MaxWave 2 다음), `AliveCount` 0, `bCleared` true. 적 5개(W1 3 + W2 2) 모두 `bActive` true·`Combat.bIsDead` true, Mob2 적은 휴면 그대로. 웨이브 1이 전멸한 뒤에야 CurrentWave가 오르므로, 3이면 웨이브 1 → 1초 뒤 웨이브 2 → 전멸 → 클리어를 모두 거쳤다는 뜻이다(중간 순간은 킬러가 빨라서 따로 잡지 못함) | 통과 |
| 2b-3 | 문 | Door_Mob1_Entry `bIsOpen` false, Door_Mob1_Exit true, 배너 '클리어' | 통과 |
| 2c-1 | Room_Event 진입 (3700,0,100) | `bStarted`·`bCleared`·`bEventDone` true, `DestroyedCount` 3/`TotalCrystals` 3, 봉인석 3개 모두 사망 | 통과 |
| 2c-2 | 성공 보상 | 플레이어 이펙트에 `GE_Buff_Attack`(남은 59초)이 있고 AttackPower 50 → 65(+30%), HP 1000/1000, SP 100/100. 배너 '성공!' | 통과 |
| 2c-3 | 이벤트 타이머 표시·숨김 | 끝난 뒤 HUD `EventTimer` Collapsed. 떠 있는 순간은 킬러가 1초 안에 끝내서 이 실행에서는 못 잡았고, 3번 실패 테스트에서 표시를 확인했다 | 통과(3번과 합쳐서) |
| 2c-4 | 문 | Door_Event_Entry 닫힘, Door_Event_Exit 열림 | 통과 |
| 2d | Room_Mob2 진입 (5700,0,100) | 웨이브 1(3) → 웨이브 2(3) → `CurrentWave` 3, `bCleared` true, 적 6개 모두 사망, Door_Mob2_Entry 닫힘, Door_Mob2_Exit 열림 | 통과 |
| 2e-1 | Room_Boss 진입 (8100,0,100) | 보스 활성, `CurrentBoss` = Boss_Guardian, 보스 사망, `bCleared` true, Door_Boss_Entry 닫힘 | 통과 |
| 2e-2 | 보스 바 표시·숨김 | 킬러 실행에서는 첫 폴링에 이미 Collapsed였다(사망 뒤 숨김). 킬러 없는 실행(3번 테스트 끝)에서 보스 방에 들어가자 `BossBar` HitTestInvisible(표시)였다 | 통과 |
| 2e-3 | 클리어 창 | 약 2초 뒤 `PC.ClearWidget` = `WBP_DungeonClear_C_0`, 커서 표시(`bShowMouseCursor` true). 따로 확인한 실행에서 글자 'DUNGEON CLEAR' / '클리어 시간 4.3초' / '4초 후 필드로 돌아갑니다' → '1초 후 …'. GameMode `ClearSeconds` 4.33과 같다(전체 실행은 127.4초) | 통과 |
| 2e-4 | 카운트다운 뒤 복귀 | 로그 `Browse: /Game/SoulCombat/Maps/L_CombatField#GateReturn` → PIE 월드가 `UEDPIE_0_L_CombatField`, GameMode `BP_FieldGameMode_C_0`. 플레이어 (146,1506,92) Yaw -90(GateReturn (0,1450) 근처, 몇 초 사이 잡몹에게 밀림). HUD 새로 생성(`WBP_PlayerHUD_C_1`), ClearWidget None, 커서 숨김 | 통과 |
| 2e-5 | 복귀 직후 상태 | 복귀 몇 초 만에 HP 1000 → 575. 스파링 잡몹 2마리가 이미 (172,1474), (251,1480)까지 와서 공격하고 있었다 | 부분(설계 문제 B5) |
| 2-L | 로그 | 킬러 실행 중 `LogSkinnedMeshComp: Warning: GetSocketInfoByName(spine_03): No SkeletalMesh for Component(CharacterMesh0) Actor(BP_SealCrystal_C …)` 3줄(봉인석이 맞은 순간) | 부분(버그 B2) |

### 3. 이벤트 방 실패 (`L_DungeonFlowTest`, 킬러를 뺀 상태)

| # | 확인 | 관찰 | 판정 |
| --- | --- | --- | --- |
| 3-1 | 진입 직후 | `bStarted` true, 입구·출구 닫힘, 봉인석 `bActive` true·`bHidden` false. 배너 'EVENT: 봉인석을 파괴하라', HUD `EventTimer` HitTestInvisible(표시) | 통과 |
| 3-2 | 타이머 내용 | ObjectiveText '봉인석을 파괴하라', TimeText '남은 시간 4.0초'(진입 28초 뒤), ProgressText '봉인석 0 / 3', `bRunning` true | 통과 |
| 3-3 | 30초 초과 뒤 | `bEventDone`·`bCleared` true, `DestroyedCount` 0. 봉인석 3개 모두 `bActive` false·`bHidden` true(`bIsDead` false). 배너 '실패', `EventTimer` Collapsed(`bRunning` false). Door_Event_Exit 열림, 입구는 닫힘. 보상 없음(AttackPower 50, GE_Buff_Attack 없음) | 통과 |
| 3-L | 로그 | 이어서 보스 방에 들어갔을 때 `LogStaticMesh: Warning: Invalid material [MI_SC_Telegraph] used on Nanite static mesh [SM_Cylinder] … [BLEND_Translucent]` 1줄(보스 내려찍기 예고원) | 부분(버그 B3) |

### 4. 필드 → 던전 입장 (`L_FieldFlowTest` + TestGateDriver)

| # | 확인 | 관찰 | 판정 |
| --- | --- | --- | --- |
| 4-1 | 드라이버 진행 | 약 7초 뒤 `Step` 3, `Gate` = BP_DungeonGate_C_0 | 통과 |
| 4-2 | 겹침 → 상호작용 대상 등록 | `SeenInteractable` = `BP_DungeonGate_C_0.Interactable`. Interact 직전 PC.CurrentInteractable이 게이트였다. InteractSphere 겹침 → `SetInteractable`이 동작했다는 뜻이다 | 통과 |
| 4-3 | 게이트 열림 | `bIsOpen` true. DoorL RelativeLocation y -250 → -490, DoorR 0 → 240(각 240 이동). PortalPlane `bHiddenInGame` false, `bVisible` true. PortalTrigger `collisionEnabled` QueryOnly | 통과 |
| 4-4 | 포털 → 입장 창 | `bEntryOpen` true, `PC.EntryWidget` = `WBP_DungeonEntry_C_0`, `bShowMouseCursor` true. SlateInspector 스냅샷에 '시련의 회랑', '다섯 개의 방을 돌파하고 수호자를 쓰러뜨려라.', 'Start → Mob → Event → Mob → Boss', 버튼 '입장'·'취소'가 보였다 | 통과 |
| 4-5 | 입력 모드 UI | 커서 표시는 확인했다. 하지만 로그에 `LogPlayerController: Error: InputMode:UIOnly - Attempting to focus Non-Focusable widget SObjectWidget [Widget.cpp(976)]!`가 창을 열 때마다 1줄씩 남았다 | 부분(버그 B4) |
| 4-6 | '입장' 누르기 | SlateInspector `Click {"ref":"b22"}`는 true를 돌려줬지만 버튼에 포커스만 가고(`button "입장" [focused]`) OnClicked가 불리지 않았다. 이어서 `PressKey {"key":"Enter"}`를 보내자 눌렸다 | 통과(우회) |
| 4-7 | 던전 로드 | PIE 월드 `UEDPIE_0_L_Dungeon_01`, GameMode `BP_DungeonGameMode_C_0`, 플레이어 (0,0,92), EntryWidget None, 커서 숨김, 새 HUD | 통과 |
| 4-8 | 도착 뒤 Room_Start | 진짜 L_Dungeon_01에서도 `bStarted`/`bCleared` false, 시작 배너 없음(B1 재현) | 실패(B1) |
| 4-9 | 창이 떠 있는 동안 | 스파링 잡몹이 게이트까지 쫓아와 계속 때렸다(HP 925 → 550, 17초 사이). 첫 실행에서는 창이 떠 있는 동안 플레이어가 죽어 필드 시작점 (0,0)에서 HP 1000으로 부활했다. 그런데도 `EntryWidget`과 `bEntryOpen` true는 그대로였다 | 실패(설계 문제 B5) |

### 5. 취소 경로 (`L_FieldFlowTest`, 새 PIE)

| # | 확인 | 관찰 | 판정 |
| --- | --- | --- | --- |
| 5-1 | '취소' 누르기 | 새 스냅샷에서 ref `b63`을 찾아 `Click` → `PressKey Enter` | 통과(우회, 4-6과 같은 방식) |
| 5-2 | 창 닫힘 | `PC.EntryWidget` None, `bShowMouseCursor` false | 통과 |
| 5-3 | 게이트 앞으로 밀려남 | 플레이어 (-5,1880,92). 게이트 (0,2200) 앞 300이면 (0,1900)이고, 잡몹에게 조금 밀린 위치다 | 통과 |
| 5-4 | `bEntryOpen` false | false, `bIsOpen` true 유지 | 통과 |
| 5-5 | 그 뒤 | 잡몹이 계속 때려서 HP 175까지 내려갔다가 사망 → (0,0)에서 부활, 잡몹이 다시 쫓아와 HP 900 | 설계 문제 B5 |

## 발견한 버그와 권장 수정 (직접 고치지 않음)

### B1. 스폰 지점이 방 트리거 안이면 Room_Start가 시작되지 않는다 (재현 확정)

- 증상: 플레이어가 처음부터 Room_Start의 RoomTrigger 안에서 스폰된다. `L_DungeonFlowTest`에서도, 필드에서 실제로 입장한 `L_Dungeon_01`에서도 그 뒤 `bStarted`/`bCleared`가 계속 false였다.
- 영향:
  - 시작 배너 '시련의 회랑 / 앞으로 나아가라'가 뜨지 않는다. 배너 TitleText가 기본값 '방 제목' 그대로다.
  - 플레이어 부활 지점(`Combat.SetRespawnTransform`)이 Start 방으로 설정되지 않는다.
  - Door_Start_Exit는 `bStartOpen` true라 진행은 막히지 않는다.
- 원인: `BP_DungeonRoom`의 시작 경로는 `OnComponentBeginOverlap(RoomTrigger)` → `OtherActor == GetPlayerPawn(0)` 하나뿐이다. 스폰 순간의 겹침은 빙의 전에 생겨서 GetPlayerPawn(0)이 None이다. 그 뒤로는 새 BeginOverlap이 생기지 않는다.
- 권장 수정(`/Game/SoulCombat/Dungeon/BP_DungeonRoom`): BeginPlay에 초기 겹침 확인을 추가한다. BP_DungeonRoom EventGraph의 BeginPlay 노드를 쓰거나 새 커스텀 이벤트를 만든다. 자식 BP_Room_*는 BeginPlay를 오버라이드하지 않으므로 그대로 상속된다.
  ```
  (event EventBeginPlay
    (Utilities|FlowControl|Delay :Duration 0.2)
    (bind p (Game|GetPlayerPawn :PlayerIndex 0))
    (Utilities|IsValid p
      (:"Is Valid"
        (if (and (Collision|IsOverlappingActor :self (Variables|Default|GetRoomTrigger) :Other p)
                 (not (Variables|Room|State|GetStarted)))
          (CallFunction|StartRoom)))
      (:"Is Not Valid")))
  ```
  노드 ID는 `find_node_types`로 확인한다. `bStarted`의 카테고리는 `Room|State`이고, bool Get은 `GetStarted`로 쓴다(쿡북 규칙). `IsOverlappingActor`는 PrimitiveComponent 버전이다.
- 레벨만 고치는 대안: L_Dungeon_01의 Room_Start RoomTrigger를 스폰 지점 앞(예: 방 중심 기준 x 100~400)으로 옮겨, 한 걸음 걸어야 시작되게 한다.
- 이 대안은 이번 테스트 범위 밖이라 적용하지 않았다.

### B2. 봉인석이 맞을 때 GC_Hit의 소켓 경고

- 증상: `LogSkinnedMeshComp: Warning: GetSocketInfoByName(spine_03): No SkeletalMesh for Component(CharacterMesh0) Actor(BP_SealCrystal_C …)`가 봉인석이 맞을 때마다 뜬다.
- 원인: `GC_Hit`(그리고 `GC_Guard_Block`)의 `defaultPlacementInfo.socketName`이 `spine_03`이다(`OT get_properties` 확인). BP_SealCrystal은 스켈레탈 메시가 없는 Character라서 이 소켓을 찾지 못한다. 동작은 컴포넌트 위치로 대체되므로 경고만 남는다.
- 권장 수정: 둘 중 하나.
  - (a) `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/GAS/Cues/GC_Hit.GC_Hit"},"values":"{\"defaultPlacementInfo\":{\"socketName\":\"None\"}}"}`. GC_Guard_Block도 필요하면 똑같이 한다. 효과는 대상 액터 위치에 뜬다.
  - (b) 소켓을 유지한다면, 봉인석처럼 메시가 없는 대상은 경고를 감수한다.

  (a)를 권장한다. 캐릭터에서 가슴 높이가 필요하면 GC 쪽에서 위치 오프셋을 준다.

### B3. 보스 예고원 머티리얼이 Nanite 메시에 맞지 않는다

- 증상: `LogStaticMesh: Warning: Invalid material [MI_SC_Telegraph] used on Nanite static mesh [SM_Cylinder]. Only opaque or masked blend modes are currently supported, [BLEND_Translucent] …`. 반투명 예고원이 의도대로 그려지지 않을 수 있다(Nanite는 반투명을 지원하지 않는다).
- 권장 수정: 템플릿 메시 `SM_Cylinder`는 고치지 않는다. 대신 BP_TelegraphCircle의 Disc 컴포넌트에서 Nanite를 끈다.
  `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/Combat/BP_TelegraphCircle.BP_TelegraphCircle_C:Disc_GEN_VARIABLE"},"values":"{\"bDisallowNanite\":true}"}`
  지금 값은 `bDisallowNanite` false이고, 프로퍼티 이름은 `list_properties`로 확인했다. 그 뒤 컴파일과 저장을 한다.

### B4. 입장 창을 열 때 입력 모드 포커스 에러

- 증상: `LogPlayerController: Error: InputMode:UIOnly - Attempting to focus Non-Focusable widget SObjectWidget [Widget.cpp(976)]!`가 입장 창을 열 때마다 뜬다. 키보드 포커스가 창으로 가지 않는다(Enter는 버튼에 포커스가 간 뒤에만 먹었다).
- 원인: `BP_SCPlayerController.OpenDungeonEntry`가 `SetInputModeUIOnly(InWidgetToFocus = 입장 위젯)`을 부르는데, `WBP_DungeonEntry` CDO의 `bIsFocusable`이 false다(`OT get_properties` 확인).
- 권장 수정: `OT set_properties {"instance":{"refPath":"/Game/SoulCombat/UI/WBP_DungeonEntry.WBP_DungeonEntry"},"values":"{\"bIsFocusable\":true}"}` → UMG CompileWidgetBlueprint → 저장.
  - 또는 InWidgetToFocus에 `EnterButton`을 넘긴다. 버튼은 기본적으로 포커스를 받을 수 있다.
  - 클리어 창(`OpenDungeonClear`)에서는 같은 에러가 로그에 없었다.

### B5. 입장 창이 떠 있어도, 필드로 복귀한 직후에도 스파링 잡몹이 계속 공격한다 (설계 문제)

- 증상:
  - 스파링 잡몹 2마리의 `AggroRange`가 2500이라 필드 시작점 (0,0), 게이트 (0,2200), 복귀점 (0,1450)이 모두 추적 범위 안이다.
  - 입장 창이 떠 있는 동안(UIOnly, 게임은 계속 진행)에도 플레이어를 때린다. 창을 연 채 죽어서 (0,0)에서 부활한 사례가 있었고, 그때도 창과 `bEntryOpen`은 남아 있었다.
  - 던전에서 복귀한 직후에도 바로 맞는다(몇 초 만에 HP 1000 → 575).
- 권장 수정: 둘 중 하나 또는 둘 다.
  - (a) L_CombatField의 SparringGrunt_1/2 인스턴스 `AggroRange`를 줄인다(예: 800. 스파링 구역 (-1200,900) 근처에 머문다). 인스턴스 편집 가능 변수이므로 `OT set_properties`로 레벨 액터에 넣는다.
  - (b) `OpenDungeonEntry`에서 `SetGamePaused(true)`를 걸고, `HandleEntryCancelled`에서 해제한다. UMG는 일시정지 중에도 동작한다. 또는 창이 떠 있는 동안 플레이어 ASC에 `State.Invulnerable` 루스 태그를 준다.

## 도구 쪽 메모 (자세한 레시피는 `ui-cookbook.md` '7c 흐름 테스트' 절)

- UMG 버튼은 SlateInspector `Click`만으로는 눌리지 않았다(포커스만 감). `PressKey Enter`로 눌렀다.
- 백그라운드 PIE(3 fps)라 한 번 폴링하는 데 속성 20여 개 기준 5~10초가 걸린다. 킬러가 1초 간격이라 웨이브 전환, 보스 바 표시 같은 중간 순간은 대부분 지나간 뒤에 읽혔다. 최종 상태와 카운터로 판정했다.
- 레벨 이동 뒤 PIE 경로가 `/Game/SoulCombat/Maps/UEDPIE_0_L_CombatField.L_CombatField:PersistentLevel...`로 바뀐다. 옛 경로는 `is not valid Object for property 'instance'` 에러를 낸다.
