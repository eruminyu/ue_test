"""일시정지 버튼의 실제 델리게이트와 맵 전환을 PIE에서 검사한다."""
import json
import os
import time
import traceback
import unreal

_menu_level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
_menu_editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
_menu_state = {"phase": "waiting", "start": time.monotonic(), "checks": []}
_menu_handle = None


def _menu_check(name, condition):
    _menu_state["checks"].append({"name": name, "passed": bool(condition)})
    if not condition:
        raise AssertionError(name)


def _menu_click(controller, name):
    widget = controller.get_editor_property("PauseWidget")
    button = widget.get_editor_property(name + "Button")
    button.get_editor_property("on_clicked").broadcast()


def _menu_finish(error=None):
    world = _menu_editor.get_game_world()
    if world:
        unreal.GameplayStatics.set_game_paused(world, False)
    checks = _menu_state["checks"]
    output = {"done": True, "passed": error is None and all(c["passed"] for c in checks), "checks": checks, "error": error, "physical_input_tested": False}
    with open(os.path.join(unreal.Paths.project_saved_dir(), "pause-buttons-result.json"), "w", encoding="utf-8") as stream:
        json.dump(output, stream, ensure_ascii=False, indent=2)
    unreal.unregister_slate_post_tick_callback(_menu_handle)
    if world:
        _menu_level.editor_request_end_play()


def _menu_wait(phase, controller):
    _menu_state.update({"phase": phase, "previous_controller": controller, "transition_start": time.monotonic()})


def _menu_tick(delta):
    try:
        world = _menu_editor.get_game_world()
        now = time.monotonic()
        phase = _menu_state["phase"]
        if phase == "quit":
            if world is None:
                _menu_check("종료 버튼에서 PIE 종료", True)
                _menu_finish()
            elif now - _menu_state["transition_start"] > 15:
                _menu_finish("종료 시간 초과")
            return
        if world is None or unreal.GameplayStatics.get_time_seconds(world) < 0.4:
            if now - _menu_state.get("transition_start", _menu_state["start"]) > 25:
                _menu_finish("월드 준비 시간 초과")
            return
        controller = unreal.GameplayStatics.get_player_controller(world, 0)
        if phase in ["restarted", "dungeon", "returned"]:
            if controller == _menu_state["previous_controller"]:
                if now - _menu_state["transition_start"] > 25:
                    _menu_finish("새 컨트롤러 생성 시간 초과")
                return
        if phase == "waiting":
            controller.call_method("TogglePauseMenu")
            _menu_click(controller, "Resume")
            _menu_check("계속하기 실제 버튼에서 복귀", not unreal.GameplayStatics.is_game_paused(world) and controller.get_editor_property("PauseWidget") is None)
            entry = controller.call_method("OpenDungeonEntry", args=(unreal.Text("테스트"), unreal.Text("기존 입장 창 수명 검사"), unreal.Name("L_Dungeon_01")))
            controller.call_method("TogglePauseMenu")
            _menu_check("입장 창 위에 메뉴 생성 거부", controller.get_editor_property("PauseWidget") is None and not unreal.GameplayStatics.is_game_paused(world))
            controller.call_method("HandleEntryCancelled")
            controller.call_method("TogglePauseMenu")
            _menu_click(controller, "Restart")
            _menu_wait("restarted", controller)
        elif phase == "restarted":
            _menu_check("재시작에서 새 필드 생성", "L_CombatField" in world.get_path_name())
            _menu_check("재시작에서 정지·위젯·커서 정리", not unreal.GameplayStatics.is_game_paused(world) and controller.get_editor_property("PauseWidget") is None and not controller.get_editor_property("show_mouse_cursor"))
            instance = unreal.GameplayStatics.get_game_instance(world)
            instance.call_method("EnterDungeon", args=(unreal.Name("L_Dungeon_01"),))
            _menu_wait("dungeon", controller)
        elif phase == "dungeon":
            _menu_check("실제 던전 입장", "L_Dungeon_01" in world.get_path_name())
            controller.call_method("TogglePauseMenu")
            _menu_click(controller, "Return")
            _menu_wait("returned", controller)
        elif phase == "returned":
            _menu_check("복귀 버튼에서 필드 생성", "L_CombatField" in world.get_path_name())
            location = unreal.GameplayStatics.get_player_pawn(world, 0).get_actor_location()
            _menu_check("실제 복귀 포털 위치", abs(location.x) < 10 and abs(location.y - 1450) < 10)
            _menu_check("복귀에서 정지·위젯·커서 정리", not unreal.GameplayStatics.is_game_paused(world) and controller.get_editor_property("PauseWidget") is None and not controller.get_editor_property("show_mouse_cursor"))
            controller.call_method("TogglePauseMenu")
            _menu_click(controller, "Quit")
            _menu_wait("quit", controller)
    except Exception:
        _menu_finish(traceback.format_exc())


if _menu_editor.get_game_world() is not None:
    raise RuntimeError("기존 PIE를 종료한 뒤 실행한다.")
_menu_handle = unreal.register_slate_post_tick_callback(_menu_tick)
_menu_level.editor_request_begin_play()
result = {"started": True}
