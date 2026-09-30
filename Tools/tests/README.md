# 실제 에셋 회귀 검사

이 폴더는 기존 `SoulCombat/Saved/audit_*.py` 검사를 재현할 수 있도록 보관한다. `Saved` 원본은 유지한다. 게임의 실제 BP·GA·GE와 PIE 월드를 사용하며 에셋을 수정하거나 저장하지 않는다. 순간이동·큰 피해·자원 소모 등의 준비는 테스트 PIE에서만 수행한다.

## 테스트 전용 에디터와 브리지

아래 명령은 **테스트용 체크아웃의 기존 에디터가 종료된 상태**에서 그 저장소 루트에서 실행한다. 다른 에디터와 병행하려면 별도 프로젝트 사본/체크아웃과 비어 있는 포트를 사용한다. 예시 포트는 8003이며, 기존 8000·8001·8002의 작업을 대신 종료하지 않는다.

```powershell
$repoPath = (Get-Location).Path
$projectFile = Join-Path $repoPath 'SoulCombat\SoulCombat.uproject'
$savedPath = Join-Path $repoPath 'SoulCombat\Saved'
$bridgeFile = Join-Path $repoPath 'Tools\tests\ue_test_bridge.py'
$editorExe = 'D:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$mcpPort = 8003
if (Get-NetTCPConnection -LocalPort $mcpPort -State Listen -ErrorAction SilentlyContinue) {
    throw "테스트 포트 $mcpPort 사용 중"
}
$testEditor = Start-Process -FilePath $editorExe -WindowStyle Hidden -PassThru -ArgumentList @(
    "`"$projectFile`"", '-culture=en', '-unattended',
    '-EnablePlugins=PythonScriptPlugin', "-ExecutePythonScript=`"$bridgeFile`"",
    '-ModelContextProtocolStartServer', "-ModelContextProtocolPort=$mcpPort"
)
```

`PythonScriptPlugin`은 이 프로세스에서만 활성화한다. uproject 설정에 추가하지 않는다. 브리지는 `EditorPythonScripting.set_keep_python_script_alive(True)`로 초기 스크립트 종료 후에도 살아 있다. `-unattended`는 숨겨진 에디터의 PIE가 백그라운드 3fps로 제한되는 조건을 피하기 위해 사용한다. 실제 테스트 로그의 tick rate도 확인한다.

`Saved/audit-bridge-ready.json`의 `pid`가 `$testEditor.Id`와 같고 `saved_dir`가 `$savedPath`인 것을 확인한 뒤 전달한다. 이전 실행의 준비 파일만으로 새 프로세스의 준비를 판정하지 않는다.

```powershell
Get-Content -LiteralPath (Join-Path $savedPath 'audit-bridge-ready.json') -Raw
python -X utf8 Tools/tests/ue_send_test.py Tools/tests/ue_actor_clock.py --saved-dir $savedPath --out actor-clock-request.json
```

MCP 포트는 에디터 구분용이다. `ue_send_test.py`는 HTTP가 아닌 해당 프로젝트의 `Saved/audit-request.json`을 사용한다. 다른 체크아웃의 브리지로 보낼 때는 **그 에디터의 Saved 절대 경로**를 `--saved-dir`로 지정한다. 같은 브리지에 요청은 한 번에 하나만 전달한다.

`--out`의 상대 이름은 대상 Saved 기준이며, Saved 밖의 응답 경로는 거부한다. `audit-request.json`, `audit-response.json`, `audit-bridge-ready.json`도 모두 대상 프로젝트 Saved에 둔다. Windows 파일 읽기와 `os.replace`가 충돌하면 최대 1초 동안 짧게 재시도하고, 계속 실패하면 요청 전달 오류 또는 에디터의 응답 기록 오류로 보고한다.

## 자체 PIE 시작 검사

다음 파일은 기존 PIE가 없는 상태에서 실행한다. 각 검사 파일이 PIE를 시작하고 끝에 종료한다. 브리지 응답의 `started=true`는 시작 접수이며, 검사 통과가 아니다. 결과 JSON의 `done`·`passed`와 실패 목록을 별도로 확인한 뒤 다음 검사를 실행한다.

| 파일 | 검사 | 프로젝트 Saved 결과 |
| --- | --- | --- |
| `ue_actor_clock.py` | 0.25 개별 배속에서 실제 몽타주 타격 위치와 피해 | `combat-actor-clock-result.json` |
| `ue_dungeon_recovery.py` | Mob1·Mob2·Boss 부분 진행 중 사망, 3초 부활, 자원·체크포인트·문·진행 유지 | `dungeon-recovery-result.json` |
| `ue_pause_menu.py` | 정지·계속하기·반복 열고 닫기와 UI 수명 | `pause-menu-result.json` |
| `ue_pause_buttons.py` | 실제 메뉴 버튼 델리게이트, 재시작·던전 입장·필드 복귀·종료 | `pause-buttons-result.json` |
| `ue_real_damage_feedback.py` | 실제 HP 감소량과 명중 피드백, 메뉴 진입 시 배율·FOV 복원 | `real-damage-feedback-result.json` |

`ue_dungeon_recovery.py`는 각 방을 새 던전 월드에서 검사하고, 부활 직후 재피해를 분리하려고 적 AI의 Think·Tick을 PIE에서만 정지한다. AI 접근이나 정상 플레이 난이도를 검증하는 용도로 쓰지 않는다.

## 실행 중인 PIE에서 사용하는 기존 세 회귀

**`ue_combat_regression.py`, `ue_timing_regression.py`, `ue_dungeon_flow.py`는 PIE를 자체 시작하지 않는다. 먼저 실제 PIE를 시작하고, 동일 브리지에 `ue_runtime.py`를 전달해야 한다.** `ue_runtime.py`에는 공통 실제 에셋 조회·회복·입력·위치 함수가 있다. 타이밍 검사는 공통 함수를 사용하므로 전투 검사 전체를 먼저 돌릴 필요가 없다.

| 파일 | 선행 상태 | 프로젝트 Saved 결과 |
| --- | --- | --- |
| `ue_combat_regression.py` | `L_CombatField` PIE, 플레이어 초기화, `ue_runtime.py` | `audit-combat-result.json` |
| `ue_timing_regression.py` | `L_CombatField` PIE, 플레이어 초기화, `ue_runtime.py` | `audit-timing-result.json` |
| `ue_dungeon_flow.py` | 실제 `GI.EnterDungeon`으로 이동한 `L_Dungeon_01` PIE, Start 방 초기화, `ue_runtime.py` | `audit-flow-result.json` |

PIE 시작용 임시 코드 파일을 Saved에 두고 전달하는 예시다.

```powershell
@'
import unreal
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
result = {"requested": True}
'@ | Set-Content -LiteralPath (Join-Path $savedPath 'ue-begin-play.py') -Encoding utf8
python -X utf8 Tools/tests/ue_send_test.py (Join-Path $savedPath 'ue-begin-play.py') --saved-dir $savedPath --out begin-play-request.json
```

PIE 월드 생성과 플레이어 초기화 후 공통 함수를 전달한다. 응답의 맵·Health·`world_seconds`를 확인한다. 아직 월드가 없으면 공통 함수 전달부터 다시 확인하며 회귀 검사를 중복 시작하지 않는다.

```powershell
python -X utf8 Tools/tests/ue_send_test.py Tools/tests/ue_runtime.py --saved-dir $savedPath --out runtime-ready.json
python -X utf8 Tools/tests/ue_send_test.py Tools/tests/ue_combat_regression.py --saved-dir $savedPath --out combat-request.json
Get-Content -LiteralPath (Join-Path $savedPath 'audit-combat-result.json') -Raw
```

결과 `done=true`와 `failures=[]`를 확인한 뒤 타이밍 검사를 전달한다. 전투·타이밍 검사는 PIE를 종료하지 않는다. 다른 자체 시작 검사로 넘어가기 전에 PIE를 종료한다.

```powershell
python -X utf8 Tools/tests/ue_send_test.py Tools/tests/ue_timing_regression.py --saved-dir $savedPath --out timing-request.json
```

던전 흐름은 공통 함수가 로드된 필드 PIE에서 실제 GI 입장을 요청한다.

```powershell
@'
unreal.GameplayStatics.get_game_instance(game_world()).call_method("EnterDungeon", args=("L_Dungeon_01",))
result = {"requested": True}
'@ | Set-Content -LiteralPath (Join-Path $savedPath 'ue-enter-dungeon.py') -Encoding utf8
python -X utf8 Tools/tests/ue_send_test.py (Join-Path $savedPath 'ue-enter-dungeon.py') --saved-dir $savedPath --out enter-dungeon-request.json
```

맵 이동이 완료된 후 `ue_runtime.py`를 다시 전달해 `L_Dungeon_01`과 월드 시간 0.5초 이후를 확인하고 흐름 검사를 시작한다. 흐름 검사는 방 진행과 클리어 후 필드 복귀까지 검사하며 PIE를 종료하지 않는다.

```powershell
python -X utf8 Tools/tests/ue_send_test.py Tools/tests/ue_runtime.py --saved-dir $savedPath --out dungeon-runtime-ready.json
python -X utf8 Tools/tests/ue_send_test.py Tools/tests/ue_dungeon_flow.py --saved-dir $savedPath --out dungeon-flow-request.json
```

## 종료와 실패 확인

실행 중인 PIE를 마치는 임시 코드다. 테스트 콜백이 실행 중이면 완료 결과부터 확인한다.

```powershell
@'
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
result = {"requested": True}
'@ | Set-Content -LiteralPath (Join-Path $savedPath 'ue-stop-play.py') -Encoding utf8
python -X utf8 Tools/tests/ue_send_test.py (Join-Path $savedPath 'ue-stop-play.py') --saved-dir $savedPath --out stop-play-request.json
```

에디터를 종료할 때는 **이 검사에서 시작한 PID·uproject·브리지 경로를 확인하고 테스트 에디터만 종료한다.** 실행 중인 UnrealEditor를 이름으로 일괄 종료하지 않는다. 테스트 에디터 창을 닫거나, PIE 종료 후 그 브리지에만 `unreal.EditorPythonScripting.set_keep_python_script_alive(False)`를 전달해 초기 스크립트의 종료 경로를 사용한다. 자동 프로세스 종료·자동 패키징은 이 폴더의 역할이 아니다.

송신기의 `--timeout`은 요청 접수 응답을 기다리는 시간이다. 타임아웃은 실행 취소가 아니다. `audit-response.json`의 요청 ID, 에디터 로그, 개별 결과 JSON과 PIE 상태를 확인한 뒤 재시도를 판단한다. 결과가 `done=false`인데 같은 검사를 다시 보내면 콜백이 겹칠 수 있다. 브리지의 `ok=true`와 검사 결과의 통과도 구분한다.

오디오 소스의 형식·경계·재현성 검사는 에디터 없이 `python -X utf8 Tools/tests/test_combat_audio.py`로 수행한다. 실제 키·화면·소리·손맛·Shipping 정상 플레이 확인은 위 자동 회귀와 별개의 사람 검증이다.

## 추적 가능한 순차 회귀 실행기

`ue_run_suite.py`는 기존 `SoulCombat/Saved/run_integrated_regressions.py`의 실행 순서와 PIE 경계를 유지한 호스트 CLI다. 저장소·`SoulCombat/Saved`·`ue_send_test.py` 경로는 실행기 파일의 실제 위치에서 계산하므로 다른 작업 체크아웃에서도 그 체크아웃의 실행기를 사용한다. 출력과 JSON은 UTF-8로 기록한다. 기존 Saved 실행기는 변경하지 않는다.

다음 두 모드는 에디터가 없어도 된다. 테스트 소스의 구문과 결과 파일 이름을 읽으며 에디터 호출·Saved 쓰기·잠금 생성을 하지 않는다. `--list`는 사용 가능한 14개 검사를 나열하고, `--plan-only`는 선택한 실행 계획과 기대 조건 수를 출력한다.

```powershell
python -X utf8 Tools/tests/ue_run_suite.py --list
python -X utf8 Tools/tests/ue_run_suite.py --plan-only
python -X utf8 Tools/tests/ue_run_suite.py --plan-only --extended
python -X utf8 Tools/tests/ue_run_suite.py --plan-only --suite feedback
```

실제 실행에는 위에서 준비한 테스트 전용 에디터·브리지와 `L_CombatField` 에디터 월드가 필요하고 기존 PIE가 없어야 한다. 시작 시 준비 파일의 `ready`·PID·Saved를 실제 브리지 응답과 대조하고, 후속 상태 조회에서도 같은 PID·Saved인지 확인한다. 다른 담당의 MCP·브리지 요청과 겹쳐 실행하지 않는다. 기존 Saved 실행기와 같은 `integrated-regressions.lock`을 사용하며 잠금이 있으면 시작하지 않는다.

```powershell
# 기본 11개 검사, 178조건
python -X utf8 Tools/tests/ue_run_suite.py

# 기본 11개 뒤 돌진6·독립 피드백57·AI17 추가: 14개, 258조건
python -X utf8 Tools/tests/ue_run_suite.py --extended

# 한 검사만 실행하거나 여러 검사를 지정한 순서로 실행
python -X utf8 Tools/tests/ue_run_suite.py --suite charge-sweep
python -X utf8 Tools/tests/ue_run_suite.py --suite feedback --suite ai
```

`--suite`는 기본 검사를 제외하고 지정한 검사만 실행한다. `--extended`와 함께 쓰거나 같은 검사를 중복 지정하면 거부한다. 기본 순서는 ActorClock1 → 실제 피해17 → 정지 메뉴8 → 메뉴 버튼9 → 던전 복구39 → 스킬 UI16 → 플레이어 타이밍14 → 적 타이밍12 → 전투37 → 기존 타이밍3 → 던전 흐름22다. 전투37·기존 타이밍3은 같은 필드 PIE와 `ue_runtime.py`를 공유한다. 던전 흐름은 새 필드 PIE에서 실제 `GI.EnterDungeon`으로 이동한 뒤 공통 런타임을 준비한다.

추가 `charge-sweep`와 `ai`는 테스트 파일이 자체 PIE 시작·종료를 맡으므로 실행기가 중복 시작하지 않는다. `feedback`은 실행기가 새 필드 PIE를 준비한 뒤 `Tools/test_combat_feedback.py`의 정의를 로드하고 `start_feedback_tests()`를 호출한다. 각 검사의 완료 결과와 PIE 종료까지 확인해야 다음 검사를 보낸다.

결과는 기존처럼 `SoulCombat/Saved/integrated-regressions.json`과 각 검사의 결과 JSON에 둔다. 이전 결과는 새 실행이 덮어쓰기 전에 `Saved/integrated-history/<UTC시각-호스트PID>/`에 복사한다. 새 실행기의 최종 통과는 `done=true`, `passed=true`, `status="passed"`, `condition_count == expected_conditions`로 판정한다. 각 suite도 기대 조건 수와 실제 `cases`/`checks` 수가 같고 모든 행이 통과해야 한다. ActorClock은 배열 없는 단일 `done`/`passed` 판정을 1조건으로 센다. 독립 피드백 파일은 `passed` 필드 없이 `done=true`, `failures=[]`, 모든 `cases.passed=true`로 완료를 판정한다.

브리지의 `ok=true`·검사의 `started=true`는 접수 확인이다. 실패 행·비어 있지 않은 실패 목록·오류를 발견하거나 최종 판정·조건 수가 다르면 다음 검사를 즉시 중단한다. 브리지 응답은 20초, 월드 준비·종료는 60초, 콜백 결과는 240초까지 기다리며 15초 간격으로 진행 상태를 출력한다. 실패·시간 초과 시 실행기가 PIE·콜백을 자동 취소하지 않으므로 요청 ID·개별 결과·현재 상태를 먼저 확인하고 재실행한다. 에셋 저장·에디터 종료·빌드·패키징은 수행하지 않는다.

에디터 없는 호스트 검증은 다음 명령으로 실행한다. 실패 판정, 기본 순서·조건 수, 추가 검사 생명주기, PID·Saved 불일치, 무호출 계획, 이전 결과 보존을 검사한다.

```powershell
python -X utf8 Tools/tests/test_ue_run_suite.py
```

2026-09-30 검증 범위: 기존 Saved 실행기를 통한 전체 11개·178조건과 별도 돌진6·독립 피드백57·AI17은 실제 완료 결과가 통과했다. 새 `ue_run_suite.py`는 호스트 단위 검사14개, AST와 `--list`/`--plan-only`를 검증했다. 이후 새 실행기를 실제 에디터 브리지에 연결한 `charge-sweep` 단독 검사도6조건 통과했다(`Saved/runner-charge-integration.json`). 이 연결 확인에서는 기존 전체178조건 결과를 보존하도록 호스트 로더에서 출력 파일만 별도로 지정했다. 새 실행기를 통한 기본 전체·확장 전체 묶음은 아직 실행하지 않았다. 전체 게임 회귀, 새 실행기의 호스트 검사, 선택 검사 연결 확인을 각각 구분한다.
