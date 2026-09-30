"""프레임 간격과 독립적인 실제 Charge 이전 위치→현재 위치 스윕 회귀.

실제 BP_Enemy_Boss의 GAS 어빌리티 인스턴스와 HitAlongPath를 실행한다.
첫/둘째/역방향 사례는 목표가 구간 안에만 있으며 양 끝점의 반경 밖에 있다.
이전 위치를 먼저 덮어쓰면 첫/둘째 표본 구간은 피해0으로 실패한다.
"""
import json
import os
import time
import traceback
import unreal

_cs_editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
_cs_level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if _cs_editor.get_game_world() is not None:
    raise RuntimeError("기존 PIE를 종료한 뒤 실행한다.")
_cs_cases=[("첫 표본 사이",375,875,625,-420,90),
           ("둘째 표본 사이",875,1375,1125,-420,90),
           ("시작점",0,0,80,-600,90),
           ("마지막 구간",1375,1500,1400,-420,90),
           ("경로 밖",1375,1500,1800,-420,0),
           ("역방향 구간",875,375,625,-420,90)]
_cs_state={"phase":"waiting","created":time.monotonic(),"index":0,"cases":[],"failures":[]}
_cs_handle=None
_cs_output=os.path.join(unreal.Paths.project_saved_dir(),"combat-charge-sweep-result.json")


def _cs_health(actor):
    asc=actor.get_component_by_class(unreal.AbilitySystemComponent)
    attr=next(a for a in asc.get_all_attributes() if unreal.AbilitySystemLibrary.get_debug_string_from_gameplay_attribute(a).endswith(".Health"))
    return asc.get_gameplay_attribute_value(attr)[0]


def _cs_place(actor,x,y,yaw):
    actor.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
    actor.set_actor_location_and_rotation(unreal.Vector(x,y,95),unreal.Rotator(yaw=yaw),False,True)


def _cs_finish(error=None):
    if error:
        _cs_state["failures"].append(error)
    if _cs_state.get("boss") and unreal.SystemLibrary.is_valid(_cs_state["boss"]):
        _cs_state["boss"].destroy_actor()
    with open(_cs_output,"w",encoding="utf-8") as stream:
        json.dump({"done":True,"passed":not _cs_state["failures"],"cases":_cs_state["cases"],"failures":_cs_state["failures"]},stream,ensure_ascii=False,indent=2)
    unreal.unregister_slate_post_tick_callback(_cs_handle)
    _cs_level.editor_request_end_play()


def _cs_tick(delta):
    try:
        world=_cs_editor.get_game_world()
        if _cs_state["phase"]=="waiting":
            if world is None or unreal.GameplayStatics.get_time_seconds(world)<0.5:
                if time.monotonic()-_cs_state["created"]>30:
                    _cs_finish("PIE 준비 시간 초과")
                return
            player=unreal.GameplayStatics.get_player_pawn(world,0)
            for actor in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor):
                if actor.get_actor_label().startswith("SparringGrunt_"):
                    actor.call_method("SetDormant",args=(True,))
            _cs_state.update(player=player,phase="setup",
                combat_class=unreal.load_class(None,"/Game/SoulCombat/Components/AC_CombatComponent.AC_CombatComponent_C"),
                boss_class=unreal.load_class(None,"/Game/SoulCombat/Characters/Enemies/BP_Enemy_Boss.BP_Enemy_Boss_C"),
                charge_class=unreal.load_class(None,"/Game/SoulCombat/GAS/Abilities/GA_Boss_Charge.GA_Boss_Charge_C"),
                restore_class=unreal.load_class(None,"/Game/SoulCombat/GAS/Effects/GE_RestoreFull.GE_RestoreFull_C"))
        if _cs_state["phase"]=="setup":
            if _cs_state["index"]>=len(_cs_cases):
                _cs_finish()
                return
            player=_cs_state["player"]
            asc=player.get_component_by_class(unreal.AbilitySystemComponent)
            asc.apply_gameplay_effect_to_self(_cs_state["restore_class"],1,asc.make_effect_context())
            player.mesh.get_anim_instance().montage_stop(0)
            label,start,end,target,y,expected=_cs_cases[_cs_state["index"]]
            statics=unreal.get_default_object(unreal.GameplayStatics)
            transform=unreal.Transform(location=unreal.Vector(0,-600,95))
            boss=statics.call_method("BeginDeferredActorSpawnFromClass",args=(world,_cs_state["boss_class"],transform,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            boss.set_editor_property("bStartDormant",False)
            statics.call_method("FinishSpawningActor",args=(boss,transform,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            controller=boss.get_controller()
            if controller:
                unreal.SystemLibrary.clear_timer(controller,"Think")
                controller.set_actor_tick_enabled(False)
            _cs_place(player,target,y,180)
            _cs_place(boss,0,-600,0)
            _cs_state.update(boss=boss,phase="case",start=unreal.GameplayStatics.get_time_seconds(world))
        elif _cs_state["phase"]=="case" and unreal.GameplayStatics.get_time_seconds(world)-_cs_state["start"]>0.7:
            boss=_cs_state["boss"]
            player=_cs_state["player"]
            label,start,end,target,y,expected=_cs_cases[_cs_state["index"]]
            tag=unreal.GameplayTag()
            tag.import_text('(TagName="InputTag.AI.Attack.3")')
            if not boss.get_component_by_class(_cs_state["combat_class"]).call_method("PressInput",args=(tag,)):
                raise RuntimeError(label+": 실제 GAS 발동 거부")
            ability=next(obj for obj in unreal.ObjectIterator() if isinstance(obj,unreal.GameplayAbility)
                         and obj.get_class()==_cs_state["charge_class"] and obj.get_avatar_actor_from_actor_info()==boss)
            _cs_place(boss,start,-600,0)
            before=_cs_health(player)
            ability.call_method("BeginChargePath")
            _cs_place(boss,end,-600,0)
            actual_end=boss.get_actor_location()
            ability.call_method("HitAlongPath")
            after=_cs_health(player)
            ability.call_method("HitAlongPath")
            repeated=_cs_health(player)
            previous=ability.get_editor_property("PreviousTraceLocation")
            hit_actors=ability.get_editor_property("HitActors")
            passed=abs(before-after-expected)<0.05 and abs(after-repeated)<0.01 and abs(previous.x-actual_end.x)<0.01 and abs(previous.y-actual_end.y)<0.01 and abs(previous.z-actual_end.z)<0.01 and sum(a==player for a in hit_actors)==(1 if expected else 0)
            row={"case":label,"passed":passed,"expected_damage":expected,"actual_damage":before-after,
                 "repeat_damage":after-repeated,"start_x":start,"end_x":end,"target_x":target,"target_y":y,
                 "player_hits":sum(a==player for a in hit_actors),"previous_updated":(abs(previous.x-actual_end.x)<0.01 and abs(previous.y-actual_end.y)<0.01 and abs(previous.z-actual_end.z)<0.01)}
            _cs_state["cases"].append(row)
            if not passed:
                _cs_state["failures"].append(label)
            boss.destroy_actor()
            _cs_state.update(boss=None,phase="setup",index=_cs_state["index"]+1)
    except Exception:
        _cs_finish(traceback.format_exc())


_cs_handle=unreal.register_slate_post_tick_callback(_cs_tick)
_cs_level.editor_request_begin_play()
result={"started":True,"cases":len(_cs_cases),"output":_cs_output}
