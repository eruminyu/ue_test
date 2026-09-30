"""실제 GE의 HP 감소량과 피드백 표시를 통합 PIE에서 대조한다."""
import json
import os
import time
import traceback
import unreal

_damage_editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
_damage_level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
_damage_state = {"phase": "waiting", "start": time.monotonic(), "checks": []}
_damage_handle = None


def _damage_check(name, condition, details=None):
    _damage_state["checks"].append({"name": name, "passed": bool(condition), "details": details})
    if not condition:
        raise AssertionError(name)


def _damage_finish(error=None):
    world = _damage_editor.get_game_world()
    if world:
        unreal.GameplayStatics.set_game_paused(world, False)
    output = {"done": True, "passed": error is None and all(c["passed"] for c in _damage_state["checks"]), "checks": _damage_state["checks"], "error": error}
    with open(os.path.join(unreal.Paths.project_saved_dir(), "real-damage-feedback-result.json"), "w", encoding="utf-8") as stream:
        json.dump(output, stream, ensure_ascii=False, indent=2)
    unreal.unregister_slate_post_tick_callback(_damage_handle)
    _damage_level.editor_request_end_play()


def _damage_health(actor):
    asc = actor.get_component_by_class(unreal.AbilitySystemComponent)
    attribute = next(a for a in asc.get_all_attributes() if unreal.AbilitySystemLibrary.get_debug_string_from_gameplay_attribute(a).endswith(".Health"))
    return asc.get_gameplay_attribute_value(attribute)[0]


def _damage_numbers(world):
    return unreal.GameplayStatics.get_all_actors_of_class(world, _damage_state["number_class"])


def _damage_display(actor):
    widget = actor.get_component_by_class(unreal.WidgetComponent).get_user_widget_object()
    return widget.get_editor_property("DamageValue"), widget.get_editor_property("bGuardedValue")


def _damage_effect(actor, effect_name):
    asc = actor.get_component_by_class(unreal.AbilitySystemComponent)
    effect = unreal.load_class(None, "/Game/SoulCombat/GAS/Effects/" + effect_name + "." + effect_name + "_C")
    return asc.apply_gameplay_effect_to_self(effect, 1.0, asc.make_effect_context())


def _damage_tag(name):
    value = unreal.GameplayTag()
    value.import_text('(TagName="' + name + '")')
    return value


def _damage_tick(delta):
    try:
        world = _damage_editor.get_game_world()
        if _damage_state["phase"] == "waiting":
            if world is None or unreal.GameplayStatics.get_time_seconds(world) < 0.4:
                if time.monotonic() - _damage_state["start"] > 20:
                    _damage_finish("PIE 준비 시간 초과")
                return
            feedback_class = unreal.load_class(None, "/Game/SoulCombat/Components/AC_CombatFeedback.AC_CombatFeedback_C")
            number_class = unreal.load_class(None, "/Game/SoulCombat/Combat/BP_DamageNumber.BP_DamageNumber_C")
            _damage_check("피드백 계약 에셋 존재", feedback_class is not None and number_class is not None)
            _damage_state["number_class"] = number_class
            controller = unreal.GameplayStatics.get_player_controller(world, 0)
            feedback = controller.get_component_by_class(feedback_class)
            _damage_check("실제 컨트롤러에 피드백 연결", feedback is not None)
            player = unreal.GameplayStatics.get_player_pawn(world, 0)
            dummy = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) if a.get_actor_label() == "Dummy_2")
            combat_class = unreal.load_class(None, "/Game/SoulCombat/Components/AC_CombatComponent.AC_CombatComponent_C")
            combat = player.get_component_by_class(combat_class)
            for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
                if actor.get_actor_label().startswith("SparringGrunt"):
                    actor.call_method("SetDormant", args=(True,))
            before = _damage_health(dummy)
            count = len(_damage_numbers(world))
            combat.call_method("ApplyHit", args=(dummy, 1.0, 0.0, 0.0))
            numbers = _damage_numbers(world)
            _damage_check("평타 실제 피해50", abs(before - _damage_health(dummy) - 50) < 0.05)
            _damage_check("실제 명중 숫자 생성", len(numbers) == count + 1)
            value, guarded = _damage_display(numbers[-1])
            _damage_check("실제 피해50 표시", abs(value - 50) < 0.05 and not guarded, {"damage": value, "guarded": guarded})
            _damage_state.update({"feedback": feedback, "controller": controller, "dummy": dummy, "combat": combat, "player": player, "phase": "after_hit", "hit_real": time.monotonic()})
        elif _damage_state["phase"] == "after_hit" and time.monotonic() - _damage_state["hit_real"] > 1.1:
            _damage_check("숫자 수명 종료", len(_damage_numbers(world)) == 0)
            player = _damage_state["player"]
            combat = _damage_state["combat"]
            before = _damage_health(_damage_state["dummy"])
            combat.call_method("ApplyHit", args=(_damage_state["dummy"], 0.0, 0.0, 0.0))
            _damage_check("피해0에서 HP·숫자 그대로", _damage_health(_damage_state["dummy"]) == before and len(_damage_numbers(world)) == 0)
            grunt = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) if a.get_actor_label() == "SparringGrunt_1")
            _damage_state["grunt_combat"] = grunt.get_component_by_class(combat.get_class())
            _damage_effect(player, "GE_DashInvuln")
            before = _damage_health(player)
            _damage_state["grunt_combat"].call_method("ApplyHit", args=(player, 1.0, 0.0, 0.0))
            _damage_check("무적에서 HP·숫자 그대로", _damage_health(player) == before and len(_damage_numbers(world)) == 0)
            _damage_state.update({"phase": "guard", "hit_real": time.monotonic()})
        elif _damage_state["phase"] == "guard" and time.monotonic() - _damage_state["hit_real"] > 0.6:
            player = _damage_state["player"]
            grunt = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) if a.get_actor_label() == "SparringGrunt_1")
            player.set_actor_location_and_rotation(unreal.Vector(550, 0, 95), unreal.Rotator(), False, True)
            grunt.set_actor_location_and_rotation(unreal.Vector(800, 0, 95), unreal.Rotator(yaw=180), False, True)
            _damage_state["combat"].call_method("PressInput", args=(_damage_tag("InputTag.Guard"),))
            before = _damage_health(player)
            _damage_state["grunt_combat"].call_method("ApplyHit", args=(player, 1.0, 0.0, 0.0))
            value, guarded = _damage_display(_damage_numbers(world)[-1])
            _damage_check("가드의 실제 피해5와 표시", abs(before - _damage_health(player) - 5) < 0.05 and abs(value - 5) < 0.05 and guarded, {"damage": value, "guarded": guarded})
            _damage_state["combat"].call_method("ReleaseInput", args=(_damage_tag("InputTag.Guard"),))
            _damage_state.update({"phase": "overkill", "hit_real": time.monotonic()})
        elif _damage_state["phase"] == "overkill" and time.monotonic() - _damage_state["hit_real"] > 1.1:
            dummy = _damage_state["dummy"]
            asc = dummy.get_component_by_class(unreal.AbilitySystemComponent)
            effect = unreal.load_class(None, "/Game/SoulCombat/GAS/Effects/GE_Damage.GE_Damage_C")
            spec = asc.make_outgoing_spec(effect, 1.0, asc.make_effect_context())
            spec = unreal.AbilitySystemLibrary.assign_tag_set_by_caller_magnitude(spec, _damage_tag("Data.Damage"), _damage_health(dummy) - 25)
            asc.apply_gameplay_effect_spec_to_self(spec)
            _damage_state["combat"].call_method("ApplyHit", args=(dummy, 1.0, 0.0, 0.0))
            numbers = _damage_numbers(world)
            value, guarded = _damage_display(numbers[-1])
            _damage_check("과잉 피해는 실제 남은 HP25 표시", _damage_health(dummy) == 0 and abs(value - 25) < 0.05, {"damage": value})
            count = len(numbers)
            _damage_state["combat"].call_method("ApplyHit", args=(dummy, 1.0, 0.0, 0.0))
            _damage_check("이미 죽은 대상은 추가 숫자 없음", len(_damage_numbers(world)) == count)
            _damage_state["feedback"].call_method("ResetAllFeedback")
            player = _damage_state["player"]
            player.set_editor_property("custom_time_dilation", 0.6, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
            camera = player.get_component_by_class(unreal.CameraComponent)
            fov = camera.get_editor_property("field_of_view")
            live = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) if a.get_actor_label() == "Dummy_1")
            _damage_state["combat"].call_method("ApplyHit", args=(live, 1.0, 0.0, 0.0))
            _damage_state["controller"].call_method("TogglePauseMenu")
            _damage_check("메뉴 진입에서 기존 배율0.6 복원", abs(player.get_editor_property("custom_time_dilation") - 0.6) < 0.001)
            _damage_check("메뉴 진입에서 기존 FOV 복원", abs(camera.get_editor_property("field_of_view") - fov) < 0.001)
            player.set_editor_property("custom_time_dilation", 1.0, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
            _damage_state["controller"].call_method("ResumeGame")
            _damage_finish()
    except Exception:
        _damage_finish(traceback.format_exc())


if _damage_editor.get_game_world() is not None:
    raise RuntimeError("기존 PIE를 종료한 뒤 실행한다.")
_damage_handle = unreal.register_slate_post_tick_callback(_damage_tick)
_damage_level.editor_request_begin_play()
result = {"started": True}
