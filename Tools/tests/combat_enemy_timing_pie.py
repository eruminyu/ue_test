"""실제 보스 BP의 내려찍기 판정과 돌진 시작·중간·끝 경로 회귀.

PIE의 기존 플레이어와 런타임에 생성한 실제 BP_Enemy_Boss를 사용한다.
자율 AI만 비활성화하고 GAS 발동·이동·피해는 게임 구현을 그대로 실행한다.
"""
import json
import os
import traceback
import unreal

_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if _world is None:
    raise RuntimeError("PIE를 먼저 시작해야 합니다.")
_player = unreal.GameplayStatics.get_player_pawn(_world, 0)
_combat_class = unreal.load_class(None,"/Game/SoulCombat/Components/AC_CombatComponent.AC_CombatComponent_C")
_boss_class = unreal.load_class(None,"/Game/SoulCombat/Characters/Enemies/BP_Enemy_Boss.BP_Enemy_Boss_C")
_grunt_class = unreal.load_class(None,"/Game/SoulCombat/Characters/Enemies/BP_Enemy_Grunt.BP_Enemy_Grunt_C")
_restore_class = unreal.load_class(None,"/Game/SoulCombat/GAS/Effects/GE_RestoreFull.GE_RestoreFull_C")
_statics = unreal.get_default_object(unreal.GameplayStatics)
_rows, _failures, _samples = [], [], []
_cases = [("내려찍기 배율0.25",0.25,250,2,125,False),
          ("보스 근접 배율0.5",0.5,200,1,60,False),("잡몹 근접 배율0.5",0.5,200,0,25,False),
          ("돌진 시작점",1,80,3,90,False),("돌진 첫 표본 사이",1,625,3,90,False),
          ("돌진 둘째 표본 사이",1,1125,3,90,False),("돌진 끝점",1,1490,3,90,False),
          ("돌진 시작점 옆걸음",1,80,3,90,True),("돌진 첫 표본 사이 옆걸음",1,625,3,90,True),
          ("돌진 둘째 표본 사이 옆걸음",1,1125,3,90,True),("돌진 끝점 옆걸음",1,1400,3,90,True),
          ("돌진 경로 밖 옆걸음",1,1650,3,0,True)]
_index,_stage,_start,_last_hp,_timing_bad,_hits=0,0,0.0,None,False,0
_boss=None
_sidestep_done=False
_handle=None
_output=os.path.join(unreal.Paths.project_saved_dir(),"combat-enemy-timing-result.json")


def _health(actor):
    c=actor.get_component_by_class(unreal.AbilitySystemComponent)
    attr=next(a for a in c.get_all_attributes() if unreal.AbilitySystemLibrary.get_debug_string_from_gameplay_attribute(a).endswith(".Health"))
    return c.get_gameplay_attribute_value(attr)[0]


def _restore(actor):
    c=actor.get_component_by_class(unreal.AbilitySystemComponent)
    c.apply_gameplay_effect_to_self(_restore_class,1,c.make_effect_context())


def _press(number):
    t=unreal.GameplayTag()
    t.import_text('(TagName="InputTag.AI.Attack.'+str(number if number else 1)+'")')
    return _boss.get_component_by_class(_combat_class).call_method("PressInput",args=(t,))


def _place(actor,x,y,yaw):
    actor.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
    actor.set_actor_location_and_rotation(unreal.Vector(x,y,95),unreal.Rotator(yaw=yaw),False,True)


def _persist(done):
    with open(_output,"w",encoding="utf-8") as f:
        json.dump({"done":done,"cases":_rows,"failures":_failures,"samples":_samples},f,ensure_ascii=False,indent=2)


for _actor in unreal.GameplayStatics.get_all_actors_of_class(_world,unreal.Actor):
    if _actor.get_actor_label().startswith("SparringGrunt_"):
        _actor.call_method("SetDormant",args=(True,))


def _tick(delta):
    global _index,_stage,_start,_last_hp,_timing_bad,_hits,_boss,_sidestep_done
    try:
        now=unreal.GameplayStatics.get_time_seconds(_world)
        if _index>=len(_cases):
            if _boss:
                _boss.destroy_actor()
            unreal.unregister_slate_post_tick_callback(_handle)
            _persist(True)
            return
        label,dilation,target_x,ability,expected,sidestep=_cases[_index]
        if _stage==0:
            if _boss:
                _boss.destroy_actor()
            _restore(_player)
            _player.mesh.get_anim_instance().montage_stop(0)
            transform=unreal.Transform(location=unreal.Vector(0,-600,95))
            _boss=_statics.call_method("BeginDeferredActorSpawnFromClass",args=(_world,_grunt_class if ability==0 else _boss_class,transform,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            _boss.set_editor_property("bStartDormant",False)
            _statics.call_method("FinishSpawningActor",args=(_boss,transform,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            controller=_boss.get_controller()
            if controller:
                unreal.SystemLibrary.clear_timer(controller,"Think")
                controller.set_actor_tick_enabled(False)
            if ability in (0,1,2):
                _place(_boss,0,-600,90)
                _place(_player,0,-600+target_x,180)
            else:
                _place(_boss,0,-600,0)
                _place(_player,target_x,-600,180)
            _stage,_start=1,now
        elif _stage==1 and now-_start>0.7:
            _boss.custom_time_dilation=dilation
            _last_hp,_timing_bad,_hits=_health(_player),False,0
            _sidestep_done=False
            started=_press(ability)
            if not started:
                raise RuntimeError(label+": GAS 발동 거부")
            _stage,_start=2,now
        elif _stage==2:
            if sidestep and not _sidestep_done and now-_start>=0.51:
                _place(_player,target_x,-420,180)
                _sidestep_done=True
            hp=_health(_player)
            anim=_boss.mesh.get_anim_instance()
            montage=anim.get_current_active_montage()
            pos=anim.montage_get_position(montage) if montage else None
            point=_boss.get_actor_location()
            elapsed=now-_start
            if hp<_last_hp-0.01:
                _hits+=1
                _samples.append({"case":label,"elapsed":elapsed,"boss_x":point.x,"target_x":_player.get_actor_location().x,
                                 "damage":_last_hp-hp,"montage_position":pos,"montage":montage.get_path_name() if montage else None})
                if ability==2 and (pos is None or pos<1.25-0.04):
                    _timing_bad=True
                if ability==1 and (pos is None or pos<2.4-0.04):
                    _timing_bad=True
                if ability==0 and (pos is None or pos<0.45-0.04):
                    _timing_bad=True
                _last_hp=hp
            if elapsed>=(6.0 if ability==2 else (4.0 if ability in (0,1) else 2.0)):
                actual=1000-_health(_player)
                passed=abs(actual-expected)<0.05 and _hits==(1 if expected>0 else 0) and not _timing_bad
                row={"case":label,"passed":passed,"expected_damage":expected,"actual_damage":actual,"hits":_hits,
                     "hit_before_animation_frame":_timing_bad,"end_x":point.x,
                     "player_pawn_response":str(_player.capsule_component.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN))}
                _rows.append(row)
                if not passed:
                    _failures.append(label)
                _index,_stage=_index+1,0
                _persist(False)
    except Exception:
        _failures.append(traceback.format_exc())
        if _boss:
            _boss.destroy_actor()
        unreal.unregister_slate_post_tick_callback(_handle)
        _persist(True)


_handle=unreal.register_slate_post_tick_callback(_tick)
_persist(False)
result={"started":True,"cases":len(_cases),"output":_output}
