"""PIE에서 실제 몽타주 위치와 피해를 비교하는 판정 회귀 검사.

에디터 Python 게임 스레드에서 실행한다. 게임 에셋은 저장하거나 변경하지
않고 테스트 월드의 배율, 위치, 기존 회복 GE만 변경한다.
"""
import json
import os
import traceback
import unreal

_editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
_world = _editor.get_game_world()
if _world is None:
    raise RuntimeError("PIE를 시작한 뒤 검사해야 합니다.")
_player = unreal.GameplayStatics.get_player_pawn(_world, 0)
_actors = unreal.GameplayStatics.get_all_actors_of_class(_world, unreal.Actor)
_dummy = next(a for a in _actors if a.get_actor_label() == "Dummy_2")
_combat_class = unreal.load_class(None, "/Game/SoulCombat/Components/AC_CombatComponent.AC_CombatComponent_C")
_restore_class = unreal.load_class(None, "/Game/SoulCombat/GAS/Effects/GE_RestoreFull.GE_RestoreFull_C")
_ga_class = unreal.load_class(None, "/Game/SoulCombat/GAS/Abilities/GA_Player_BasicAttack.GA_Player_BasicAttack_C")
_montage = unreal.get_default_object(_ga_class).get_editor_property("ComboMontage")
_anim = _player.mesh.get_anim_instance()
_initial_dilation = _player.custom_time_dilation
_output = os.path.join(unreal.Paths.project_saved_dir(), "combat-timing-result.json")
_rows, _failures, _samples = [], [], []
_cases = [("단타 배율 " + str(d), d, 1, 50, None) for d in (0.25, 0.5, 1.0, 1.5)]
_cases += [("같은 프레임 4연타", 1.0, 4, 270, None), ("같은 프레임 8연타", 1.0, 8, 270, None),
           ("타격 전 대시 취소", 1.0, 1, 0, "dash"), ("타격 전 몽타주 중단", 1.0, 1, 0, "stop"),
           ("4연타 배율0.5",0.5,4,270,None), ("콤보 중 히트스톱",1,4,270,"hitstop"),
           ("같은 단계 중복 신호",1,1,50,"duplicate"), ("다른 몽타주/액터 신호",1,1,50,"foreign"),
           ("타격 전 피격 취소",1,1,0,"react"), ("타격 전 사망 취소",1,1,0,"death")]
_index, _stage, _start, _last_hp, _hit_count, _timing_bad = 0, 0, 0.0, None, 0, False
_extra_sent,_pause_started=False,None
_handle = None


def _asc(actor):
    return actor.get_component_by_class(unreal.AbilitySystemComponent)


def _health(actor):
    component = _asc(actor)
    for attr in component.get_all_attributes():
        if unreal.AbilitySystemLibrary.get_debug_string_from_gameplay_attribute(attr).endswith(".Health"):
            return component.get_gameplay_attribute_value(attr)[0]
    raise RuntimeError("Health 속성 없음")


def _restore(actor):
    c = _asc(actor)
    c.apply_gameplay_effect_to_self(_restore_class, 1, c.make_effect_context())


def _tag(name):
    t = unreal.GameplayTag()
    t.import_text('(TagName="' + name + '")')
    return t


def _press(name):
    return _player.get_component_by_class(_combat_class).call_method("PressInput", args=(_tag(name),))


def _tags():
    ts = unreal.GameplayTagLibrary.get_owned_gameplay_tags(_asc(_player))
    return [unreal.GameplayTagLibrary.get_debug_string_from_gameplay_tag(t)
            for t in unreal.GameplayTagLibrary.break_gameplay_tag_container(ts)]


def _signal(instigator,source):
    event_tag=_tag("Event.Combat.HitFrame")
    payload=unreal.GameplayEventData(event_tag=event_tag,instigator=instigator,target=_player,
                                   optional_object=source,event_magnitude=1.0)
    unreal.AbilitySystemLibrary.send_gameplay_event_to_actor(_player,event_tag,payload)


def _save(done):
    with open(_output, "w", encoding="utf-8") as f:
        json.dump({"done": done, "cases": _rows, "failures": _failures, "samples": _samples}, f, ensure_ascii=False, indent=2)


for _actor in _actors:
    if _actor.get_actor_label().startswith("SparringGrunt_"):
        _actor.call_method("SetDormant", args=(True,))


def _tick(delta):
    global _index, _stage, _start, _last_hp, _hit_count, _timing_bad,_extra_sent,_pause_started
    try:
        now = unreal.GameplayStatics.get_time_seconds(_world)
        if _index >= len(_cases):
            _player.custom_time_dilation = _initial_dilation
            unreal.unregister_slate_post_tick_callback(_handle)
            _save(True)
            return
        label, dilation, presses, damage, cancellation = _cases[_index]
        if _stage == 0:
            _player.custom_time_dilation = 1.0
            _anim.montage_stop(0)
            _restore(_player)
            _restore(_dummy)
            for actor, xyz, yaw in ((_player, [550, 0, 95], 0), (_dummy, [800, 0, 95], 180)):
                actor.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
                actor.set_actor_location_and_rotation(unreal.Vector(*xyz), unreal.Rotator(yaw=yaw), False, True)
            _stage, _start = 1, now
        elif _stage == 1 and now - _start >= 0.7:
            _player.custom_time_dilation = dilation
            _last_hp, _hit_count, _timing_bad = _health(_dummy), 0, False
            _extra_sent,_pause_started=False,None
            for unused in range(presses):
                _press("InputTag.Attack")
            _stage, _start = 2, now
        elif _stage == 2:
            elapsed = now - _start
            if cancellation in ("dash","stop","react","death") and elapsed >= 0.15:
                if cancellation == "dash":
                    _press("InputTag.Dash")
                elif cancellation == "stop":
                    _anim.montage_stop(0)
                else:
                    enemy=next(a for a in _actors if a.get_actor_label()=="SparringGrunt_1")
                    enemy.get_component_by_class(_combat_class).call_method("ApplyHit",args=(_player,10000.0 if cancellation=="death" else 1.0,0.0,0.0))
                _stage = 3
            if cancellation=="foreign" and not _extra_sent and elapsed>=0.1:
                _signal(_dummy,_montage)
                _signal(_player,unreal.load_asset("/Game/Variant_Combat/Anims/AM_ComboAttack"))
                _extra_sent=True
            if cancellation=="duplicate" and not _extra_sent and _hit_count>=1:
                _signal(_player,_montage)
                _signal(_player,_montage)
                _extra_sent=True
            if cancellation=="hitstop":
                if _pause_started is None and elapsed>=0.48:
                    _player.custom_time_dilation=0.05
                    _pause_started=now
                elif _pause_started is not None and now-_pause_started>=0.1:
                    _player.custom_time_dilation=dilation
            hp = _health(_dummy)
            if hp < _last_hp - 0.01:
                position = _anim.montage_get_position(_montage)
                _samples.append({"case": label, "elapsed": elapsed, "montage_position": position,
                                 "damage": _last_hp - hp, "dilation": dilation})
                _hit_count += 1
                if presses == 1 and position < 0.467 - 0.035:
                    _timing_bad = True
                _last_hp = hp
            if elapsed >= (3.8 / dilation if presses > 1 else 2.0 / dilation):
                _stage = 4
        elif _stage == 3 and now - _start >= (4.0 if cancellation=="death" else 2.0):
            _stage = 4
        if _stage == 4:
            actual = 5000 - _health(_dummy)
            expected_hits = 4 if presses > 1 else (0 if cancellation in ("dash","stop","react","death") else 1)
            active = _tags()
            passed = abs(actual - damage) < 0.05 and _hit_count == expected_hits and not _timing_bad and "State.Attacking" not in active
            row = {"case": label, "expected_damage": damage, "actual_damage": actual,
                   "expected_hits": expected_hits, "actual_hits": _hit_count,
                   "hit_before_animation_frame": _timing_bad, "tags": active, "passed": passed}
            _rows.append(row)
            if not passed:
                _failures.append(label)
            _index, _stage = _index + 1, 0
            _save(False)
    except Exception:
        _failures.append(traceback.format_exc())
        _player.custom_time_dilation = _initial_dilation
        unreal.unregister_slate_post_tick_callback(_handle)
        _save(True)


_handle = unreal.register_slate_post_tick_callback(_tick)
_save(False)
result = {"started": True, "cases": len(_cases), "output": _output}
