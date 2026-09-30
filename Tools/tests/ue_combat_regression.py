"""실행 중인 필드 PIE와 ue_runtime.py가 필요한 전투 회귀 검사다."""
import json
import os
import time
import unreal

ROOT = os.path.abspath(unreal.Paths.project_saved_dir())
if "game_world" not in globals():
    raise RuntimeError("동일 브리지에 ue_runtime.py를 먼저 전달한다.")
game_world()

COMBAT_ROWS = []
COMBAT_EVENTS = []
COMBAT_SAMPLES = []
COMBAT_FAILURES = []
COMBAT_CASES = []
COMBAT_INDEX = 0
COMBAT_STAGE = 0
COMBAT_DEADLINE = 0.0
COMBAT_BEFORE = None
COMBAT_CASE_START = 0.0
COMBAT_HANDLE = None
COMBAT_LAST_HP = None
COMBAT_FRAME_DT = []
DUMMY = actor_named("Dummy_2")
for label in ("SparringGrunt_1", "SparringGrunt_2"):
    actor_named(label).call_method("SetDormant", args=(True,))


def record_case(label, expected, actual, passed, extra=None):
    row = {"case": label, "expected": expected, "actual": actual, "passed": bool(passed), "extra": extra}
    COMBAT_ROWS.append(row)
    if not passed:
        COMBAT_FAILURES.append(label)


def persist_combat(done=False):
    with open(os.path.join(ROOT, "audit-combat-result.json"), "w", encoding="utf-8") as stream:
        json.dump({"done":done,"cases":COMBAT_ROWS,"failures":COMBAT_FAILURES,"events":COMBAT_EVENTS,"frame_dt":COMBAT_FRAME_DT,"samples":COMBAT_SAMPLES},stream,ensure_ascii=False,indent=2)


def case(name, action, seconds, checker):
    COMBAT_CASES.append((name, action, seconds, checker))


def damage_check(name, expected):
    actual = COMBAT_BEFORE["dummy_hp"] - attributes(DUMMY)["Health"]
    record_case(name, expected, actual, abs(expected-actual)<0.05)


case("평타 1회", lambda: press("InputTag.Attack"), 2.0, lambda: damage_check("평타 1회",50))
case("같은 프레임 4연타", lambda: [press("InputTag.Attack") for i in range(4)], 3.5, lambda: damage_check("같은 프레임 4연타",270))
case("같은 프레임 8연타", lambda: [press("InputTag.Attack") for i in range(8)], 3.5, lambda: damage_check("같은 프레임 8연타",270))
case("Q",lambda:press("InputTag.Skill.1"),1.7,lambda:damage_check("Q 피해",150))
case("E",lambda:press("InputTag.Skill.2"),1.7,lambda:damage_check("E 피해",200))
case("R",lambda:press("InputTag.Skill.3"),1.7,lambda:damage_check("R 피해",125))
case("대시",lambda:press("InputTag.Dash"),1.0,lambda:record_case("대시 종료","Dashing/Invulnerable 해제",tags(player()),not any(t in tags(player()) for t in ("State.Dashing","State.Invulnerable"))))
case("점프",lambda:press("InputTag.Jump"),1.5,lambda:record_case("점프 종료","착지",position(player()),abs(position(player())[2]-COMBAT_BEFORE["z"])<10))


def guard_start():
    press("InputTag.Guard")
    record_case("가드 누름",True,"State.Guard" in tags(player()),"State.Guard" in tags(player()))
    # 실제 잡몹 전투 컴포넌트의 피해 함수를 호출해 가드 판정과 GE 적용을 검증한다.
    enemy=actor_named("SparringGrunt_1")
    teleport(enemy,[800,0,95],180)
    before=attributes(player())["Health"]
    combat(enemy).call_method("ApplyHit",args=(player(),1.0,300.0,0.0))
    actual=before-attributes(player())["Health"]
    record_case("정면 가드 피해",5,actual,abs(actual-5)<0.05)
    record_case("가드 경직 차단",False,"State.HitStun" in tags(player()),"State.HitStun" not in tags(player()))
    release("InputTag.Guard")
    record_case("가드 뗌",False,"State.Guard" in tags(player()),"State.Guard" not in tags(player()))
    before=attributes(player())["Health"]
    combat(enemy).call_method("ApplyHit",args=(player(),1.0,300.0,0.0))
    actual=before-attributes(player())["Health"]
    record_case("가드 해제 피해",25,actual,abs(actual-25)<0.05)
    record_case("일반 피격 경직",True,"State.HitStun" in tags(player()),"State.HitStun" in tags(player()))


case("가드와 피격",guard_start,1.0,lambda:None)


def cancel_start():
    press("InputTag.Attack")
    press("InputTag.Dash")
    active=tags(player())
    record_case("대시로 평타 취소","Dashing 및 Attacking 해제",active,"State.Dashing" in active and "State.Attacking" not in active)
    enemy=actor_named("SparringGrunt_1")
    before=attributes(player())["Health"]
    combat(enemy).call_method("ApplyHit",args=(player(),1.0,300.0,0.0))
    actual=before-attributes(player())["Health"]
    record_case("대시 중 피해 무시",0,actual,abs(actual)<0.05)
    record_case("대시 중 경직 차단",False,"State.HitStun" in tags(player()),"State.HitStun" not in tags(player()))


case("대시 취소 및 무적",cancel_start,1.5,lambda:None)


def low_resource():
    p=player()
    component=asc(p)
    # 테스트 준비: 기존 재생 GE만 제거하고 기존 비용 GE로 SP를 소비한다.
    component.remove_active_gameplay_effect_by_source_effect(unreal.load_class(None,"/Game/SoulCombat/GAS/Effects/GE_Regen_Player.GE_Regen_Player_C"),None,-1)
    effect=unreal.load_class(None,"/Game/SoulCombat/GAS/Effects/GE_Cost_Skill1.GE_Cost_Skill1_C")
    for i in range(5):
        component.apply_gameplay_effect_to_self(effect,1.0,component.make_effect_context())
    before=attributes(p)["Mana"]
    activated=press("InputTag.Skill.1")
    record_case("SP 부족 발동 거부",False,activated,activated is False, {"mana":before,"tags":tags(p)})


case("SP 부족",low_resource,1.0,lambda:record_case("SP 부족 피해 없음",0,COMBAT_BEFORE["dummy_hp"]-attributes(DUMMY)["Health"],abs(COMBAT_BEFORE["dummy_hp"]-attributes(DUMMY)["Health"])<0.05))


def combat_tick(delta):
    global COMBAT_INDEX,COMBAT_STAGE,COMBAT_DEADLINE,COMBAT_BEFORE,COMBAT_CASE_START,COMBAT_LAST_HP
    try:
        now=unreal.GameplayStatics.get_time_seconds(game_world())
        COMBAT_FRAME_DT.append(float(delta))
        hp=attributes(DUMMY)["Health"]
        if hp!=COMBAT_LAST_HP:
            COMBAT_EVENTS.append({"case_index":COMBAT_INDEX,"time":now,"dummy_hp":hp})
            COMBAT_LAST_HP=hp
        if COMBAT_INDEX>=len(COMBAT_CASES):
            unreal.unregister_slate_post_tick_callback(COMBAT_HANDLE)
            persist_combat(True)
            return
        name,action,seconds,checker=COMBAT_CASES[COMBAT_INDEX]
        if COMBAT_STAGE==0:
            reset_combat()
            COMBAT_STAGE=1
            COMBAT_DEADLINE=now+0.7
        elif COMBAT_STAGE==1 and now>=COMBAT_DEADLINE:
            COMBAT_BEFORE={"dummy_hp":attributes(DUMMY)["Health"],"z":position(player())[2]}
            before=attributes(player())
            response=action()
            after=attributes(player())
            COMBAT_SAMPLES.append({"case":name,"start":now,"response":response,"before":before,"after":after,"tags":tags(player())})
            if name in ("Q","E","R"):
                expected={"Q":20,"E":30,"R":25}[name]
                actual=before["Mana"]-after["Mana"]
                record_case(name+" SP 소비",expected,actual,abs(expected-actual)<0.05)
            if name=="Q":
                current=attributes(player())["Mana"]
                retry=press("InputTag.Skill.1")
                record_case("Q 쿨타임 중 재입력",False,retry,retry is False)
                record_case("Q 재입력 SP 미소비",current,attributes(player())["Mana"],abs(current-attributes(player())["Mana"])<0.05)
            if name=="대시":
                record_case("대시 스태미나",25,before["Stamina"]-after["Stamina"],abs(before["Stamina"]-after["Stamina"]-25)<0.05)
                record_case("대시 무적 태그",True,"State.Invulnerable" in tags(player()),"State.Invulnerable" in tags(player()))
            COMBAT_STAGE=2
            COMBAT_CASE_START=now
            COMBAT_DEADLINE=now+seconds
        elif COMBAT_STAGE==2:
            COMBAT_SAMPLES.append({"case":name,"time":now-COMBAT_CASE_START,"player_z":position(player())[2],"dummy_z":position(DUMMY)[2],"projectiles":sum(a.get_class().get_name()=="BP_WaveProjectile_C" for a in all_actors())})
            if now>=COMBAT_DEADLINE:
                checker()
                record_case(name+" 상태 종료",False,any(t in tags(player()) for t in ("State.Attacking","State.Casting","State.Dashing","State.HitStun")),not any(t in tags(player()) for t in ("State.Attacking","State.Casting","State.Dashing","State.HitStun")))
                COMBAT_INDEX+=1
                COMBAT_STAGE=0
                persist_combat()
    except Exception:
        unreal.unregister_slate_post_tick_callback(COMBAT_HANDLE)
        import traceback
        COMBAT_FAILURES.append(traceback.format_exc())
        persist_combat(True)


COMBAT_HANDLE=unreal.register_slate_post_tick_callback(combat_tick)
result={"started":True,"cases":len(COMBAT_CASES)}
