"""실제 PIE에서 피해가 애니메이션의 타격 시점에 맞는지 검사한다.

PythonScriptPlugin 작업 브리지에서 실행한다. 테스트 준비는 PIE 액터만
변경하며 에셋을 저장하지 않는다. 결과는 프로젝트 Saved에 기록한다.
"""
import json
import os
import time
import traceback
import unreal

_clock_editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
_clock_level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
_clock_output = os.path.join(unreal.Paths.project_saved_dir(), "combat-actor-clock-result.json")
_clock_state = {"phase": "waiting", "created": time.monotonic(), "player": None, "done": False}
_clock_handle = None


def _clock_attributes(actor):
    component = actor.get_component_by_class(unreal.AbilitySystemComponent)
    values = {}
    for attribute in component.get_all_attributes():
        name = unreal.AbilitySystemLibrary.get_debug_string_from_gameplay_attribute(attribute).split(".")[-1]
        value, found = component.get_gameplay_attribute_value(attribute)
        if found:
            values[name] = value
    return values


def _clock_finish(passed, details):
    player_actor = _clock_state["player"]
    if player_actor is not None:
        player_actor.set_editor_property("custom_time_dilation", _clock_state.get("original_dilation", 1.0), notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
    _clock_state["done"] = True
    with open(_clock_output, "w", encoding="utf-8") as stream:
        json.dump({"done": True, "passed": passed, "test": "개별 배속 0.25에서 피해의 몽타주 시점", "details": details}, stream, ensure_ascii=False, indent=2)
    unreal.unregister_slate_post_tick_callback(_clock_handle)
    _clock_level.editor_request_end_play()


def _clock_tick(delta):
    try:
        now = time.monotonic()
        world = _clock_editor.get_game_world()
        if _clock_state["phase"] == "waiting":
            if world is None or unreal.GameplayStatics.get_time_seconds(world) < 0.4:
                if now - _clock_state["created"] > 20:
                    _clock_finish(False, {"error": "PIE 시작 시간 초과"})
                return
            player_actor = unreal.GameplayStatics.get_player_pawn(world, 0)
            targets = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
            dummy = next(actor for actor in targets if actor.get_actor_label() == "Dummy_2")
            _clock_state["player"] = player_actor
            _clock_state["dummy"] = dummy
            _clock_state["original_dilation"] = player_actor.get_editor_property("custom_time_dilation")
            player_actor.set_actor_location_and_rotation(unreal.Vector(550, 0, 95), unreal.Rotator(), False, True)
            dummy.set_actor_location_and_rotation(unreal.Vector(800, 0, 95), unreal.Rotator(yaw=180), False, True)
            _clock_state["health_before"] = _clock_attributes(dummy)["Health"]
            player_actor.set_editor_property("custom_time_dilation", 0.25, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
            input_tag = unreal.GameplayTag()
            input_tag.import_text('(TagName="InputTag.Attack")')
            component_type = unreal.load_class(None, "/Game/SoulCombat/Components/AC_CombatComponent.AC_CombatComponent_C")
            activated = player_actor.get_component_by_class(component_type).call_method("PressInput", args=(input_tag,))
            if not activated:
                _clock_finish(False, {"error": "평타 발동 실패"})
                return
            _clock_state["start"] = now
            _clock_state["phase"] = "attacking"
            return
        if _clock_state["phase"] == "attacking":
            health = _clock_attributes(_clock_state["dummy"])["Health"]
            if health < _clock_state["health_before"] - 0.1:
                anim = _clock_state["player"].get_editor_property("mesh").get_anim_instance()
                montage = anim.get_current_active_montage()
                position = anim.montage_get_position(montage) if montage is not None else None
                damage = _clock_state["health_before"] - health
                passed = position is not None and abs(position - 0.467) < 0.08 and abs(damage - 50) < 0.05
                _clock_finish(passed, {"montage": montage.get_path_name() if montage else None, "montage_position": position, "expected_position": 0.467, "damage": damage, "elapsed_real": now - _clock_state["start"], "actor_dilation": 0.25})
            elif now - _clock_state["start"] > 8:
                _clock_finish(False, {"error": "타격 시간 초과", "health": health})
    except Exception:
        _clock_finish(False, {"error": traceback.format_exc()})


if _clock_editor.get_game_world() is not None:
    raise RuntimeError("새로운 PIE에서 시작할 검사다. 기존 PIE를 먼저 종료한다.")
_clock_handle = unreal.register_slate_post_tick_callback(_clock_tick)
_clock_level.editor_request_begin_play()
result = {"started": True, "output": _clock_output}
