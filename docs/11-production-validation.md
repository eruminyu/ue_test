# 11. 제작본 통합 검증

최종 Win64 Shipping 빌드와 패키지 시작·응답 검사가 통과했다. 전투 필드와 던전 하나의 싱글 플레이 제작본은 통합 회귀178·별도 돌진6·자율 AI17·피드백 독립57의 합계258개 조건, BP77개 엄격 컴파일, 주석 GUID 보정과 최종 cook의 오류0·경고0을 확인했다. P1·P2 구현과 자동 회귀, P3 적/보스·회복·던전 흐름의 자동 검증, P4 결과물 빌드와 자동 시작은 완료했다. 난이도·손맛·실제 키/마우스·청취·정상 종료 UI·UE 없는 PC·장기 플레이는 사람 검증으로 남긴다. 258은 중복 기능 관찰을 포함한 검사 조건 수이며 초기 PC 준비 기록 `08-pc-validation.md`와 담당 사본의 결과를 최종 통합 결과와 구분한다.

## 제작 변경

- 타격·콤보 타이머를 전용 몽타주 BranchingPoint 이벤트로 교체했다. 아바타·몽타주·단계를 확인하고 한 단계의 타격을 한 번 소비하며 입력 큐3·피니시·취소·기존 피해와 비용을 유지한다.
- 실제 GE 적용 전후 Health 차를 컨트롤러에 전달한다. 히트스톱, 오버레이 플래시, 피해 숫자·가드 표시, 카메라 FOV 펄스와 직접 만든 명중·가드 효과음을 연결했다. 통합 원본의 피드백 에셋 기본값과 PC 배치 컴포넌트는 bEnableHitstop=true다. 원래 배율·FOV·오버레이와 외부 변경을 보존한다.
- Esc 메뉴에 계속하기·현재 맵 처음부터 재시작·필드 복귀·종료·조작 안내를 넣었다. 메뉴 진입과 맵 전환에서 명중 연출을 정리한다. 자동 부활은 방 진행 유지, 메뉴 재시작은 현재 맵 전체 초기화다.
- 스킬 비용·자원 종류·실제 쿨다운 표시와 방별 사망 복구를 대조했다. 보스 돌진은 이전 위치부터 현재 위치까지의 스윕과 시작·끝점 검사를 사용한다.

## 기준과 정적 검사

- 체크아웃: `D:\Project\UE\AstraTest\ue_test`, UE 5.8.3 CL58210709.
- 병행 기준 `81a750f`; A 반환 `2f6e9ec`, B 반환 `09c2aed`를 원본에 통합했다. 실제 원본 통합 커밋은 `308e7f2`, `89062ed`다. 이후 컨트롤러 연결·기본 히트스톱 활성화는 통합 담당이 수행했다.
- 모든 연결과 돌진 수정 이후 첫 cook 전에 `/Game/SoulCombat` 에셋116개, BP77개를 실제 집계했고 부모 우선 `warnings_as_errors=true` 컴파일77/77이 통과했다. 주석 GUID 강제 재저장 후에도 같은116/77 집계와 엄격 컴파일77/77을 다시 확인했다.
- 주석 GUID 보정 뒤 전체 의존 집합227개는 존재하는 에셋210개와 Script 패키지17개다. 누락0, `_Scratch` 참조·에셋0, 콘텐츠·맵 dirty0이다. `SoulCombat/Saved/full-final-static-after-guid.json`은 `passed=true`, 부모 순환0, 엄격 컴파일 통과77/실패0과 PID24232·PIE false·`L_CombatField`를 기록한다. 이 정적 검사는 에셋을 저장하지 않았다. 첫 cook 전 자료 `full-final-static.json`과 이후 새 cook의 GUID 경고 검증을 각각 구분한다.
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

추적 가능한 새 회귀 실행기의 실제 에디터 연결은 `--suite charge-sweep` 선택6조건으로만 확인했다. `SoulCombat/Saved/runner-charge-integration.json`은 done/passed=true·error=null·condition_count6·약13.1초를 기록한다. 기존178개 전체 실행 결과는 덮어쓰지 않고 보존했다. 새 실행기를 통한 전체/extended 묶음은 아직 실행하지 않았으며, 이 연결 확인을 추가로 서로 다른6개 게임 조건으로 합산하지 않는다.

## 자율 AI 관찰

`Tools/tests/ue_ai_autonomy.py`는 기존 `SparringGrunt_1`의 Think 타이머와 Tick을 바꾸거나 Think/PressInput을 직접 호출하지 않는다. `SoulCombat/Saved/ai-autonomy-result.json`의17조건은 `done=true`, `passed=true`, `error=null`로 통과했다.

- 실제 배치 AggroRange800cm와 CDO2500cm, 공격 거리180cm, Think 간격0.2초를 읽었다.
- 범위 밖에서 기다린 뒤 원래 적 위치의 +Y700cm에 플레이어를 배치했다. AI가 자연 접근해 State.Attacking과 실제 GE 피해25·유효 숫자 위젯25를 확인했다.
- 현재 적 위치에서1000cm 밖에 플레이어를 배치한 뒤 기존 공격 몽타주가 끝나길 기다렸다. 이후 새 추격·공격·HP 감소가 없었고 재진입 때 다시 피해25가 발생했다.
- 실제 GE_Damage로 플레이어를 사망시킨 뒤 설정된3초 부활 전까지 bChasing=false와 새 공격 없음, 기존 Think 타이머·Tick 유지를 확인했다.

플레이어의 CharacterMovement만 PIE에서 MovementMode.NONE으로 고정하고 다른 스파링 적은 휴면으로 격리했다. 설정 복원과 PIE 종료를 수행한다. 이 검사는 장애물 우회·공간별 난이도·일반 조작의 낙하/넉백·사람의 입력을 검증하지 않는다.

## 패키지 상태

첫 제작본 UAT는 코드 기준 `4c6ee1a`에서 Win64 Shipping build/cook/stage/archive에 성공했다. `SoulCombat/Saved/production-packaging-result.json`은 ExitCode0,58.329초,32파일,727,456,174바이트와 게임 실행 파일·`vc_redist.x64.exe`/`vc_redist.arm64.exe`2개 설치 파일의 존재를 기록한다. 출력은 `SoulCombat/Saved/Packages/Win64Shipping-20260930`이다. 이 결과의 `passed=true`는 UAT 종료와 필수 파일 검사를 뜻하며 최종 배포물 채택을 뜻하지 않는다.

첫 cook에는9개 BP의 서로 다른 주석 노드25개에서 `missing NodeGuid, this can cause deterministic cooking issues please resave package` 경고가 있었다. 동일 경고의 반복 출력은 중복 노드로 세지 않았다. 실제 로그는 `SoulCombat/Saved/production-packaging.log`, 대상 노드/패키지 목록은 `comment-guid-cook-red.json`에 보존했다. 첫 배포물은 원인 보정과 새 cook 검증의 비교 자료로 남긴다.

현재 UE5.8.3의 `BlueprintGraphEditor.cpp:1292`에 있는 `UBlueprintGraphEditor::AddCommentNode`는 새 주석에 `CreateNewGuid`를 호출하지 않는다. `EdGraphNode.cpp:693`의 `UEdGraphNode::PostLoad`는 유효 GUID가 없는 노드를 로드할 때 경고를 남기고 `CreateNewGuid`를 호출하며 이 분기에서 패키지를 dirty로 표시하지 않는다. 따라서 에디터 메모리에서 GUID가 복구되고 dirty0이어도 디스크의 패키지 보정이 저장됐다는 근거가 되지 않았다.

새 에디터 PID24232에서 대상9개 BP의 전체 노드·핀·연결을 먼저 기록하고 로드 시 복구된 GUID를 `only_if_is_dirty=False`의 네이티브 패키지 강제 저장으로 직렬화했다. `comment-guid-resave-result.json`은9개 저장 성공, 피드백 CDO의 bEnableHitstop=true와 dirty 콘텐츠/맵0을 확인한다. `comment-guid-same-logic.json`은9개 BP·64개 그래프·925개 실행 노드의 타입·위치·전체 입력/출력 핀·값·연결이 전후 JSON 구조까지 동일함을 기록한다. 게임 동작을 바꾸는 수정은 없으며 기존258개 실행 조건을 게임 동작의 검증 근거로 유지한다. 보정 후 전체77개 엄격 컴파일·에디터 종료·별도 새 출력 경로 재UAT를 마쳤고 최종 cook에서 GUID 경고0을 확인했다.

최종 빌드 소스는 `dd559e08481ca1726ed6e1f967eee06de21c185a`다. `SoulCombat/Saved/production-packaging-final-result.json`은 done/passed=true·ExitCode0·51.797초·32파일·727,456,174바이트와 런타임 설치 파일2개 존재를 기록한다. `production-packaging-final.log`의 cook 결과는 `Success - 0 error(s), 0 warning(s)`이며 missing NodeGuid 출력은0이다. 최종 배포물은 `SoulCombat/Saved/Packages/Win64Shipping-20260930-Final`이고 첫 경고 포함 출력과 별도로 보관한다.

`SoulCombat/Saved/production-shipping-smoke.json`은 done/passed=true·error=null·31.029초의 시작·응답 검사를 기록한다. 최종 배포물의 부트스트랩 PID1616이 실제 Shipping 실행 파일의 자식 PID468을 만들었고,5~25초의5회 관찰에서 모두 Responding=true·창 제목 SoulCombat·창 핸들16912436이었다. 실제 실행 파일 경로와 부모 PID도 대조했다. 검사 후에는 이 검사에서 시작한 경로·부모 PID에 일치하는 프로세스를 Stop-Process로 정리했다. 정상 종료 UI를 통한 종료와 사람의 게임 플레이는 이 검사에 포함하지 않았다.

| 제작본 패키지 단계 | 현재 확인 상태 |
| --- | --- |
| 첫 UAT (`4c6ee1a`) | 성공, 주석 GUID 경고로 최종 배포물 미채택 |
| 대상9개 BP 강제 재저장·전체 노드/핀/연결 same-logic | 저장9/9,64개 그래프·925개 실행 노드 동일 |
| 주석 GUID 보정 후 전체 BP77개 엄격 컴파일 | 77/77 통과, 의존 누락/Scratch/dirty0 |
| 별도 새 출력 경로 Win64 Shipping 재UAT·GUID 경고 해소 | ExitCode0, cook 오류0·경고0,51.797초 |
| 최종 배포물 시작·응답·검사 프로세스 정리 | 실제 Shipping 자식·5회 응답·창 확인,31.029초 |

전달용 `SoulCombat/Saved/Packages/SoulCombat-Win64-20260930.zip`을 만들고33개 항목(UAT 파일32개+한국어 플레이 안내)의 전체 CRC를 검증했다. 크기는435,928,098바이트이며 SHA256은 `aea0f99dfad2eedca5d9f70623cf1bf04747d9e2c4ef632ee7b6c18d8d9896b5`다. `SoulCombat/Saved/production-package-bundle.json`과 추적 가능한 `docs/verification/production-verification.json`에 패키지 파일별 크기·SHA256과 ZIP 결과를 보존했다. 작업 에디터·검사 게임 프로세스가 없고 MCP8000/8001/8002도 종료 상태임을 후속 확인했다. 로컬 커밋만 수행하며 Git push는 하지 않았다.

`08-pc-validation.md`의 Shipping 성공은 `main/cc31c5c`에 대한 초기 PC 준비 결과다. 첫 제작본 UAT와 경고 보정 뒤 최종 패키지를 각각 구분한다. 실행 안내와 사람 확인 순서는 `10-play-guide.md`를 따른다.

## 사람이 확인할 범위

자동 검사는 실제 게임 에셋과 GE·어빌리티·위젯·PIE 월드를 사용한다. 위치·배율·일부 AI 정지는 테스트 월드에만 적용하며 에셋을 저장하지 않는다. 함수·델리게이트 검사를 실제 키·마우스 조작으로 표시하지 않는다.

통합 담당이 정지 메뉴의 실제 스크린샷을 직접 확인했다. 한국어 글자,4개 버튼과 조작 안내가 표시되고 배치 겹침이 없었다. 실제 키·마우스의 진입/복귀와 전투 중 전체 UI 가독성은 별도 확인 대상이다.

남은 사람 검증은 실제 입력과 정상 종료 UI, 애니메이션 연결·난이도·손맛, 숫자·가드·오버레이의 화면 가독성, 음향 청음, 정상 조작으로 전체 던전 완주, UE 없는 PC의 설치·실행, 장시간 안정성이다. 자동 검증에서 이미 수정한 기능의 구현 완료와 이 항목들의 플레이 승인은 구분한다.
