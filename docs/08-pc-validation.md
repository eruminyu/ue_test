# 08. 현재 PC 준비와 재검증

확인일은 2026-09-30이다. PC 작업 재개 준비, 전체 점검, 개선 방향 검토를 기록한다. 게임 로직·에셋·프로젝트 설정은 변경하지 않았다. 학습 목적과 검증 결과를 문서에 반영했다.

## 1. 확인 범위와 환경

| 항목 | 확인 결과 |
| --- | --- |
| 체크아웃 | `D:\Project\UE\AstraTest\ue_test` |
| 검증 기준 | `main`, `cc31c5c8d5b2ba96536218a1d8d8c243aa338537`. fetch 후 `origin/main`과 일치, 시작 시 작업 트리 깨끗함 |
| Git 확인 | 전체 브랜치·병합 그래프와 SoulCombat 제작 이후 커밋 확인. 이전 ActionDemo 기록과 현재 SoulCombat 구현 구분 |
| LFS | 이 체크아웃에서 초기화, `git lfs fsck` 통과 |
| 엔진 | `D:\Program Files\Epic Games\UE_5.8`, 실제 UE 5.8.3, CL 58210709. 이전 제작·QA는 UE 5.8.2 |
| 컴파일러 | Visual Studio Community 2026, MSVC 14.51.36257, Windows SDK 10.0.26100.0 |
| 프로젝트 | `SoulCombat/SoulCombat.uproject`, ThirdPerson 및 변형 템플릿 콘텐츠 복원 |
| C++ | `SoulCombatEditor Win64 Development` 빌드 성공. GAS용 클래스 2개: `SCAttributeSet`, `SCAbilitySet` |
| 에셋 | `/Game/SoulCombat` 104개, BP 72개 |
| BP 컴파일 | 부모 우선 순차 `compile_blueprint(warnings_as_errors=true)`, 실패 0, 점검 전후 dirty 0 |
| 의존성 | 104개 에셋의 직접 의존성에서 고유 경로 206개. `/Script` 모듈 경로를 제외한 에셋 존재 확인에서 누락 0. `_Scratch` 의존 0 |
| 마지막 상태 확인 | PIE 종료, `L_CombatField`, 104개 에셋 dirty 0. 에셋 저장 호출 없음 |
| MCP | 검증은 포트 8001에서 순차 호출. 작업 재개용 정상 에디터는 `.mcp.json`과 같은 포트 8000 사용 |

BP 컴파일의 경고 0과 C++ 빌드의 경고는 별개다. C++ 빌드에는 엔진 권장 버전보다 최신인 MSVC 경고, 엔진 헤더의 deprecated API 경고, adaptive build용 git 실행 경고가 있었다. 빌드는 성공했지만 경고 없는 빌드로 표현하지 않는다.

## 2. Shipping 패키징과 시작 확인

Win64 Shipping의 build → cook → stage → pak/IoStore → archive가 성공했다. `AutomationTool` 종료 코드 0, 전체 소요 시간 182.60초다. 필드와 던전 맵을 명시해 cook했다. 재실행할 때는 에디터를 종료한 뒤 아래 명령을 쓴다.

```powershell
& 'D:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\RunUAT.bat' BuildCookRun `
  '-project=D:\Project\UE\AstraTest\ue_test\SoulCombat\SoulCombat.uproject' `
  -noP4 -platform=Win64 -clientconfig=Shipping -build -cook `
  '-map=/Game/SoulCombat/Maps/L_CombatField+/Game/SoulCombat/Maps/L_Dungeon_01' `
  -stage -pak -iostore -archive `
  '-archivedirectory=D:\Project\UE\AstraTest\ue_test\SoulCombat\Saved\Packages\Win64Shipping' `
  -utf8output
```

- 시작 파일: `SoulCombat/Saved/Packages/Win64Shipping/SoulCombat.exe`.
- 실제 실행 파일: `SoulCombat/Saved/Packages/Win64Shipping/SoulCombat/Binaries/Win64/SoulCombat-Win64-Shipping.exe`.
- pak·ucas·utoc 생성 확인.
- 패키지 실행에서 프로세스가 유지되고 창 제목 `SoulCombat`, 응답 상태가 확인됐다. 테스트용 프로세스는 종료했다.
- 시작 스모크 테스트이며 실제 키 조작, 화면·소리, 패키지의 전체 게임 루프는 미검증이다.

## 3. PIE 자동 검증

저장된 실제 필드·던전, 실제 GA·GE·캐릭터를 사용했다. 테스트용 Python 브리지는 `Saved/`에 두고 `-EnablePlugins=PythonScriptPlugin`을 해당 에디터 프로세스에만 지정했다. uproject의 플러그인 설정은 변경하지 않았다. 피해·이동·회복 등의 테스트 준비는 PIE 월드에만 적용했다.

입력은 `AC_CombatComponent.PressInput/ReleaseInput`에 태그를 전달했다. 물리 키부터 Enhanced Input까지의 경로는 포함하지 않는다. 게이트의 실제 Interact를 호출하고, 입장·취소는 실제 버튼에 연결된 OnClicked 핸들러를 실행했다. 사람이 화면을 보며 클릭한 결과는 아니다.

| 분야 | 확인한 결과 |
| --- | --- |
| 평타 | 한 번이면 피해 50. 같은 프레임 4회·8회면 50+55+65+100=270, 4타로 종료. Attacking 상태 해제 |
| 시간차 입력 | 0.1초·0.35초 간격 지정의 4회 모두 피해 270, 4타 종료. 0.35초 시험의 실제 입력 시각 약 0.008/0.355/0.706/1.056초 |
| Q | SP20, 피해 150. 쿨다운 중 재입력 발동·추가 소비 없음 |
| E | SP 30, 피해 200, 대상 최고 Z 약 344.9(시작 Z 약 95에서 약 250 상승) |
| R | SP25, 피해 125. 별도 시나리오에서 세 대상에 각각 125를 한 번씩 적용 |
| 대시·점프 | 대시 스태미나 25, 무적 부여·종료. 점프 최고 Z 약 275.8, 착지·상태 종료 |
| 가드·피격 | 가드 중 실제 공격 피해 5·경직 없음. 해제 후 피해 25·경직 발생 |
| 취소·무적 | 대시로 평타 취소, 무적 중 피해 0·경직 없음. 종료 후 상태 해제 |
| 자원 부족 | 실제 GE로 SP0 상태를 만들어 Q 발동 거부·피해 없음 확인 |
| 게이트 | 상호작용 → 개방 → 입장 위젯. 취소 시 필드 유지·위젯 제거·커서 해제. 입장 시 실제 던전 이동 |
| 던전 | Start 자동 클리어, Mob1의 3+2마리, Event, Mob2의 3+3마리, Boss의 시작·클리어와 입출구 제어 |
| 이벤트 성공 | 봉인석 3개 파괴, 공격력 50→65, HP1000/SP100 회복, 출구 열림 |
| 클리어 후 | 보스 HP바 표시 상태, 클리어 위젯 생성, 자동 필드 복귀. 위치(0,1450)·HP1000·입장/클리어 UI와 커서 정리 |
| 이벤트 시간 초과 | 약 29.985초에 미파괴 3개 비활성화, 보상 없음, 공격력 50 유지, 출구 열림 |
| 사망·부활 | 사망 시 HP0·Dead태그·공격 취소·입력 거부. 방의 RespawnPoint에서 전부 회복·Dead 해제 |
| 보스 | HP50% 이하에서 공격력 60→78. 20초 관찰에서 공격 1/2/3 쿨다운 태그를 각각 확인 |

합격 체크는 전투 37, 타이밍/관통 3, 던전 흐름 22, 경계 조건 최초 7, 부활 재검사 2개다. 체크에는 동일 행동의 수치·종료 상태 등 여러 관찰을 포함한다. 게이트의 단계 확인은 별도 결과 파일로 기록했다.

방·적 처치에는 테스트용 큰 공격 계수, 이동에는 순간이동을 사용했다. 방 진행 로직의 검증이며 난이도·이동 체험·사람의 정상 플레이로 클리어 가능한지의 증명은 아니다. 보스 세 행동의 발동도 연출을 눈으로 확인했다는 의미는 아니다.

## 4. 중간 실패와 검증 방법의 한계

- 첫 환경 빌드는 다른 체크아웃의 Live Coding, Shipping 첫 시도는 이 검증용 에디터의 Live Coding으로 중단됐다. 소유한 에디터를 종료하고 Shipping을 재실행해 성공했다. 관련 없는 프로세스를 일괄 종료하지 않았다.
- 흐름 검사 첫 시도는 위젯 안의 공개되지 않은 텍스트 변수를 읽다가 검사 코드가 실패했다. 공개된 위젯 참조·Visibility·이동 후 상태를 사용하도록 바꾸고 새 PIE에서 전체 흐름을 다시 검사했다. 화면 글자나 배치가 맞다는 판정에는 쓰지 않는다.
- 부활 검사 첫 시도는 예상 X를 3350으로 고정해 실측 3650을 실패로 판정했다. 실제 방의 `RespawnPoint`는(3650,0,100)이다. 별도 PIE에서 이 설정을 직접 읽고 사망·부활을 재검사해 XY 일치·전부 회복·Dead 해제를 확인했다. 부활 후 Z 약 92.175는 접지 후 관찰값이다. 첫 실패 기록을 보존하며 게임 버그로 취급하지 않는다.
- 숨겨진 에디터는 배경 CPU 제한 설정을 꺼도 3fps가 될 수 있다. UE 5.8.3의 `UEditorEngine::ShouldThrottleCPUUsage`는 모든 창이 숨겨진 경우도 검사한다. 이번 타이밍 시험은 전용 에디터를 `-unattended`로 시작해 제한 없는 PIE에서 진행했다. 전투 시험 1257개 샘플의 프레임 중앙값 약 8.52ms, 최대 125ms를 관찰했다. 성능 벤치마크는 아니다.
- Shipping에서 `ExecCmds`를 받는 코드는 `!UE_BUILD_SHIPPING` 조건에 들어가므로 그 방식으로 게임 루프를 자동 조작할 수 없었다. 패키지 시작 확인과 에디터 PIE의 로직 검증을 나눴다.

## 5. 문서·구현 대조와 개선 방향

| 대조한 점 | 현재 상태와 이번 반영 |
| --- | --- |
| 평타 입력 버퍼 | 실제 `QueuedInputs`, `MaxQueuedInputs=3`. 04 앞부분의 bool 방식은 과거 실패 기록. 후반 수정과 07 안내 추가 |
| 경직 | `GA_HitReact` Activation Owned Tags와 `StunDuration=0.4`. 존재하지 않는 `GE_HitStun`을 쓴다는 01 설명 수정 |
| 쿨다운 HUD | `WBP_SkillSlot.Refresh`의 `GetActiveEffectsWithAllTags`와 GE의 AssetTags가 02 설계와 일치. API노트의 OwningTagQuery 제안을 필수 수정으로 오해하지 않도록 보충 |
| 안전한 그래프 읽기 | 02의 `read_graph_dsl` 절차를 `find_nodes` + `get_node_infos`로 수정. Assign 그래프에 이벤트를 만드는 알려진 MCP 문제 회피 |
| 피해 계산 | `PostGameplayEffectExecute`와 IncomingDamage의 현재 구조도 사용할 수 있는 선택. ExecutionCalculation만 정답이라는 05설명 수정 |
| SetByCaller비용 제안 | 기본 CheckCost의 검사 Spec과 나중에 값을 넣는 적용 Spec을 구분. 공용화만으로 SP 부족 거부까지 보장하지 않음 |
| BP클래스 참조 | 생성 불가는 제작 당시 MCP의 제약이며 UE/BP자체의 제약이 아님 |
| C++규모 | 클래스 2개와 헤더/구현을 포함한 파일 수 구분 |
| 로드맵 | 직군·C++전환·멀티플레이·스킬 8개는 선택할 발전안. 학습의 필수 조건으로 삼지 않음 |

실제 노드의 주요 책임을 추적하기 위해 `AC_CombatComponent`, `GA_Player_BasicAttack`, `GA_HitReact`, `BP_DungeonRoom`, `WBP_SkillSlot`, `BP_EnemyAIController`를 안전한 읽기로 확인했다. 모든 BP의 모든 핀을 형식 검증했다는 의미는 아니다.

학습 후보는 입력/큐 → 피해 → 취소/상태 수명 → 판정 시각과 애니메이션 → 스킬 데이터 → 장애물에 대한 AI 대응이다. 먼저 예상·관찰·원인 후보·최소 실험을 기록한다. 상세 방향은 `07-study-guide.md`에 있다. 이번 점검에서 신기능·리팩토링은 하지 않았다.

## 6. 남은 사람 검증

- PIE에서 실제 WASD·마우스·좌/우클릭·Q/E/R·Shift·Space·F와 입장/취소 조작.
- 실제 키 입력의 0.35초 4콤보, 카메라, 가드 각도, 넉백, 애니메이션과 판정의 시각적 일치.
- Shipping패키지에서 필드 → 게이트 → 던전 → 클리어 → 복귀를 정상 플레이로 진행.
- UI 글자·배치·가독성, 해상도 차이, VFX와 소리. 시작 시험은 `-nosound`라 소리 검증에 쓰지 못함.
- UE없는 PC로 옮겨 런타임 의존 설치·배포물 실행 확인. 패키지는 폴더 전체가 필요하며 exe하나만 옮기지 않음.
- 장시간 플레이, 연속 입퇴장, 종료/재실행, 성능과 플레이 편의성.

현재 판정은 **개발 환경·주요 로직 자동 검증·패키지 제작 준비 완료**다. 사람 플레이를 포함한 최종 수용 검증 완료는 아니다.

## 7. 이 PC에 남긴 근거

아래 파일은 `SoulCombat/Saved/`의 로컬 자료로 Git추적 대상이 아니다. 다른 PC에 자동으로 옮겨지지 않는다.

| 파일 | 내용 |
| --- | --- |
| `pc-readiness-result.json` | BP 72개 컴파일, dirty 전후, 맵 |
| `packaging-shipping.log` | 성공한 UAT 전체 로그 |
| `packaging-shipping-attempt1.log` | Live Coding으로 중단된 첫 로그 |
| `audit-shipping-smoke.json` | Shipping프로세스 시작·응답 |
| `audit-dependencies.json`, `audit-final-static.json`, `audit-final-dirty.json`, `audit-working-editor.json` | 의존성·실제 기본값·PIE 종료 후 상태·일반 에디터 재개 상태 |
| `audit-combat-result.json`, `audit-timing-result.json` | 전투 37·시간차 입력/관통 3개 체크와 관찰값 |
| `audit-gate-*.json`, `audit-flow-result.json` | 입장/취소·흐름 22개 체크 |
| `audit-flow-attempt1.json` | 위젯 읽기 실패의 첫 기록 |
| `audit-edge-result.json`, `audit-checkpoint-result.json` | 경계 조건 8개 체크(첫 기준 오류 1건 포함)·독립된 부활 재검사 2개 체크 |
| `audit-graph-*.json` | 주요 BP 6개의 노드·연결 읽기 |
| `audit_bridge.py`, `audit_send.py`, `audit_*tests.py`, `audit_checkpoint_test.py` | 현재 PC의 임시 검사 코드 |

일반 작업용 에디터에서는 Python 브리지를 시작하지 않는다. 검사 코드를 재사용할 때는 새로운 PIE의 초기화·대상 이름·실행 순서를 확인해야 하며, 그대로 범용 테스트 기반으로 취급하지 않는다.

## 8. API 판단 근거

- [Epic 속성·AttributeSet 설명](https://dev.epicgames.com/documentation/unreal-engine/gameplay-attributes-and-attribute-sets-for-the-gameplay-ability-system-in-unreal-engine): 메타 속성과 PostGameplayEffectExecute 처리.
- [Epic GAS 구성 설명](https://dev.epicgames.com/documentation/unreal-engine/understanding-the-unreal-engine-gameplay-ability-system): 계산 분리·네트워크 기능을 포함한 구성.
- [Epic GameplayAbility 설명](https://dev.epicgames.com/documentation/unreal-engine/using-gameplay-abilities-in-unreal-engine): 비용·쿨다운·Commit의 역할.
- 로컬 UE 5.8.3 소스: `GameplayAbilities/Private/Abilities/GameplayAbility.cpp`의 CheckCost/ApplyCost, `GameplayAbilities/Private/GameplayEffect.cpp`의 CanApplyAttributeModifiers, `UnrealEd/Private/EditorEngine.cpp`의 ShouldThrottleCPUUsage, `Engine/Private/UnrealEngine.cpp`의 ExecCmds 조건. 이후 엔진 버전에서는 다시 확인한다.
