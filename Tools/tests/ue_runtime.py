"""실행 중인 실제 PIE에서 사용하는 회귀 검사 공통 함수다."""
import json
import os
import time
import math
import unreal

ROOT = os.path.abspath(unreal.Paths.project_saved_dir())
ue = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
le = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def game_world():
    world = ue.get_game_world()
    if world is None:
        raise RuntimeError("PIE 월드 없음")
    return world


def player():
    return unreal.GameplayStatics.get_player_pawn(game_world(), 0)


def pc():
    return unreal.GameplayStatics.get_player_controller(game_world(), 0)


def all_actors():
    return unreal.GameplayStatics.get_all_actors_of_class(game_world(), unreal.Actor)


def actor_named(label):
    return next(a for a in all_actors() if a.get_actor_label() == label)


def combat(actor):
    cls = unreal.load_class(None, "/Game/SoulCombat/Components/AC_CombatComponent.AC_CombatComponent_C")
    return actor.get_component_by_class(cls)


def asc(actor):
    return actor.get_component_by_class(unreal.AbilitySystemComponent)


def tag(name):
    value = unreal.GameplayTag()
    value.import_text('(TagName="' + name + '")')
    if not unreal.GameplayTagLibrary.is_gameplay_tag_valid(value):
        raise ValueError("잘못된 태그: " + name)
    return value


def tags(actor):
    values = unreal.GameplayTagLibrary.get_owned_gameplay_tags(asc(actor))
    return [unreal.GameplayTagLibrary.get_debug_string_from_gameplay_tag(v) for v in unreal.GameplayTagLibrary.break_gameplay_tag_container(values)]


def attributes(actor):
    component = asc(actor)
    result = {}
    for attr in component.get_all_attributes():
        name = unreal.AbilitySystemLibrary.get_debug_string_from_gameplay_attribute(attr).split('.')[-1]
        value, found = component.get_gameplay_attribute_value(attr)
        if found:
            result[name] = value
    return result


def position(actor):
    value = actor.get_actor_location()
    return [value.x, value.y, value.z]


def press(name):
    return combat(player()).call_method("PressInput", args=(tag(name),))


def release(name):
    return combat(player()).call_method("ReleaseInput", args=(tag(name),))


def teleport(actor, xyz, yaw=0):
    actor.set_actor_location_and_rotation(unreal.Vector(*xyz), unreal.Rotator(yaw=yaw), False, True)


def snapshot():
    p = player()
    return {"map": game_world().get_name(), "player": attributes(p), "tags": tags(p), "location": position(p), "world_seconds": unreal.GameplayStatics.get_time_seconds(game_world())}


def restore(actor):
    component = asc(actor)
    component.apply_gameplay_effect_to_self(unreal.load_class(None, "/Game/SoulCombat/GAS/Effects/GE_RestoreFull.GE_RestoreFull_C"), 1.0, component.make_effect_context())


def reset_combat():
    p = player()
    restore(p)
    restore(DUMMY)
    p.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
    DUMMY.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
    teleport(p, [550, 0, 95], 0)
    teleport(DUMMY, [800, 0, 95], 180)


result = {
    "snapshot": snapshot(),
    "combat": combat(player()).get_path_name(),
    "test_tag": str(tag("InputTag.Attack")),
    "actors": [{"name":a.get_actor_label(), "class":a.get_class().get_name(), "location":position(a)} for a in all_actors() if a.get_class().get_name().startswith("BP_")],
}
