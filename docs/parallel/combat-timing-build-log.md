# 몽타주 판정·돌진 경로 제작 기록 (담당 A)

2026-09-30. 사용자 제작 위임과 `09-production-plan.md`의 P1 계약에 따라 구현했다. 보스 내려찍기와 돌진은 통합 담당이 소유 범위를 추가 승인했다. 아직 통합 에디터와 Shipping 패키지의 검증 결과는 포함하지 않는다.

## 작업 기준과 소유

- worktree: `D:/Project/UE/AstraTest/_workers/combat-timing`
- branch: `codex/combat-timing`, 기준 커밋 `81a750f`
- UE 5.8.3, 프로젝트 `SoulCombat/SoulCombat.uproject`, MCP8001, 에디터 PID39636
- 공통 태그 `Event.Combat.HitFrame`, `Event.Combat.Combo.Chain`은 기준 커밋에 등록되어 있었다.
- 수정은 아래 전용 몽타주·노티파이와 담당 GA에 한정했다. 템플릿 원본, 공통 캐릭터·컴포넌트·PC·ini·C++는 변경하지 않았다.

## 실패 재현과 원인

개별 `CustomTimeDilation=0.25`에서는 애니메이션의 진행도 느려지지만 기존 GA의 `WaitDelay(HitTime / PlayRate)`는 월드 시간으로 끝났다. 구현 전에 작성한 평타 8개 검사 중 배율0.25·0.5가 실패했다. 0.25 검사에서 약0.475초 뒤 실제 몽타주 위치0.11875에 피해50이 발생했다. 기대 타격 위치는0.467이다. 통합 담당의 별도 `ue_actor_clock.py`도 같은 원인을 재현했다.

보스 내려찍기의 예고1.2초는 의도된 월드 타이머로 보존했다. 별도 타격 `HitDelay=0.45`는 애니메이션 배율과 분리되어, 배율0.25에서 몽타주 위치 약0.913에 피해125가 발생했다. Attack 섹션 시작0.8+타격0.45=1.25보다 빨랐다.

돌진은 속도2500, 표본0.15/0.35/0.55초, 반경200이다. 연속 표본 중심의 이동 간격500이 구 지름400보다 커서 빈 공간이 생길 수 있고, 마지막 표본 뒤 이동도 검사하지 않았다. 실제 Pawn 충돌을 유지하면 중간의 일부 누락 후보는 몸이 막혀 기존 구현에서도 맞았다. 따라서 후보 전체를 실패로 단정하지 않았다. 실제 RED는 끝점1490, 첫 표본 사이에서 옆걸음한 대상625, 끝점1400에서 옆걸음한 대상에서 재현했다. 유효 경로 밖1650은 피해0이 맞는 대조군으로 두었다.

수정 전 계획은 기존 피해·이동·입력 규칙을 보존하면서 애니메이션 타격은 몽타주 이벤트로, 돌진의 공간 간격은 이전 위치부터 현재 위치까지 구 스윕으로 잇는 것이었다. 첫 출발점과 마지막 이동/어빌리티 종료점도 검사하도록 했다.

## 최종 구현

`AN_SCGameplayEvent`는 AnimNotify BP다. `Received_Notify`에서 Mesh의 소유자에게 설정된 이벤트 태그를 보낸다. Payload의 Instigator와 Target은 소유자, OptionalObject는 받은 Animation, EventMagnitude는 평타 단계다. 노티파이는 여러 캐릭터가 공유하므로 런타임 타격 상태를 저장하지 않는다. CDO와 각 노티파이의 `should_fire_in_editor=false`로 미리보기에서 게임 이벤트를 보내지 않는다.

GA는 몽타주 재생 전에 반복 `WaitGameplayEvent`를 등록한다. 자기 몽타주와 아바타인지 확인하고, 평타는 단계도 확인한다. 피해 처리 전에 `bHitFrameConsumed=true`로 바꿔 재진입·중복 신호를 막는다. 종료 시 GAS가 이벤트 작업을 정리한다.

| 몽타주 | SCGameplay 트랙의 BranchingPoint | 사용처 |
| --- | --- | --- |
| AM_SCComboAttack | 타격0.467/1.467/2.400, 연결0.533/1.567/2.900, 단계1/2/3 | 평타1~3, Q/R, 보스 근접3타 |
| AM_SCChargedAttack | 타격1.167, 단계4 | 평타 피니시, E |
| AM_SCEnemyMelee | 타격0.450, 단계1 | 잡몹 근접 |
| AM_SCBossSlam | 타격1.250, 단계0 | 보스 내려찍기 |

기존 애니메이션·섹션·루트 모션과 템플릿 노티파이는 복제본에서 보존했다. 현재 캐릭터는 템플릿 `BPI_Attacker`를 구현하지 않으므로 원본 콤보 노티파이가 별도 피해를 발생시키지 않는다. 새 타격 태그는 명중 피드백의 ReportHit 함수와 구분된다.

- `GA_ActionBase.HandleHitFrame`: 유효 신호를 기존 `OnHitFrame` 훅으로 전달한다. GroundSlam·WaveSlash의 자식 오버라이드를 유지했다. 기존 HitTime 변수와 타격용 WaitDelay를 제거했다.
- `GA_Player_BasicAttack.HandleHitFrame/HandleComboChain`: 큐 최대3, 피해50/55/65/100, 각 단계 범위·넉백·띄우기, 대시/스킬 캔슬, 3→4타의 동기 OnInterrupted 가드를 유지했다. StepHitTimes/StepChainTimes와 관련 타이머를 제거했다. `BeginStepTimers`라는 기존 커스텀 이벤트 이름은 참조 보존을 위해 남겼으며, 이제 단계 상태 두 개만 초기화한다.
- `GA_Enemy_Melee_Boss`: 부모 잡몹의 새 몽타주를 그대로 상속하면 Melee03에 신호가 없다. 원본 자식의 HitTime0.4·Melee03·PlayRate0.9를 실제 CDO와 대조하고 AM_SCComboAttack을 명시했다.
- `GA_Boss_Slam.HandleHitFrame`: 예고·Attack 섹션 점프·피해·종료 정리를 보존하고 타격만 전용 몽타주 이벤트로 옮겼다. 별도 HitDelay 변수/타격 타이머를 제거했다. 남은 WaitDelay 하나는 예고1.2초다.
- `GA_Boss_Charge.BeginChargePath/HitAlongPath`: 출발점을 기록하고 첫 길이0 스윕을 수행한다. 이후 Pawn 대상 `MultiSphereTraceForObjects`가 이전 검사 위치→현재 위치를 반경200으로 잇는다. 유효 적·HitActors 중복 검사를 거쳐 기존 ApplyHit를 호출한다. 기존 세 표본 외에 root motion 종료와 EndTime0.8 종료점도 검사한다. 계수1.8·넉백600·띄우기200·속도2500·지속0.6·전조0.5·기존 쿨다운을 보존했다.

돌진은 특정 애니메이션 포즈에서 한 번 타격하는 공격과 다르다. `ApplyRootMotionConstantForce`의 이동 수명과 기존 표본을 월드 시간으로 유지하고, 공간 누락만 수정했다. 따라서 Charge의 다섯 WaitDelay는 의도적으로 남아 있다. 스윕은 표본 사이의 직선 구간을 검사하며, 복잡한 장애물 곡선 경로를 정밀하게 재구성하는 기능은 추가하지 않았다.

## 이 엔진에서 확인한 도구 경로

엔진 헤더의 `AnimationBlueprintLibrary`는 Python ScriptName이 `AnimationLibrary`다. `add_animation_notify_event`가 반환한 노티파이에 태그/단계를 설정했다. 이 함수의 기본 TickType은 Queued이므로 그대로 사용하지 않았다. 트랙 이벤트를 읽고 `montage_tick_type=MontageNotifyTickType.BRANCHING_POINT`로 바꾼 뒤 `add_animation_notify_event_from_source`로 다시 넣었다. 마지막에 전용 트랙의 이벤트9개가 모두 BranchingPoint인지 확인했다.

엔진 `AnimMontage.cpp`의 BranchingPoint payload는 Montage를 SequenceAsset으로 전달하고, `AnimNotify.cpp`가 이를 `Received_Notify`의 Animation에 넘긴다. 실제 첫 PIE 스모크에서 받은 Animation 이름이 AM_SCComboAttack임을 로그로 확인했다. 확인용 PrintString은 제거했다. 단순히 이름을 유추해 OptionalObject 필터를 적용하지 않았다.

그래프 읽기는 `find_nodes`+`get_node_infos` 덤프를 사용했다. `read_graph_dsl`의 디스패처 부작용을 피했다. 최종 11개 그래프를 왼쪽→오른쪽으로 배치하고 한국어 주석을 정리했다. 주석 툴의 K2Node 타입 제약과 클립보드 좌표 스냅을 확인한 뒤, 엔진 `BlueprintGraphEditor.h:361~384`의 `list_comment_nodes/remove_comment_node/add_comment_node`와 `BlueprintEditorLibrary.set_node_pos`를 사용했다. 위치/주석 정리 전후 실행 노드·연결·핀 값은 모든 그래프에서 `same-logic`이 일치했다.

## 자동 검증 결과

모의 게임 데이터 없이 실제 PIE 캐릭터·ASC·몽타주·GE·Pawn 충돌을 사용했다. 테스트 월드에만 위치·배율·AI 대기 상태를 설정했다. 에셋을 PIE 중 변경하지 않았다.

| 검사 | 결과 | 확인 내용 |
| --- | --- | --- |
| 평타 초기 RED8 | 6통과/2실패 | 배율0.25·0.5에서 애니메이션보다 이른 피해 재현 |
| 적 공격 RED10 | 6통과/4실패 | 느린 내려찍기와 실제 돌진 끝점/옆걸음 누락 재현 |
| 평타 최종14 | 14/14 | 배율0.25/0.5/1/1.5, 같은 프레임4/8입력, 배율0.5콤보, 짧은 히트스톱, 중복/다른 액터·몽타주 이벤트, 대시·몽타주 중단·피격·사망 취소 |
| 적 공격 최종12 | 12/12 | 느린 Slam/보스근접/잡몹근접, 돌진 출발·두 표본 사이·끝점과 옆걸음, 경로 밖 대조군 |
| 기존 전투 | 37/37 | 평타/스킬 피해, Q/E/R 비용·쿨다운, SP부족, 대시·가드·경직·종료 |
| 기존 타이밍/관통 | 3/3 | 0.1/0.35초 4연타, 다중 투사체 관통·중복 금지 |
| 컴파일·저장 | 통과 | 담당 BP10개 warnings_as_errors=true, 에셋14개 명시 저장·dirty=false |
| 그래프 정리 | 통과 | 5개 BP 전체 그래프의 실행 노드·핀 값·연결 동일성 |

최종 배율0.25 평타는 약1.871초/몽타주 위치0.46784에서 피해50이 한 번 발생했다. 내려찍기0.25는 위치1.26399에서125, 보스 근접0.5는2.40155에서60, 잡몹 근접0.5는0.45004에서25가 한 번 발생했다. 같은 프레임8입력도 기존 큐 상한 때문에 총4타/270이며, 중복 신호를 보내도 추가 피해는 없었다.

`Tools/tests/combat_timing_pie.py`, `combat_enemy_timing_pie.py`는 재실행할 수 있는 담당 검사 코드다. 초기8개와 적 RED 검사를 구현 전에 작성했고, 평타 추가6개와 보스/잡몹 근접2개는 구현 후 검증 범위를 확장했다. 전체 프로젝트의 자동 검사와 구분한다.

상세 원본은 이 worktree의 ignored `SoulCombat/Saved`에 보존했다: `combat-timing-red.json`, `combat-timing-green.json`, `combat-enemy-timing-red.json`, `combat-enemy-timing-green.json`, `audit-combat-result.json`, `audit-timing-result.json`, `a-final-static-result.json`, `a-save-result.json`, `a-*-format-before/after.json`, `a-mcp-history.jsonl`. 검사 요약과 실제 측정치는 이 문서와 `combat-timing-verification.json`에도 저장했다.

## 변경 파일과 남은 통합

새 에셋5개는 AN_SCGameplayEvent와 위 몽타주4개다. 기존 GA9개(ActionBase, BasicAttack, DashSlash, GroundSlam, WaveSlash, Enemy_Melee, Enemy_Melee_Boss, Boss_Slam, Boss_Charge)를 수정했다. 담당 검사2개와 이 기록·검증 요약·checklist를 추가/갱신했다.

이 결과는 기준81a750f의 독립 작업 사본에서 검증한 것이다. 통합 담당의 피드백 컴포넌트·실제 히트스톱·PC/UI와 합친 후 전체 BP 컴파일·참조·배속·전투/던전 회귀, Shipping 패키징이 필요하다. 이번 히트스톱 검사는 테스트 월드의 짧은 개별 배율 변경이며, 최종 피드백 컴포넌트의 동작 검증은 아니다. 실제 키·마우스, 화면·소리·손맛, UE 없는 PC 실행은 사람이 확인할 항목으로 남긴다.
