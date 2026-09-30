"""실행 중인 필드 PIE와 ue_runtime.py가 필요한 입력 간격·검기 회귀 검사다."""
import json
import os
import time
import unreal

ROOT = os.path.abspath(unreal.Paths.project_saved_dir())
if "game_world" not in globals():
    raise RuntimeError("동일 브리지에 ue_runtime.py를 먼저 전달한다.")
game_world()

DUMMY = actor_named("Dummy_2")
for label in ("SparringGrunt_1", "SparringGrunt_2"):
    actor_named(label).call_method("SetDormant", args=(True,))

TIMING_ROWS=[]
TIMING_INDEX=0
TIMING_STAGE=0
TIMING_START=0.0
TIMING_NEXT=0
TIMING_PRESSES=[]
TIMING_HANDLE=None
TIMING_FAILURES=[]
TIMING_DUMMIES=[actor_named("Dummy_1"),actor_named("Dummy_2"),actor_named("Dummy_3")]


def timing_save(done):
    with open(os.path.join(ROOT,"audit-timing-result.json"),"w",encoding="utf-8") as stream:
        json.dump({"done":done,"cases":TIMING_ROWS,"failures":TIMING_FAILURES},stream,ensure_ascii=False,indent=2)


def timing_tick(delta):
    global TIMING_INDEX,TIMING_STAGE,TIMING_START,TIMING_NEXT,TIMING_PRESSES
    try:
        now=unreal.GameplayStatics.get_time_seconds(game_world())
        if TIMING_INDEX>=3:
            unreal.unregister_slate_post_tick_callback(TIMING_HANDLE)
            timing_save(True)
            return
        if TIMING_STAGE==0:
            reset_combat()
            TIMING_STAGE=1
            TIMING_START=now
            TIMING_NEXT=0
            TIMING_PRESSES=[]
            if TIMING_INDEX==2:
                for target,xyz in zip(TIMING_DUMMIES,([800,-50,95],[1000,0,95],[1200,50,95])):
                    restore(target)
                    teleport(target,xyz,180)
        elif TIMING_STAGE==1 and now-TIMING_START>0.7:
            TIMING_STAGE=2
            TIMING_START=now
        elif TIMING_STAGE==2:
            elapsed=now-TIMING_START
            if TIMING_INDEX<2:
                interval=[0.1,0.35][TIMING_INDEX]
                if TIMING_NEXT<4 and elapsed>=TIMING_NEXT*interval:
                    press("InputTag.Attack")
                    TIMING_PRESSES.append(elapsed)
                    TIMING_NEXT+=1
                if elapsed>=3.6:
                    actual=5000-attributes(DUMMY)["Health"]
                    row={"case":"4연타 간격 "+str(interval),"expected":270,"actual":actual,"press_times":TIMING_PRESSES,"passed":abs(actual-270)<0.05}
                    TIMING_ROWS.append(row)
                    if not row["passed"]:
                        TIMING_FAILURES.append(row["case"])
                    TIMING_INDEX+=1
                    TIMING_STAGE=0
                    timing_save(False)
            else:
                if TIMING_NEXT==0:
                    press("InputTag.Skill.3")
                    TIMING_NEXT=1
                if elapsed>=2:
                    actual=[5000-attributes(d)["Health"] for d in TIMING_DUMMIES]
                    row={"case":"R 3대상 관통 및 중복 타격 방지","expected":[125,125,125],"actual":actual,"passed":all(abs(v-125)<0.05 for v in actual)}
                    TIMING_ROWS.append(row)
                    if not row["passed"]:
                        TIMING_FAILURES.append(row["case"])
                    TIMING_INDEX+=1
                    TIMING_STAGE=0
    except Exception:
        import traceback
        TIMING_FAILURES.append(traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(TIMING_HANDLE)
        timing_save(True)


TIMING_HANDLE=unreal.register_slate_post_tick_callback(timing_tick)
result={"started":True}
