"""에디터 없이 회귀 실행기의 실패 판정·경로·계획 모드를 검사한다."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).with_name("ue_run_suite.py")
SPEC = importlib.util.spec_from_file_location("ue_run_suite", SOURCE)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RunnerContractTests(unittest.TestCase):
    def test_default_order_and_verified_condition_total(self):
        suites = runner.select_suites()
        self.assertEqual([s.identifier for s in suites], [
            "actor-clock", "real-damage", "pause-menu", "pause-buttons",
            "dungeon-recovery", "skill-ui", "player-timing", "enemy-timing",
            "combat", "timing", "dungeon-flow",
        ])
        self.assertEqual(sum(s.expected_count for s in suites), 178)
        self.assertEqual([s.lifecycle for s in suites[8:10]], ["runtime_field", "runtime_field"])

    def test_extended_sources_keep_their_actual_lifecycle(self):
        suites = runner.select_suites(extended=True)
        self.assertEqual([(s.identifier, s.lifecycle, s.expected_count) for s in suites[-3:]], [
            ("charge-sweep", "self_start", 6),
            ("feedback", "field", 57),
            ("ai", "self_start", 17),
        ])
        self.assertEqual(suites[-2].source, runner.REPO / "Tools" / "test_combat_feedback.py")
        self.assertEqual(suites[-2].entrypoint, "start_feedback_tests")

    def test_failed_partial_row_stops_before_done(self):
        self.assertTrue(runner.failures({"done": False, "checks": [{"passed": False}]}))

    def test_final_passed_false_cannot_hide_behind_empty_failures(self):
        self.assertTrue(runner.failures({"done": True, "passed": False, "failures": []}))

    def test_missing_final_verdict_is_rejected(self):
        self.assertTrue(runner.failures({"done": True, "checks": [{"passed": True}]}))

    def test_feedback_result_can_use_failures_verdict(self):
        self.assertEqual(runner.failures({"done": True, "failures": [], "cases": [{"passed": True}]}), [])

    def test_malformed_rows_and_failure_list_fail_closed(self):
        self.assertTrue(runner.failures({"checks": None}))
        self.assertTrue(runner.failures({"checks": {"passed": True}}))
        self.assertTrue(runner.failures({"failures": ""}))

    def test_single_clock_verdict_and_empty_case_array_differ(self):
        self.assertEqual(runner.condition_count({"done": True, "passed": True}), 1)
        self.assertEqual(runner.condition_count({"done": True, "passed": True, "cases": []}), 0)

    def test_plan_mode_sends_nothing_and_saves_nothing(self):
        class NoLock:
            def __str__(self):
                return "잠금 사용 금지"

            def open(self, *args, **kwargs):
                raise AssertionError("잠금 쓰기 금지")

        with patch.object(runner.Runner, "send", side_effect=AssertionError("에디터 호출 금지")), \
                patch.object(runner.Runner, "save", side_effect=AssertionError("Saved 쓰기 금지")), \
                patch.object(runner, "LOCK", NoLock()), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(runner.main(["--plan-only", "--suite", "charge-sweep", "--suite", "feedback"]), 0)
        plan = json.loads(output.getvalue())
        self.assertEqual(plan["mode"], "plan_only")
        self.assertFalse(plan["editor_calls_performed"])
        self.assertEqual(plan["expected_conditions"], 63)

    def test_result_name_is_read_from_source_without_executing_it(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "test.py"
            source.write_text('raise RuntimeError("실행 금지")\noutput="fixture-result.json"\n', encoding="utf-8")
            self.assertEqual(runner.result_name(source), "fixture-result.json")

    def test_editor_pid_change_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "PID"):
            runner.validate_editor_state({"pid": 456, "saved_dir": str(runner.SAVED)}, 123)

    def test_editor_saved_mismatch_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Saved"):
            runner.validate_editor_state({"pid": 123, "saved_dir": str(runner.REPO)}, 123)

    def test_archive_does_not_treat_own_new_result_as_previous_run(self):
        instance = runner.Runner(runner.select_suites(identifiers=["actor-clock"]))
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / "result.json"
            instance.archive_dir = Path(directory) / "history"
            instance.archive(result)
            result.write_text("새 실행의 첫 결과", encoding="utf-8")
            instance.archive(result)
            self.assertFalse(instance.archive_dir.exists())

    def test_archive_preserves_original_evidence_only_once(self):
        instance = runner.Runner(runner.select_suites(identifiers=["actor-clock"]))
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / "result.json"
            instance.archive_dir = Path(directory) / "history"
            result.write_text("이전 실행 근거", encoding="utf-8")
            instance.archive(result)
            result.write_text("새 실행 진행 중", encoding="utf-8")
            instance.archive(result)
            self.assertEqual((instance.archive_dir / result.name).read_text(encoding="utf-8"), "이전 실행 근거")


if __name__ == "__main__":
    unittest.main()
