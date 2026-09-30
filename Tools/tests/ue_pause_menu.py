"""실제 PIE의 일시정지 메뉴 수명과 입력 복귀를 검사한다."""
import json
import os
import time
import traceback
import unreal

_pause_level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
_pause_editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
_pause_state = {"phase": "waiting", "start": time.monotonic(), "checks": []}
_pause_handle = None


def _pause_finish(error=None):
    world = _pause_editor.get_game_world()
    if world:
        unreal.GameplayStatics.set_game_paused(world, False)
    checks = _pause_state["checks"]
    output = {"done": True, "passed": error is None and all(c["passed"] for c in checks), "checks": checks, "error": error}
    with open(os.path.join(unreal.Paths.project_saved_dir(), "pause-menu-result.json"), "w", encoding="utf-8") as stream:
        json.dump(output, stream, ensure_ascii=False, indent=2)
    unreal.unregister_slate_post_tick_callback(_pause_handle)
    _pause_level.editor_request_end_play()


def _pause_check(name, passed):
    _pause_state["checks"].append({"name": name, "passed": bool(passed)})
    if not passed:
        raise AssertionError(name)


def _pause_tick(delta):
    try:
        world = _pause_editor.get_game_world()
        now = time.monotonic()
        phase = _pause_state["phase"]
        if phase == "waiting":
            if world is None or unreal.GameplayStatics.get_time_seconds(world) < 0.4:
                if now - _pause_state["start"] > 20:
                    _pause_finish("PIE 시작 시간 초과")
                return
            controller = unreal.GameplayStatics.get_player_controller(world, 0)
            _pause_state["controller"] = controller
            controller.call_method("TogglePauseMenu")
            _pause_check("메뉴 열기에서 게임 정지", unreal.GameplayStatics.is_game_paused(world))
            _pause_check("메뉴 위젯 표시", controller.get_editor_property("PauseWidget") is not None)
            _pause_check("메뉴에서 마우스 표시", controller.get_editor_property("show_mouse_cursor"))
            _pause_state["paused_time"] = unreal.GameplayStatics.get_time_seconds(world)
            _pause_state["paused_real"] = now
            _pause_state["phase"] = "paused"
        elif phase == "paused" and now - _pause_state["paused_real"] > 0.3:
            controller = _pause_state["controller"]
            _pause_check("일시정지 동안 월드 시간 정지", abs(unreal.GameplayStatics.get_time_seconds(world) - _pause_state["paused_time"]) < 0.001)
            controller.call_method("ResumeGame")
            _pause_check("계속하기에서 게임 재개", not unreal.GameplayStatics.is_game_paused(world))
            _pause_check("닫은 메뉴 참조 해제", controller.get_editor_property("PauseWidget") is None)
            _pause_check("게임에서 마우스 숨김", not controller.get_editor_property("show_mouse_cursor"))
            controller.call_method("TogglePauseMenu")
            controller.call_method("TogglePauseMenu")
            _pause_check("반복 열기와 닫기 복귀", not unreal.GameplayStatics.is_game_paused(world) and controller.get_editor_property("PauseWidget") is None)
            _pause_finish()
    except Exception:
        _pause_finish(traceback.format_exc())


if _pause_editor.get_game_world() is not None:
    raise RuntimeError("기존 PIE를 종료한 뒤 실행한다.")
_pause_handle = unreal.register_slate_post_tick_callback(_pause_tick)
_pause_level.editor_request_begin_play()
result = {"started": True}
