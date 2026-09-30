"""실행 중인 던전 PIE와 ue_runtime.py가 필요한 방 진행·복귀 회귀 검사다."""
import json
import os
import time
import unreal

ROOT = os.path.abspath(unreal.Paths.project_saved_dir())
if "game_world" not in globals():
    raise RuntimeError("동일 브리지에 ue_runtime.py를 먼저 전달한다.")
game_world()

FLOW_ROWS=[]
FLOW_FAILURES=[]
FLOW_EVENTS=[]
FLOW_INDEX=0
FLOW_STAGE=0
FLOW_TIME=0.0
FLOW_HANDLE=None
FLOW_LAST_WAVE=None
FLOW_ROOMS=[('Room_Mob1',[1300,0,100]),('Room_Event',[3700,0,100]),('Room_Mob2',[5700,0,100]),('Room_Boss',[8100,0,100])]


def flow_row(name,passed,data=None):
    FLOW_ROWS.append({'case':name,'passed':bool(passed),'data':data})
    if not passed:
        FLOW_FAILURES.append(name)


def flow_save(done=False):
    with open(os.path.join(ROOT,'audit-flow-result.json'),'w',encoding='utf-8') as stream:
        json.dump({'done':done,'cases':FLOW_ROWS,'failures':FLOW_FAILURES,'events':FLOW_EVENTS},stream,ensure_ascii=False,indent=2)


def flow_tick(delta):
    global FLOW_INDEX,FLOW_STAGE,FLOW_TIME,FLOW_LAST_WAVE
    try:
        now=time.monotonic()
        if FLOW_INDEX<len(FLOW_ROOMS):
            name,xyz=FLOW_ROOMS[FLOW_INDEX]
            room=actor_named(name)
            if FLOW_STAGE==0:
                teleport(player(),xyz,0)
                FLOW_TIME=now
                FLOW_STAGE=1
                FLOW_LAST_WAVE=None
            elif FLOW_STAGE==1 and now-FLOW_TIME>0.5:
                flow_row(name+' 시작',room.get_editor_property('bStarted'))
                entry=room.get_editor_property('EntryDoor')
                if entry:
                    flow_row(name+' 입구 닫힘',not entry.get_editor_property('bIsOpen'))
                if name=='Room_Boss':
                    hud=pc().get_editor_property('HUD')
                    bar=hud.get_editor_property('BossBar')
                    flow_row('보스 HP 바 표시',str(bar.get_visibility())!='SlateVisibility.COLLAPSED',{'visibility':str(bar.get_visibility())})
                FLOW_STAGE=2
            elif FLOW_STAGE==2:
                if name.startswith('Room_Mob'):
                    wave=room.get_editor_property('CurrentWave')
                    if wave!=FLOW_LAST_WAVE:
                        FLOW_EVENTS.append({'room':name,'wave':wave})
                        FLOW_LAST_WAVE=wave
                for enemy in room.get_editor_property('Enemies'):
                    if enemy and enemy.get_editor_property('bActive') and not combat(enemy).get_editor_property('bIsDead'):
                        combat(player()).call_method('ApplyHit',args=(enemy,10000.0,0.0,0.0))
                if room.get_editor_property('bCleared'):
                    data={'started':room.get_editor_property('bStarted'),'cleared':room.get_editor_property('bCleared')}
                    flow_row(name+' 클리어',True,data)
                    exit_door=room.get_editor_property('ExitDoor')
                    if exit_door:
                        flow_row(name+' 출구 열림',exit_door.get_editor_property('bIsOpen'))
                    if name=='Room_Event':
                        stats=attributes(player())
                        data={'destroyed':room.get_editor_property('DestroyedCount'),'attack':stats['AttackPower'],'health':stats['Health'],'mana':stats['Mana']}
                        flow_row('이벤트 성공 보상',data['destroyed']==3 and abs(data['attack']-65)<0.05 and abs(data['health']-1000)<0.05 and abs(data['mana']-100)<0.05,data)
                    FLOW_INDEX+=1
                    FLOW_STAGE=0
                    FLOW_TIME=now
                    flow_save()
                elif now-FLOW_TIME>15:
                    raise RuntimeError(name+' 클리어 시간 초과')
        else:
            map_name=game_world().get_name()
            if FLOW_STAGE==0 and map_name=='L_Dungeon_01':
                widget=pc().get_editor_property('ClearWidget')
                if widget:
                    flow_row('클리어 창 생성',True,{'widget':widget.get_path_name()})
                    FLOW_STAGE=1
            if map_name=='L_CombatField':
                loc=position(player())
                stats=attributes(player())
                flow_row('클리어 자동 필드 복귀',abs(loc[0])<1 and abs(loc[1]-1450)<1,{'location':loc,'health':stats['Health'],'cursor':pc().get_editor_property('bShowMouseCursor')})
                flow_row('복귀 UI 정리',pc().get_editor_property('EntryWidget') is None and pc().get_editor_property('ClearWidget') is None and not pc().get_editor_property('bShowMouseCursor'))
                unreal.unregister_slate_post_tick_callback(FLOW_HANDLE)
                flow_save(True)
            elif now-FLOW_TIME>15:
                raise RuntimeError('클리어 복귀 시간 초과')
    except Exception:
        import traceback
        FLOW_FAILURES.append(traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(FLOW_HANDLE)
        flow_save(True)


flow_row('던전 입장',game_world().get_name()=='L_Dungeon_01')
start_room=actor_named('Room_Start')
flow_row('스폰 시 Start 자동 클리어',start_room.get_editor_property('bStarted') and start_room.get_editor_property('bCleared'))
FLOW_HANDLE=unreal.register_slate_post_tick_callback(flow_tick)
result={'started':True}
