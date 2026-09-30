# 11. 제작본 통합 검증

현재 전투 필드와 던전 하나의 싱글 플레이 제작본을 대상으로 한다. 2026-09-30 돌진 수정 뒤 최종 통합 회귀178조건과 별도 돌진6·자율 AI17·피드백 독립57조건, 최종 BP77개 엄격 재컴파일·전체 정적 검사를 확인했다. 합계258은 중복 기능 관찰을 포함한 검사 조건 수다. 제작본 Shipping 패키지·시작 확인은 아직 대기 중이다. 초기 PC 준비 기록 `08-pc-validation.md`와 담당 사본의 결과는 이 제작본의 최종 결과와 구분한다.

## 제작 변경

- 타격·콤보 타이머를 전용 몽타주 BranchingPoint 이벤트로 교체했다. 아바타·몽타주·단계를 확인하고 한 단계의 타격을 한 번 소비하며 입력 큐3·피니시·취소·기존 피해와 비용을 유지한다.
- 실제 GE 적용 전후 Health 차를 컨트롤러에 전달한다. 히트스톱, 오버레이 플래시, 피해 숫자·가드 표시, 카메라 FOV 펄스와 직접 만든 명중·가드 효과음을 연결했다. 통합 원본의 피드백 에셋 기본값과 PC 배치 컴포넌트는 bEnableHitstop=true다. 원래 배율·FOV·오버레이와 외부 변경을 보존한다.
- Esc 메뉴에 계속하기·현재 맵 처음부터 재시작·필드 복귀·종료·조작 안내를 넣었다. 메뉴 진입과 맵 전환에서 명중 연출을 정리한다. 자동 부활은 방 진행 유지, 메뉴 재시작은 현재 맵 전체 초기화다.
- 스킬 비용·자원 종류·실제 쿨다운 표시와 방별 사망 복구를 대조했다. 보스 돌진은 이전 위치부터 현재 위치까지의 스윕과 시작·끝점 검사를 사용한다.

## 기준과 정적 검사

- 체크아웃: `D:\Project\UE\AstraTest\ue_test`, UE 5.8.3 CL58210709.
- 병행 기준 `81a750f`; A 반환 `2f6e9ec`, B 반환 `09c2aed`를 원본에 통합했다. 실제 원본 통합 커밋은 `308e7f2`, `89062ed`다. 이후 컨트롤러 연결·기본 히트스톱 활성화는 통합 담당이 수행했다.
- 모든 연결과 돌진 수정 이후 `/Game/SoulCombat` 에셋116개, BP77개를 다시 실제 집계했고 부모 우선 `warnings_as_errors=true` 최종 컴파일77/77이 통과했다.
- 최종 전체 의존 집합227개는 존재하는 에셋210개와 Script 패키지17개다. 누락0, `_Scratch` 참조·에셋0, 콘텐츠·맵 dirty0이다. `SoulCombat/Saved/full-final-static.json`은 `passed=true`, 부모 순환0, 엄격 컴파일 통과77/실패0과 PID40248·PIE false·`L_CombatField`를 기록한다. 이 정적 검사는 에셋을 저장하지 않았다.
- 명중/가드 오디오는 외부 샘플 없이 생성했다. 48kHz 모노 PCM, 0.16/0.23초, 형식·무클리핑·양끝0·재현성 검사를 통과했다.

## 돌진 실패의 원인과 보정

첫 통합 실행은 실제 피해 피드백17개가 모두 통과했으나 실행기의 예상 수16과 달라 중단했다. 예상 수를 보정하고 결과를 보존했다. 두 번째 실행은 적 공격12 중 돌진의 두 중간 옆걸음에서 기대 피해90과 실제0이 달라 중단했다.

원인은 HitAlongPath의 실행 순서였다. 순수 `GetPreviousTraceLocation`은 이전 값의 사본이 아니므로 스윕 전에 `SetPreviousTraceLocation`을 실행하면 Trace의 Start와 End가 같아졌다. 표본 끝점이 목표 가까이에 있을 때만 우연히 맞았고, 히트스톱은 표본 위치를 바꿔 증상을 가렸다. 첫 피해0은 히트스톱 적용 전에 발생했으므로 별도 이동 수명 변경으로 해결하지 않았다.

실행 연결을 `IsValid → MultiSphereTraceForObjects → SetPreviousTraceLocation → ForEachLoop`로 보정했다. 노드26개와 데이터 핀·기본값은 그대로이며, 기존 피해/범위/히트수/쿨다운/전조/속도/지속시간과 다른 GA를 보존했다. 격리한 실제 PIE 스윕6조건은 두 중간 옆걸음·역방향의3실패에서6통과로 바뀌었다. 적 공격12조건도 실제 어빌리티·Root Motion과 히트스톱 활성 상태에서 모두 통과했고 범위 밖의 피해0·대상별1회 피해를 유지했다.

근거는 `SoulCombat/Saved/charge-fix-verification.json`, `combat-charge-sweep-red.json`, `combat-charge-sweep-green.json`, `combat-enemy-timing-integrated-green.json`이다. `charge-exec-diff.json`은 실행 연결 변경과 데이터 핀·기본값 불변, `charge-layout-audit.json`은 배치 후 핀 불변, `charge-final-save-result.json`은 저장·PIE 종료·dirty0을 기록한다.

## 최종 통합 자동 회귀

돌진 수정 뒤 세 번째 실행의 `SoulCombat/Saved/integrated-regressions.json`은 `done=true`, `passed=true`, `error=null`이다. 11개 묶음178조건이 약203초에 통과했고 마지막에는 PIE가 종료되고 에디터가 `L_CombatField`에 돌아왔다.

| 검사 | 통과 조건 | 실제 소스 (`Tools/tests/`) |
| --- | --- | --- |
| 개별 배속0.25의 몽타주 타격 시점 | 1 | `ue_actor_clock.py` |
| GE 실제 감소량·무적/가드/과잉피해·사망 적·메뉴 복원 | 17 | `ue_real_damage_feedback.py` |
| 메뉴의 정지·시간·위젯·커서·반복 복귀 | 8 | `ue_pause_menu.py` |
| 실제 버튼 델리게이트·맵 재시작/복귀/종료 | 9 | `ue_pause_buttons.py` |
| Mob1/Mob2/Boss 사망·자원/체크포인트 복구·진행 유지 | 39 | `ue_dungeon_recovery.py` |
| 실제 스킬 비용·소모 속성·발동·쿨다운 표시 | 16 | `ue_skill_ui.py` |
| 평타의 배속·큐·피니시·중복/취소 판정 | 14 | `combat_timing_pie.py` |
| 내려찍기/잡몹/보스 근접·돌진 경로·히트스톱 | 12 | `combat_enemy_timing_pie.py` |
| 기존 전투·피해·비용·태그·입력 거부 | 37 | `ue_combat_regression.py` |
| 기존 타이밍·투사체 관통/중복 금지 | 3 | `ue_timing_regression.py` |
| 필드→게이트→던전→보스→클리어→복귀 | 22 | `ue_dungeon_flow.py` |
| 합계 | 178 | 11개 묶음 |

원본에서 연결 이후 다시 실행한 `Tools/test_combat_feedback.py`의57조건도 모두 통과했다. `SoulCombat/Saved/combat-feedback-tests.json`은 `done=true`, 실패 배열0·예외 null이다. 독립 컴포넌트의 반복 명중·외부 변경·사망/부활·일시정지·전역 배속·파괴/EndPlay·숫자 수명/상한을 확인하며, 게임의 실제 ApplyHit 전달은 위17조건으로 함께 확인한다.

## 자율 AI 관찰

`Tools/tests/ue_ai_autonomy.py`는 기존 `SparringGrunt_1`의 Think 타이머와 Tick을 바꾸거나 Think/PressInput을 직접 호출하지 않는다. `SoulCombat/Saved/ai-autonomy-result.json`의17조건은 `done=true`, `passed=true`, `error=null`로 통과했다.

- 실제 배치 AggroRange800cm와 CDO2500cm, 공격 거리180cm, Think 간격0.2초를 읽었다.
- 범위 밖에서 기다린 뒤 원래 적 위치의 +Y700cm에 플레이어를 배치했다. AI가 자연 접근해 State.Attacking과 실제 GE 피해25·유효 숫자 위젯25를 확인했다.
- 현재 적 위치에서1000cm 밖에 플레이어를 배치한 뒤 기존 공격 몽타주가 끝나길 기다렸다. 이후 새 추격·공격·HP 감소가 없었고 재진입 때 다시 피해25가 발생했다.
- 실제 GE_Damage로 플레이어를 사망시킨 뒤 설정된3초 부활 전까지 bChasing=false와 새 공격 없음, 기존 Think 타이머·Tick 유지를 확인했다.

플레이어의 CharacterMovement만 PIE에서 MovementMode.NONE으로 고정하고 다른 스파링 적은 휴면으로 격리했다. 설정 복원과 PIE 종료를 수행한다. 이 검사는 장애물 우회·공간별 난이도·일반 조작의 낙하/넉백·사람의 입력을 검증하지 않는다.

## 패키지 상태

제작본 Win64 Shipping build/cook/stage/archive·패키지 시작 스모크는 대기 중이다. `08-pc-validation.md`의 Shipping 성공은 `main/cc31c5c`에 대한 초기 PC 준비 결과이며, 이번 몽타주·피드백·메뉴·돌진 변경이 포함된 패키지의 성공으로 표시하지 않는다. 실행 안내와 사람 확인 순서는 `10-play-guide.md`를 따른다.

## 사람이 확인할 범위

자동 검사는 실제 게임 에셋과 GE·어빌리티·위젯·PIE 월드를 사용한다. 위치·배율·일부 AI 정지는 테스트 월드에만 적용하며 에셋을 저장하지 않는다. 함수·델리게이트 검사를 실제 키·마우스 조작으로 표시하지 않는다.

통합 담당이 정지 메뉴의 실제 스크린샷을 직접 확인했다. 한국어 글자,4개 버튼과 조작 안내가 표시되고 배치 겹침이 없었다. 실제 키·마우스의 진입/복귀와 전투 중 전체 UI 가독성은 별도 확인 대상이다.

남은 사람 검증은 실제 입력, 애니메이션 연결과 손맛, 숫자·가드·오버레이의 화면 가독성, 음향 청음, 정상 조작으로 전체 던전 완주, UE 없는 PC의 설치·실행, 장시간 안정성이다. 자동 검증에서 이미 수정한 기능의 구현 완료와 이 항목들의 플레이 승인은 구분한다.
