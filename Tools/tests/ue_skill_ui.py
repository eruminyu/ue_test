"""실제 GA 비용 GE와 HUD 표시·실제 쿨다운 효과를 대조한다."""
import json
import os
import time
import traceback
import unreal

_skill_editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
_skill_level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
_skill_cases = [("GA_Player_Dash", "SlotDash", "InputTag.Dash"), ("GA_Skill_DashSlash", "SlotSkill1", "InputTag.Skill.1"), ("GA_Skill_GroundSlam", "SlotSkill2", "InputTag.Skill.2"), ("GA_Skill_WaveSlash", "SlotSkill3", "InputTag.Skill.3")]
_skill_state = {"phase": "waiting", "created": time.monotonic(), "index": 0, "checks": []}
_skill_handle = None


def _skill_check(name, condition, details=None):
    _skill_state["checks"].append({"name": name, "passed": bool(condition), "details": details})
    if not condition:
        raise AssertionError(name)


def _skill_finish(error=None):
    checks = _skill_state["checks"]
    with open(os.path.join(unreal.Paths.project_saved_dir(), "skill-ui-result.json"), "w", encoding="utf-8") as stream:
        json.dump({"done": True, "passed": error is None and all(c["passed"] for c in checks), "checks": checks, "error": error}, stream, ensure_ascii=False, indent=2)
    unreal.unregister_slate_post_tick_callback(_skill_handle)
    _skill_level.editor_request_end_play()


def _skill_tick(delta):
    try:
        now = time.monotonic()
        world = _skill_editor.get_game_world()
        if _skill_state["phase"] == "waiting":
            if world is None or unreal.GameplayStatics.get_time_seconds(world) < 0.4:
                if now - _skill_state["created"] > 20:
                    _skill_finish("PIE 준비 시간 초과")
                return
            player = unreal.GameplayStatics.get_player_pawn(world, 0)
            controller = unreal.GameplayStatics.get_player_controller(world, 0)
            combat_class = unreal.load_class(None, "/Game/SoulCombat/Components/AC_CombatComponent.AC_CombatComponent_C")
            _skill_state.update({"player": player, "hud": controller.get_editor_property("HUD"), "combat": player.get_component_by_class(combat_class), "phase": "next"})
        if _skill_state["phase"] == "next":
            if _skill_state["index"] >= len(_skill_cases):
                _skill_finish()
                return
            ability_name, slot_name, input_name = _skill_cases[_skill_state["index"]]
            ability = unreal.get_default_object(unreal.load_class(None, "/Game/SoulCombat/GAS/Abilities/" + ability_name + "." + ability_name + "_C"))
            effect = unreal.get_default_object(ability.get_editor_property("cost_gameplay_effect_class"))
            modifier = effect.get_editor_property("modifiers")[0]
            magnitude = modifier.get_editor_property("modifier_magnitude").get_editor_property("scalable_float_magnitude").get_editor_property("value")
            attribute = unreal.AbilitySystemLibrary.get_debug_string_from_gameplay_attribute(modifier.get_editor_property("attribute"))
            slot = _skill_state["hud"].get_editor_property(slot_name)
            _skill_check(slot_name + " 실제 GE 비용과 표시 일치", abs(slot.get_editor_property("Cost") + magnitude) < 0.001, {"ui_cost": slot.get_editor_property("Cost"), "ge_magnitude": magnitude})
            _skill_check(slot_name + " 실제 소모 속성과 표시 일치", unreal.AbilitySystemLibrary.get_debug_string_from_gameplay_attribute(slot.get_editor_property("CostAttribute")) == attribute)
            asc = _skill_state["player"].get_component_by_class(unreal.AbilitySystemComponent)
            restore = unreal.load_class(None, "/Game/SoulCombat/GAS/Effects/GE_RestoreFull.GE_RestoreFull_C")
            asc.apply_gameplay_effect_to_self(restore, 1.0, asc.make_effect_context())
            tag = unreal.GameplayTag()
            tag.import_text('(TagName="' + input_name + '")')
            activated = _skill_state["combat"].call_method("PressInput", args=(tag,))
            _skill_check(slot_name + " 실제 발동", activated)
            slot.call_method("Refresh")
            bar = slot.get_editor_property("CooldownBar")
            _skill_check(slot_name + " 실제 쿨다운 효과 표시", str(bar.get_visibility()) != "SlateVisibility.COLLAPSED" and bar.get_editor_property("percent") > 0.9)
            _skill_state.update({"phase": "cooling", "after": now + 1.6})
        elif _skill_state["phase"] == "cooling" and now >= _skill_state["after"]:
            _skill_state["index"] += 1
            _skill_state["phase"] = "next"
    except Exception:
        _skill_finish(traceback.format_exc())


if _skill_editor.get_game_world() is not None:
    raise RuntimeError("기존 PIE를 종료한 뒤 실행한다.")
_skill_handle = unreal.register_slate_post_tick_callback(_skill_tick)
_skill_level.editor_request_begin_play()
result = {"started": True}
