"""단독 테스트 에디터의 브리지로 통합 회귀를 순차 실행하는 호스트 실행기.

실행: python -X utf8 Tools/tests/ue_run_suite.py
목록/무호출 계획: --list / --plan-only, 추가 검사: --extended
단독 선택: --suite charge-sweep --suite feedback --suite ai
기본 11개·178조건의 순서와 PIE 경계를 유지한다. 추가 6/57/17은 계약
기대값이며 이 파일의 존재나 계획 출력은 해당 검사의 통과 증거가 아니다.
기존 결과는 Saved/integrated-history에 복사해 보존한다.
Tools/tests/ue_test_bridge.py가 현재 프로젝트에서 준비되어 있어야 한다.
기존 PIE가 있으면 시작하지 않는다. 검사 실패/타임아웃에는 다음 검사와
자동 정리를 중단해 현재 PIE·콜백을 검토할 수 있게 한다. 에셋 저장,
에디터 종료, 빌드·패키징은 수행하지 않는다.
"""
import argparse
import ast
from collections import namedtuple
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SAVED = REPO / "SoulCombat" / "Saved"
TESTS = REPO / "Tools" / "tests"
SENDER = TESTS / "ue_send_test.py"
OUTPUT = SAVED / "integrated-regressions.json"
LOCK = SAVED / "integrated-regressions.lock"
CALLBACK_TIMEOUT = 240.0
WORLD_TIMEOUT = 60.0
BRIDGE_TIMEOUT = 20.0
PROGRESS_INTERVAL = 15.0
# 기존 완료 결과의 실제 조건 수를 계약으로 유지한다. 실행 통과와 구분한다.
Suite = namedtuple("Suite", "identifier source lifecycle expected_count entrypoint", defaults=[None])
BASE_SUITES = (
    Suite("actor-clock", TESTS / "ue_actor_clock.py", "self_start", 1),
    Suite("real-damage", TESTS / "ue_real_damage_feedback.py", "self_start", 17),
    Suite("pause-menu", TESTS / "ue_pause_menu.py", "self_start", 8),
    Suite("pause-buttons", TESTS / "ue_pause_buttons.py", "self_start", 9),
    Suite("dungeon-recovery", TESTS / "ue_dungeon_recovery.py", "self_start", 39),
    Suite("skill-ui", TESTS / "ue_skill_ui.py", "self_start", 16),
    Suite("player-timing", TESTS / "combat_timing_pie.py", "field", 14),
    Suite("enemy-timing", TESTS / "combat_enemy_timing_pie.py", "field", 12),
    Suite("combat", TESTS / "ue_combat_regression.py", "runtime_field", 37),
    Suite("timing", TESTS / "ue_timing_regression.py", "runtime_field", 3),
    Suite("dungeon-flow", TESTS / "ue_dungeon_flow.py", "dungeon", 22),
)
EXTRA_SUITES = (
    Suite("charge-sweep", TESTS / "combat_charge_sweep_pie.py", "self_start", 6),
    Suite("feedback", REPO / "Tools" / "test_combat_feedback.py", "field", 57, "start_feedback_tests"),
    Suite("ai", TESTS / "ue_ai_autonomy.py", "self_start", 17),
)


def select_suites(extended=False, identifiers=None):
    if identifiers:
        if extended:
            raise ValueError("--extended와 --suite를 함께 지정하지 않는다.")
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("같은 suite를 중복 지정하지 않는다.")
        catalog = {s.identifier: s for s in BASE_SUITES + EXTRA_SUITES}
        return tuple(catalog[name] for name in identifiers)
    return BASE_SUITES + EXTRA_SUITES if extended else BASE_SUITES


def condition_count(value):
    for key in ("cases", "checks"):
        if key in value:
            rows = value[key]
            if not isinstance(rows, list):
                raise RuntimeError(key + "가 배열이 아니다.")
            return len(rows)
    # ActorClock은 배열 없이 단일 done/passed 판정을 기록한다.
    return 1 if value.get("done") is True and value.get("passed") is True else 0


def validate_editor_state(value, expected_pid):
    if value.get("pid") != expected_pid:
        raise RuntimeError("준비 파일과 실제 브리지 PID가 다르다: " + str(value))
    if Path(value.get("saved_dir", "")).resolve() != SAVED:
        raise RuntimeError("응답한 에디터의 Saved가 다르다: " + str(value))


def build_plan(suites):
    for code in (QUERY_CODE, BEGIN_CODE, END_CODE, DUNGEON_CODE):
        ast.parse(code)
    entries = []
    for suite in suites:
        name = result_name(suite.source)
        entries.append({"id": suite.identifier, "source": str(suite.source),
                        "output": str(SAVED / name), "lifecycle": suite.lifecycle,
                        "expected_count": suite.expected_count, "entrypoint": suite.entrypoint})
    return {"mode": "plan_only", "editor_calls_performed": False,
            "saved_writes_performed": False, "repo": str(REPO), "saved": str(SAVED),
            "sender": str(SENDER), "output": str(OUTPUT), "lock": str(LOCK),
            "expected_conditions": sum(s.expected_count for s in suites),
            "callback_timeout_seconds": CALLBACK_TIMEOUT, "world_timeout_seconds": WORLD_TIMEOUT,
            "bridge_timeout_seconds": BRIDGE_TIMEOUT, "progress_interval_seconds": PROGRESS_INTERVAL,
            "suites": entries}


QUERY_CODE = '''import os
import unreal
_ir_editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
_ir_world = _ir_editor.get_game_world()
_ir_editor_world = _ir_editor.get_editor_world()
result = {
    "pid": os.getpid(),
    "saved_dir": unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()),
    "editor_world": _ir_editor_world.get_name() if _ir_editor_world else None,
    "pie": _ir_world is not None,
    "world_name": _ir_world.get_name() if _ir_world else None,
    "world_path": _ir_world.get_path_name() if _ir_world else None,
    "world_seconds": unreal.GameplayStatics.get_time_seconds(_ir_world) if _ir_world else None,
    "player_ready": unreal.GameplayStatics.get_player_pawn(_ir_world, 0) is not None if _ir_world else False,
    "controller_ready": unreal.GameplayStatics.get_player_controller(_ir_world, 0) is not None if _ir_world else False,
    "paused": unreal.GameplayStatics.is_game_paused(_ir_world) if _ir_world else False,
}
'''
BEGIN_CODE = '''import unreal
_ir_editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if _ir_editor.get_game_world() is not None:
    raise RuntimeError("이미 PIE가 실행 중이다.")
if _ir_editor.get_editor_world().get_name() != "L_CombatField":
    raise RuntimeError("에디터의 L_CombatField에서 시작해야 한다.")
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
result = {"requested": True}
'''
END_CODE = '''import unreal
_ir_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if _ir_world is not None:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
result = {"requested": _ir_world is not None}
'''
DUNGEON_CODE = '''import unreal
_ir_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if _ir_world is None or _ir_world.get_name() != "L_CombatField":
    raise RuntimeError("준비된 필드 PIE에서 던전에 입장해야 한다.")
_ir_source_world_path = _ir_world.get_path_name()
unreal.GameplayStatics.get_game_instance(_ir_world).call_method("EnterDungeon", args=(unreal.Name("L_Dungeon_01"),))
result = {"requested": True, "source_world_path": _ir_source_world_path}
'''


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def result_name(source):
    """실제 테스트 소스의 결과 JSON 리터럴을 읽는다."""
    tree = ast.parse(source.read_text(encoding="utf-8-sig"), filename=str(source))
    names = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
             and isinstance(n.value, str) and n.value.endswith(("-result.json", "-tests.json"))
             and Path(n.value).name == n.value}
    if len(names) != 1:
        raise RuntimeError(f"결과 파일 이름을 하나로 확인할 수 없다: {source}: {sorted(names)}")
    return names.pop()


def failures(value):
    if value.get("error"):
        return [str(value["error"])]
    if "failures" in value:
        if not isinstance(value["failures"], list):
            return ["failures가 배열이 아니다."]
        if value["failures"]:
            return value["failures"]
    bad = []
    for key in ("cases", "checks"):
        rows = value.get(key, [])
        if not isinstance(rows, list):
            bad.append(key + "가 배열이 아니다.")
            continue
        for row in rows:
            if not isinstance(row, dict) or row.get("passed") is not True:
                bad.append(row)
    if value.get("done") is True:
        if "passed" in value and value["passed"] is not True:
            bad.append("passed가 true가 아니다.")
        if "passed" not in value and "failures" not in value:
            bad.append("최종 결과에 passed/failures 판정이 없다.")
    return bad


class Runner:
    def __init__(self, suites):
        self.suites = suites
        self.editor_pid = None
        self.archive_dir = SAVED / "integrated-history" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + str(os.getpid()))
        self.archived = set()
        self.start = time.monotonic()
        self.last_progress = self.start
        self.report = {"started_utc": utc_now(), "status": "running", "done": False,
                       "passed": False, "repo": str(REPO), "saved": str(SAVED),
                       "selected_suites": [s.identifier for s in suites],
                       "expected_conditions": sum(s.expected_count for s in suites),
                       "archive_dir": str(self.archive_dir),
                       "callback_timeout_seconds": CALLBACK_TIMEOUT,
                       "progress_interval_seconds": PROGRESS_INTERVAL,
                       "suites": [], "lifecycle": [], "error": None}

    def log(self, message):
        print(f"[{time.monotonic() - self.start:6.1f}s] {message}", flush=True)
        self.last_progress = time.monotonic()

    def progress(self, message):
        if time.monotonic() - self.last_progress >= PROGRESS_INTERVAL:
            self.log(message)

    def archive(self, path):
        if path in self.archived:
            return
        if path.is_file():
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, self.archive_dir / path.name)
        self.archived.add(path)

    def save(self):
        self.archive(OUTPUT)
        temporary = OUTPUT.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.report, ensure_ascii=False, indent=2), encoding="utf-8")
        deadline = time.monotonic() + 1.0
        while True:
            try:
                os.replace(temporary, OUTPUT)
                return
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.02)

    def send(self, path, label):
        path = Path(path).resolve()
        if path.parent not in (TESTS.resolve(), (REPO / "Tools").resolve(), SAVED):
            raise RuntimeError("프로젝트 Tools 또는 Saved의 로컬 스크립트만 전달한다: " + str(path))
        command = [sys.executable, "-X", "utf8", str(SENDER), str(path),
                   "--saved-dir", str(SAVED), "--timeout", str(BRIDGE_TIMEOUT)]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, encoding="utf-8")
        deadline = time.monotonic() + BRIDGE_TIMEOUT + 5.0
        while True:
            try:
                stdout, stderr = process.communicate(timeout=0.25)
                break
            except subprocess.TimeoutExpired:
                self.progress(label + " 브리지 응답 대기")
                if time.monotonic() >= deadline:
                    process.kill()
                    stdout, stderr = process.communicate()
                    raise RuntimeError(label + " 송신기 시간 초과. 에디터 요청은 취소되지 않았다.\n" + stdout + stderr)
        try:
            response = json.loads(stdout)
        except ValueError as error:
            raise RuntimeError(label + " 송신기 JSON 응답을 읽지 못했다.\n" + stdout + stderr) from error
        if process.returncode != 0 or not isinstance(response, dict) or response.get("ok") is not True:
            raise RuntimeError(label + " 브리지 실패:\n" + json.dumps(response, ensure_ascii=False) + "\n" + stderr)
        return response

    def inline(self, code, label):
        ast.parse(code)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".py",
                                         prefix="integrated-request-", dir=SAVED, delete=False) as stream:
            stream.write(code)
            path = Path(stream.name)
        try:
            return self.send(path, label)["result"]
        finally:
            path.unlink(missing_ok=True)

    def query(self):
        value = self.inline(QUERY_CODE, "PIE 상태 조회")
        if not isinstance(value, dict):
            raise RuntimeError("PIE 상태 응답이 객체가 아니다.")
        validate_editor_state(value, self.editor_pid)
        return value

    def wait_world(self, expected=None, changed_from=None):
        deadline = time.monotonic() + WORLD_TIMEOUT
        while time.monotonic() < deadline:
            state = self.query()
            ready = not state["pie"] if expected is None else (
                state["pie"] and state["world_name"] == expected
                and state["world_seconds"] >= 0.5 and state["player_ready"]
                and state["controller_ready"] and not state["paused"]
                and (changed_from is None or state["world_path"] != changed_from))
            if ready:
                self.report["lifecycle"].append({"at_utc": utc_now(), "expected": expected,
                                                  "changed_from": changed_from, "state": state})
                self.save()
                return state
            self.progress(f"월드 준비 대기: {expected or 'PIE 종료'}, 현재 {state}")
            time.sleep(0.25)
        raise RuntimeError("월드 준비/종료 시간 초과: " + str(state))

    def require_stopped(self):
        state = self.query()
        if state["pie"]:
            raise RuntimeError("이전 PIE/콜백의 완료·종료를 먼저 확인한다: " + str(state))
        if state["editor_world"] != "L_CombatField":
            raise RuntimeError("L_CombatField 에디터 월드가 필요하다: " + str(state))

    def begin(self):
        self.require_stopped()
        self.log("새 필드 PIE 시작, 월드 시간0.5초·플레이어·컨트롤러 준비 대기")
        self.inline(BEGIN_CODE, "PIE 시작")
        self.wait_world("L_CombatField")

    def end(self):
        self.inline(END_CODE, "PIE 종료")
        self.wait_world()
        self.log("PIE 종료 확인")

    def runtime(self, expected):
        response = self.send(TESTS / "ue_runtime.py", "공통 런타임 초기화")
        snapshot = response.get("result", {}).get("snapshot", {})
        if snapshot.get("map") != expected or snapshot.get("world_seconds", -1) < 0.5:
            raise RuntimeError("ue_runtime의 맵/준비 시간이 다르다: " + str(snapshot))
        self.report["lifecycle"].append({"at_utc": utc_now(), "runtime": snapshot})
        self.save()

    def suite(self, spec):
        source = spec.source
        filename = source.name
        expected_count = spec.expected_count
        output = SAVED / result_name(source)
        self.query()  # 에디터 재시작으로 브리지 PID가 바뀌면 다음 검사 전에 중단한다.
        self.archive(output)
        output.unlink(missing_ok=True)
        started = time.monotonic()
        row = {"id": spec.identifier, "source": str(source), "output": str(output), "started_utc": utc_now(),
               "status": "running", "expected_count": expected_count, "result": None}
        self.report["suites"].append(row)
        self.save()
        self.log("검사 시작: " + filename)
        try:
            row["bridge_response"] = self.send(source, filename)
            accepted = row["bridge_response"].get("result")
            if spec.entrypoint:
                # 이 소스는 정의만 로드한다. 새 PIE에 검사 객체를 만들고 강한 참조를 유지한다.
                accepted = self.inline("_ir_feedback_test = " + spec.entrypoint + "()\nresult = {\"started\": True}\n", filename + " 검사 객체 생성")
                row["entrypoint_response"] = accepted
            if not isinstance(accepted, dict) or accepted.get("started") is not True:
                raise RuntimeError(filename + " started=true 접수를 확인하지 못했다.")
            deadline = started + CALLBACK_TIMEOUT
            while time.monotonic() < deadline:
                value = read_json(output)
                if value is not None:
                    row["result"] = value
                    bad = failures(value)
                    if bad:
                        raise RuntimeError(filename + " 검사 실패: " + json.dumps(bad, ensure_ascii=False))
                    if value.get("done") is True:
                        if condition_count(value) != expected_count:
                            raise RuntimeError(f"{filename} 검사 수가 다르다: {condition_count(value)}/{expected_count}")
                        row.update(status="passed", elapsed_seconds=time.monotonic() - started,
                                   finished_utc=utc_now())
                        self.save()
                        count = condition_count(value)
                        self.log(f"검사 완료: {filename}, {count or 1}개 통과")
                        return
                count = condition_count(value) if value else 0
                self.progress(f"콜백 대기: {filename}, 완료 검사 {count}개, {time.monotonic() - started:.1f}초")
                time.sleep(0.25)
            raise RuntimeError(filename + " 콜백240초 시간 초과. 콜백/PIE는 자동 취소하지 않는다.")
        except Exception:
            row.update(status="failed", error=traceback.format_exc(),
                       elapsed_seconds=time.monotonic() - started, finished_utc=utc_now())
            self.save()
            raise

    def run(self):
        self.save()
        ready = read_json(SAVED / "audit-bridge-ready.json")
        if not ready or ready.get("ready") is not True:
            raise RuntimeError("현재 에디터 브리지의 준비 파일이 없다.")
        self.editor_pid = ready.get("pid")
        if type(self.editor_pid) is not int or self.editor_pid <= 0 or Path(ready.get("saved_dir", "")).resolve() != SAVED:
            raise RuntimeError("준비 파일의 PID/Saved가 올바르지 않다.")
        state = self.query()
        self.report["editor_pid"] = state["pid"]
        self.require_stopped()
        for index, spec in enumerate(self.suites):
            previous = self.suites[index - 1].lifecycle if index else None
            following = self.suites[index + 1].lifecycle if index + 1 < len(self.suites) else None
            if spec.lifecycle == "self_start":
                self.require_stopped()
                self.suite(spec)
                self.wait_world()
            elif spec.lifecycle == "field":
                self.begin()
                self.suite(spec)
                self.end()
            elif spec.lifecycle == "runtime_field":
                # 기본 전투37 → 타이밍3은 기존과 같은 PIE와 공통 런타임을 공유한다.
                if previous != "runtime_field":
                    self.begin()
                    self.runtime("L_CombatField")
                self.suite(spec)
                if following != "runtime_field":
                    self.end()
            elif spec.lifecycle == "dungeon":
                self.begin()
                self.log("GI.EnterDungeon으로 실제 던전 월드 전환 요청")
                travel = self.inline(DUNGEON_CODE, "던전 입장")
                self.wait_world("L_Dungeon_01", changed_from=travel["source_world_path"])
                self.runtime("L_Dungeon_01")
                self.suite(spec)
                self.end()
            else:
                raise RuntimeError("알 수 없는 suite 생명주기: " + spec.lifecycle)
        total = sum(condition_count(row["result"]) for row in self.report["suites"])
        if total != self.report["expected_conditions"]:
            raise RuntimeError("최종 조건 수가 계약과 다르다: " + str(total))
        self.report.update(status="passed", done=True, passed=True, condition_count=total,
                           finished_utc=utc_now(), elapsed_seconds=time.monotonic() - self.start)
        self.save()
        self.log("통합 회귀 모두 통과: " + str(OUTPUT))


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="사용 가능한 검사를 나열한다. 에디터 호출·Saved 쓰기 없음")
    parser.add_argument("--plan-only", action="store_true", help="소스 구문·결과 경로·실행 계획만 확인한다. 에디터 호출·Saved 쓰기 없음")
    parser.add_argument("--extended", action="store_true", help="기본 11개 뒤 돌진6·독립 피드백57·AI17 추가")
    parser.add_argument("--suite", action="append", choices=[s.identifier for s in BASE_SUITES + EXTRA_SUITES], help="선택한 검사만 지정 순서대로 실행. 반복 지정 가능")
    args = parser.parse_args(argv)
    try:
        suites = select_suites(args.extended, args.suite)
        plan = build_plan(BASE_SUITES + EXTRA_SUITES if args.list else suites)
    except (ValueError, RuntimeError, OSError, SyntaxError) as error:
        parser.error(str(error))
    if args.list or args.plan_only:
        if args.list:
            plan["mode"] = "list"
        print(json.dumps(plan, ensure_ascii=False, indent=2), flush=True)
        return 0
    if not SAVED.is_dir():
        print("프로젝트 Saved가 없다: " + str(SAVED), flush=True)
        return 1
    if not SENDER.is_file():
        print("송신기가 없다: " + str(SENDER), flush=True)
        return 1
    try:
        with LOCK.open("x", encoding="utf-8") as stream:
            json.dump({"host_pid": os.getpid(), "started_utc": utc_now()}, stream)
    except FileExistsError:
        print("다른 실행기 또는 이전 실행의 잠금이 있다. 실제 프로세스·PIE를 확인한다: " + str(LOCK), flush=True)
        return 1
    runner = Runner(suites)
    try:
        runner.run()
        return 0
    except (Exception, KeyboardInterrupt) as error:
        runner.report.update(status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
                             done=True, passed=False, error=traceback.format_exc(),
                             finished_utc=utc_now(), elapsed_seconds=time.monotonic() - runner.start)
        runner.save()
        runner.log("실행 중단. 다음 검사는 보내지 않는다. 현재 PIE/콜백과 결과를 검토한다: " + str(OUTPUT))
        print(runner.report["error"], flush=True)
        return 130 if isinstance(error, KeyboardInterrupt) else 1
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
