# 명중 피드백 제작 기록 — 담당 B

2026-09-30, 기준 `81a750fed986bd080960a5246d29131f6cdd513e`, 브랜치 `codex/combat-feedback`.
작업 사본은 `D:/Project/UE/AstraTest/_workers/combat-feedback`, 프로젝트는 `SoulCombat/SoulCombat.uproject`, MCP 8002, 에디터 PID 12548이다. `audit-bridge-ready.json`의 실제 PID와 로그를 대조했다.

## 변경 범위와 통합 계약

새 에셋 네 개와 담당 테스트만 만든다. 원본 `AC_CombatComponent`, `BP_SCPlayerController`, 캐릭터, ini와 음원은 수정하지 않았다. 추가 C++·외부 다운로드·Git push도 없다.

| 에셋 | 경로 | 역할 |
|---|---|---|
| `AC_CombatFeedback` | `/Game/SoulCombat/Components/AC_CombatFeedback` | 컨트롤러 Tick에서 명중 연출과 실제 시간 복원 관리 |
| `M_SC_HitFlash` | `/Game/SoulCombat/Materials/M_SC_HitFlash` | 반투명 Unlit 오버레이, 색·불투명도 파라미터 |
| `WBP_DamageNumber` | `/Game/SoulCombat/UI/WBP_DamageNumber` | 실제 피해량을 표시하고 가드를 파란색으로 구분 |
| `BP_DamageNumber` | `/Game/SoulCombat/Combat/BP_DamageNumber` | 화면 공간 WidgetComponent, 상승·투명도·실제 시간 수명 |

통합 담당은 `BP_SCPlayerController`의 SCS에 `/Game/SoulCombat/Components/AC_CombatFeedback.AC_CombatFeedback_C`를 ActorComponent로 하나 추가하고 다음 공개 함수에 실제 HP 감소량을 보낸다.

```text
ReportHit(Attacker: Actor, Target: Actor, Damage: float, bGuarded: bool)
ResetAllFeedback()
```

피해0은 새 연출을 만들지 않는다. `Damage`는 요청 피해나 초기 `IncomingDamage`가 아니라 통합 측에서 측정한 `max(0, HealthBefore - HealthAfter)`다. 기본 에셋의 `bEnableHitstop=false`를 유지했다. 통합 담당이 공격·콤보의 애니메이션 시간 전환을 검증한 다음 켠다. 이 컴포넌트는 GlobalTimeDilation, 비용, 쿨다운, 경직 타이머를 변경하지 않는다.

실제 표시와 수명을 읽을 때 쓰는 프로퍼티는 다음과 같다. 테스트 전용 상태 변수는 추가하지 않았다.

| 소유 | 프로퍼티 | 의미·기본값 |
|---|---|---|
| `WBP_DamageNumber` | `DamageValue`, `bGuardedValue` | 실제 표시 피해 float, 가드 bool |
| `BP_DamageNumber` | `Lifetime`, `RiseDistance` | 실제 시간 수명 0.7초, 상승 거리 65 |
| `AC_CombatFeedback` | `DamageNumberLifetime`, `MaxDamageNumbers` | 숫자 생성 수명 0.7초, 동시 숫자 상한 24 |
| `AC_CombatFeedback` | `DamageActors` | 활성 숫자 액터 참조 배열 |
| `AC_CombatFeedback` | `bEnableHitstop` | 반환 기본값 false |

숫자만 따로 켜는 bool은 없다. 양수 피해에서 생성한다. 숫자 액터의 `get_component_by_class(unreal.WidgetComponent).get_user_widget_object()`로 표시 위젯을 읽을 수 있다.

## 수명·복원 설계

- 최초 배율을 대상별로 저장하고 원래 배율의 0.06을 적용한다. 같은 대상의 추가 명중은 최초 값을 덮어쓰지 않으며 실제 종료 시각을 연장한다. PC 자체는 느리게 하지 않는다.
- 컨트롤러 컴포넌트의 정상 Tick와 `GetRealTimeSeconds`를 쓴다. 컴포넌트와 숫자 액터는 일시정지 중 Tick을 허용한다.
- 만료, `State.Dead`, 대상 파괴, 외부 배율 변경을 확인한다. 현재 값이 마지막 적용값과 같을 때만 최초 값으로 복원하고 관련 Map을 지운다. 외부 값은 보존한다.
- 메시마다 최초 OverlayMaterial을 보관한다. 현재 재질이 피격 재질인 경우에만 복원한다. 기존 메시의 기본 Material은 바꾸지 않는다.
- FOV는 실제 초기값을 보관한다. 반복 타격 세기는 최대값을 사용하고 합산하지 않는다. 실제 시간 0.2초에 제곱 곡선으로 줄이며, 카메라 전환·외부 FOV 변경·종료 시 소유한 변경만 복원한다.
- `EndPlay → ResetAllFeedback`은 배율·오버레이·FOV를 정리하고 모든 활성 숫자를 파괴한다. 통합 PauseMenu에서도 이 함수를 호출할 수 있다.

## 테스트와 관찰 근거

`Tools/test_combat_feedback.py`를 먼저 작성했다. 새 클래스가 없는 상태에서 `require_feedback_contract()`가 실패한 결과는 `SoulCombat/Saved/feedback-contract-red.json`이다. 실제 PIE에서는 기존 PC에 테스트 컴포넌트를 붙이고, 기존 `ApplyHit`와 GE로 감소한 실제 HP를 측정해 전달했다. 파일을 실행하면 함수들이 정의되며, PIE에서 `start_feedback_tests()`를 호출해 비동기 검사를 시작한다.

기존 검증 브리지에서 실행한 명령은 다음과 같다.

```powershell
python -X utf8 SoulCombat/Saved/audit_send.py SoulCombat/Saved/feedback_start_pie.py --out SoulCombat/Saved/feedback-pie-request.json --timeout 120
python -X utf8 SoulCombat/Saved/audit_send.py SoulCombat/Saved/feedback_run_tests.py --out SoulCombat/Saved/feedback-test-started.json --timeout 120
```

시작 스크립트는 실제 PIE 시작을 요청한다. 검사 스크립트의 핵심 호출은 다음과 같다.

```python
exec(compile(open(os.path.join(unreal.Paths.project_dir(), '..', 'Tools', 'test_combat_feedback.py'), encoding='utf-8-sig').read(), 'test_combat_feedback.py', 'exec'), globals())
FEEDBACK_TESTS = start_feedback_tests()
```

최종 `SoulCombat/Saved/combat-feedback-tests.json`은 `done=true`, **57/57 통과**, 실패 배열0, 예외 null이다. 확인한 항목은 실제 GE 피해50, 피해0, 가드 피해10·표시 상태, 숫자 수명·24개 상한, FOV 합산 방지, 히트스톱 적용, 재명중·만료·외부 변경 보존, 사망·부활, 일시정지·전역0.1배, 대상 파괴·EndPlay 정리다. 최초 배율 .75/1.2에서 실제 적용 .045/.072와 복원, FOV97 복원을 확인했다. 통합 원본에서 자동으로 전달하는 경로는 통합 담당의 별도 회귀 대상이다.

초기 실행에서 `bEnableHitstop`의 `set_editor_property` 기본 변경 알림이 생성 스크립트를 재실행해 동적으로 추가한 컴포넌트를 파괴했다. 그 상태의 호출은 히트스톱 적용에 실패했다. 같은 실제 PIE PC에서 별도 대조한 `feedback-notify-control.json`은 기본 알림의 유효성 true→false, `NEVER` 알림의 유효성 true·동일 객체·Owner=PC를 기록한다. 엔진 `ActorComponent.cpp:1444,1470`과 `PyWrapperObject.cpp:863,1133`도 이 경로를 뒷받침한다. 테스트의 런타임 설정 변경은 `notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER`로 교정했다. 게임 BP의 Set 변수 실행은 이런 에디터 변경 알림을 요청하지 않는다.

제작 도구에서 반환 노드를 지우면 출력 시그니처가 사라지는 문제도 발견했다. `IsActorDead`의 명시 반환 핀과 세 경로를 복구하고 호출 노드를 다시 만들었으며, 실제 사망·부활 검사까지 통과했다. 히트스톱 유효성 가드에는 명시 ReturnNode를 남겼다. 임시 추적 PrintString은 최종 에셋에서 제거했다.

## 최종 정적 검증·저장

세 BP 모두 `warnings_as_errors=true` MCP 컴파일이 성공했다. 예시는 다음 명령이며, 같은 방식으로 숫자 BP와 위젯도 검사했다.

```powershell
python -X utf8 Tools/mcp_http.py --port 8002 --out SoulCombat/Saved/compile-AC_CombatFeedback.json call editor_toolset.toolsets.blueprint.BlueprintTools compile_blueprint '@SoulCombat/Saved/compile-AC_CombatFeedback.args.json'
python -X utf8 Tools/mcp_http.py --port 8002 --out SoulCombat/Saved/feedback-assets-saved.json call editor_toolset.toolsets.asset.AssetTools save_assets '@SoulCombat/Saved/feedback-save.args.json'
```

컴파일 응답은 세 개 모두 `returnValue:null`, 네 경로를 명시한 저장 응답은 `returnValue:true`다. `feedback-final-state.json`은 PIE false, dirty 콘텐츠0·맵0, `bEnableHitstop=false`, 일시정지 Tick 허용을 확인한다. 재질도 재컴파일했다.

20개 그래프를 왼쪽→오른쪽으로 정리하고 한국어 주석과 상세 설명을 넣었다. `feedback-layout-before.json`, `feedback-layout-after.json`, `feedback-annotated.json`에서 정리 전후 노드·연결·전체 핀 값 동일20/20, 추정 노드 겹침0을 확인했다. 현재 UE5.8의 `BlueprintGraphEditor.AddCommentNode`를 직접 사용했으며 Slate·클립보드를 쓰지 않았다. 현재 엔진에는 이 API가 있으므로 기존 쿡북의 주석 도구 제약은 모든 버전에 적용되지 않는다.

## 통합 뒤 남는 확인

통합 담당이 실제 `ApplyHit → PC → ReportHit` 경로, 기본 히트스톱 활성화, 공격·콤보 타이밍을 새 PIE에서 검증한다. 기존 VFX·새 오버레이·숫자·FOV·통합 음향의 조합, Nanite 정적 메시의 실제 화면, 손맛과 화면 가독성은 사람/화면 검증 대상이다. 독립 수치 검사로 이 항목을 완료 표시하지 않는다. PC·공통 Combat·원본 UI·Audio 통합이나 Shipping 빌드는 담당 B 범위에서 수행하지 않았다.
