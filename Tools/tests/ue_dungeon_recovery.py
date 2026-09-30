"""실제 PIE에서 Mob1·Mob2·Boss의 사망·체크포인트 복구를 검사한다.

PythonScriptPlugin 작업 브리지에서 새 PIE를 시작하며 실제 GameInstance의
EnterDungeon을 사용한다. 각 방은 새 던전 월드에서 겹침으로 시작한다.
테스트 중 적 AI의 Think 타이머·Tick만 멈춰 부활 직후 추가 피해를 분리한다.
부분 진행과 자원 소모·사망은 기존 GE로 만들며 에셋은 수정·저장하지 않는다.
"""
import json
import os
import time
import traceback
import unreal


if globals().get("_recovery_handle") is not None:
    raise RuntimeError("이전 던전 복구 검사가 아직 진행 중이다.")

_recovery_editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
_recovery_level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if _recovery_editor.get_game_world() is not None:
    raise RuntimeError("기존 PIE를 종료한 뒤 새 던전 복구 검사를 시작한다.")

_recovery_output = os.path.join(unreal.Paths.project_saved_dir(), "dungeon-recovery-result.json")
_recovery_rooms = [("Room_Mob1", [1300, 0, 100]),
                   ("Room_Mob2", [5700, 0, 100]),
                   ("Room_Boss", [8100, 0, 100])]
_recovery_state = {"phase": "waiting_pie", "since": time.monotonic(),
                   "index": 0, "done": False, "cases": [], "failures": [],
                   "rooms": [], "old_world": None}
_recovery_handle = None
_recovery_combat_class = None
_recovery_damage_class = None
_recovery_damage_tag = None


def _recovery_save():
    data = {key: _recovery_state[key] for key in ("phase", "done", "cases", "failures", "rooms")}
    data["passed"] = _recovery_state["done"] and not _recovery_state["failures"]
    data["test"] = "실제 에셋 던전의 사망·자원 복구·체크포인트·진행 유지"
    data["fixture"] = "각 방은 EnterDungeon으로 새 월드. 적 AI의 Think와 Tick을 PIE에서만 정지."
    data["limits"] = "적 접근·전투 난이도·방 초기화 재시작·실제 키 입력을 검증하지 않는다."
    with open(_recovery_output, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)


def _recovery_row(name, passed, details=None):
    _recovery_state["cases"].append({"case": name, "passed": bool(passed), "data": details})
    if not passed:
        _recovery_state["failures"].append(name)
    _recovery_save()


def _recovery_finish():
    global _recovery_handle
    _recovery_state["done"] = True
    _recovery_state["phase"] = "finished"
    _recovery_save()
    if _recovery_handle is not None:
        unreal.unregister_slate_post_tick_callback(_recovery_handle)
        _recovery_handle = None
    _recovery_state["old_world"] = None
    _recovery_level.editor_request_end_play()


def _recovery_phase(name):
    _recovery_state["phase"] = name
    _recovery_state["since"] = time.monotonic()


def _recovery_valid(value):
    return value is not None and unreal.SystemLibrary.is_valid(value)


def _recovery_asc(actor):
    component = actor.get_component_by_class(unreal.AbilitySystemComponent)
    if component is None:
        raise RuntimeError(actor.get_path_name() + "에 ASC가 없다.")
    return component


def _recovery_combat(actor):
    component = actor.get_component_by_class(_recovery_combat_class)
    if component is None:
        raise RuntimeError(actor.get_path_name() + "에 전투 컴포넌트가 없다.")
    return component


def _recovery_attributes(actor):
    component = _recovery_asc(actor)
    values = {}
    for attribute in component.get_all_attributes():
        name = unreal.AbilitySystemLibrary.get_debug_string_from_gameplay_attribute(attribute).split(".")[-1]
        value, found = component.get_gameplay_attribute_value(attribute)
        if found:
            values[name] = value
    return values


def _recovery_tags(actor):
    container = unreal.GameplayTagLibrary.get_owned_gameplay_tags(_recovery_asc(actor))
    return sorted(unreal.GameplayTagLibrary.get_debug_string_from_gameplay_tag(tag)
                  for tag in unreal.GameplayTagLibrary.break_gameplay_tag_container(container))


def _recovery_position(actor):
    value = actor.get_actor_location()
    return [value.x, value.y, value.z]


def _recovery_actor(world, label):
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
    return next(actor for actor in actors if actor.get_actor_label() == label)


def _recovery_damage(source, target, magnitude):
    source_asc = _recovery_asc(source)
    spec = source_asc.make_outgoing_spec(_recovery_damage_class, 1.0, source_asc.make_effect_context())
    spec = unreal.AbilitySystemLibrary.assign_tag_set_by_caller_magnitude(spec, _recovery_damage_tag, magnitude)
    # Instant GE 핸들 유효성 대신 적용 후 실제 Health·Dead 상태로 판정한다.
    _recovery_asc(target).apply_gameplay_effect_spec_to_self(spec)


def _recovery_apply_cost(actor, effect_name, count):
    component = _recovery_asc(actor)
    effect = unreal.load_class(None, "/Game/SoulCombat/GAS/Effects/" + effect_name + "." + effect_name + "_C")
    if effect is None:
        raise RuntimeError("자원 소모 GE를 찾지 못했다: " + effect_name)
    for unused in range(count):
        component.apply_gameplay_effect_to_self(effect, 1.0, component.make_effect_context())


def _recovery_freeze_enemy_ai(world):
    names = []
    for pawn in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Pawn):
        controller = pawn.get_controller()
        if _recovery_valid(controller) and controller.get_class().get_name() == "BP_EnemyAIController_C":
            unreal.SystemLibrary.clear_timer(controller, "Think")
            controller.set_actor_tick_enabled(False)
            movement = pawn.get_component_by_class(unreal.CharacterMovementComponent)
            if movement is not None:
                movement.stop_movement_immediately()
            names.append(pawn.get_actor_label())
    return sorted(names)


def _recovery_room_state(room):
    state = {"started": bool(room.get_editor_property("bStarted")),
             "cleared": bool(room.get_editor_property("bCleared")), "doors": {}, "alive_enemies": []}
    for property_name in ("EntryDoor", "ExitDoor"):
        door = room.get_editor_property(property_name)
        state["doors"][property_name] = bool(door.get_editor_property("bIsOpen")) if _recovery_valid(door) else None
    for enemy in room.get_editor_property("Enemies"):
        if _recovery_valid(enemy) and not _recovery_combat(enemy).get_editor_property("bIsDead"):
            state["alive_enemies"].append({"label": enemy.get_actor_label(),
                                           "active": bool(enemy.get_editor_property("bActive"))})
    state["alive_enemies"].sort(key=lambda value: value["label"])
    if room.get_actor_label().startswith("Room_Mob"):
        state["wave"] = int(room.get_editor_property("CurrentWave"))
        state["alive_count"] = int(room.get_editor_property("AliveCount"))
    else:
        boss = room.get_editor_property("CurrentBoss")
        state["boss"] = {"label": boss.get_actor_label(), "health": _recovery_attributes(boss)["Health"],
                         "attack": _recovery_attributes(boss)["AttackPower"],
                         "enraged": bool(boss.get_editor_property("bEnraged"))}
    return state


def _recovery_begin_travel(world):
    _recovery_state["old_world"] = world
    instance = unreal.GameplayStatics.get_game_instance(world)
    instance.call_method("EnterDungeon", args=("L_Dungeon_01",))
    _recovery_phase("waiting_dungeon")


def _recovery_tick(delta):
    global _recovery_combat_class, _recovery_damage_class, _recovery_damage_tag
    try:
        now = time.monotonic()
        phase = _recovery_state["phase"]
        world = _recovery_editor.get_game_world()
        if now - _recovery_state["since"] > 20:
            raise RuntimeError("검사 단계 시간 초과: " + phase)
        if phase == "waiting_pie":
            if world is None or unreal.GameplayStatics.get_time_seconds(world) < 0.4:
                return
            _recovery_combat_class = unreal.load_class(None, "/Game/SoulCombat/Components/AC_CombatComponent.AC_CombatComponent_C")
            _recovery_damage_class = unreal.load_class(None, "/Game/SoulCombat/GAS/Effects/GE_Damage.GE_Damage_C")
            _recovery_damage_tag = unreal.GameplayTag()
            _recovery_damage_tag.import_text('(TagName="Data.Damage")')
            if _recovery_combat_class is None or _recovery_damage_class is None:
                raise RuntimeError("실제 전투 컴포넌트 또는 GE_Damage를 찾지 못했다.")
            if not unreal.GameplayTagLibrary.is_gameplay_tag_valid(_recovery_damage_tag):
                raise RuntimeError("Data.Damage 태그가 등록되지 않았다.")
            _recovery_begin_travel(world)
            return
        if world is None:
            return
        player = unreal.GameplayStatics.get_player_pawn(world, 0)
        if not _recovery_valid(player):
            return
        name, destination = _recovery_rooms[_recovery_state["index"]]
        if phase == "waiting_dungeon":
            if world == _recovery_state["old_world"] or world.get_name() != "L_Dungeon_01":
                return
            if unreal.GameplayStatics.get_time_seconds(world) < 0.4:
                return
            _recovery_state["old_world"] = None
            room = _recovery_actor(world, name)
            _recovery_state["room"] = room
            _recovery_state["frozen_ai"] = _recovery_freeze_enemy_ai(world)
            _recovery_row(name + " 실제 던전 재입장", not room.get_editor_property("bStarted"),
                          {"map": world.get_name(), "frozen_ai": _recovery_state["frozen_ai"]})
            player.set_actor_location_and_rotation(unreal.Vector(*destination), unreal.Rotator(), False, True)
            _recovery_phase("waiting_room")
        elif phase == "waiting_room":
            room = _recovery_state["room"]
            if not room.get_editor_property("bStarted"):
                return
            if now - _recovery_state["since"] < 0.7:
                return
            initial = _recovery_room_state(room)
            _recovery_row(name + " 겹침으로 전투 시작", initial["started"] and not initial["cleared"]
                          and initial["doors"]["EntryDoor"] is False
                          and initial["doors"]["ExitDoor"] in (False, None), initial)
            if name.startswith("Room_Mob"):
                enemy = next(enemy for enemy in room.get_editor_property("Enemies")
                             if _recovery_valid(enemy) and enemy.get_editor_property("bActive")
                             and not _recovery_combat(enemy).get_editor_property("bIsDead"))
                _recovery_state["initial_alive_count"] = initial["alive_count"]
                _recovery_damage(player, enemy, 1000000.0)
            else:
                boss = room.get_editor_property("CurrentBoss")
                values = _recovery_attributes(boss)
                raw = values["MaxHealth"] * 0.6 * (100.0 + values["Defense"]) / 100.0
                _recovery_damage(player, boss, raw)
            _recovery_phase("waiting_partial_progress")
        elif phase == "waiting_partial_progress":
            if now - _recovery_state["since"] < 0.15:
                return
            room = _recovery_state["room"]
            before = _recovery_room_state(room)
            if name.startswith("Room_Mob"):
                good = before["alive_count"] == _recovery_state["initial_alive_count"] - 1 and before["alive_count"] > 0
            else:
                good = 0 < before["boss"]["health"] < 3000 and before["boss"]["enraged"]
            _recovery_row(name + " 실제 피해로 부분 진행 생성", good, before)
            _recovery_state["before"] = before
            arrow = room.get_editor_property("RespawnPoint").get_world_location()
            _recovery_state["checkpoint"] = [arrow.x, arrow.y, arrow.z]
            _recovery_state["respawn_delay"] = float(_recovery_combat(player).get_editor_property("RespawnDelay"))
            _recovery_apply_cost(player, "GE_Cost_Skill1", 5)
            _recovery_apply_cost(player, "GE_Cost_Dash", 4)
            depleted = _recovery_attributes(player)
            _recovery_row(name + " 실제 비용 GE로 자원 소모", depleted["Mana"] < depleted["MaxMana"]
                          and depleted["Stamina"] < depleted["MaxStamina"], depleted)
            _recovery_damage(player, player, 1000000.0)
            _recovery_state["death_world_time"] = unreal.GameplayStatics.get_time_seconds(world)
            values = _recovery_attributes(player)
            _recovery_row(name + " 실제 GE_Damage로 사망", values["Health"] <= 0.01
                          and "State.Dead" in _recovery_tags(player)
                          and _recovery_combat(player).get_editor_property("bIsDead"),
                          {"attributes": values, "tags": _recovery_tags(player)})
            _recovery_phase("waiting_respawn")
        elif phase == "waiting_respawn":
            values = _recovery_attributes(player)
            if "State.Dead" in _recovery_tags(player) or values["Health"] <= 0.01:
                return
            elapsed = unreal.GameplayStatics.get_time_seconds(world) - _recovery_state["death_world_time"]
            delay = _recovery_state["respawn_delay"]
            actual = _recovery_position(player)
            expected = _recovery_state["checkpoint"]
            after = _recovery_room_state(_recovery_state["room"])
            _recovery_row(name + " 설정된 3초 뒤 부활", abs(delay - 3.0) < 0.01
                          and delay - 0.15 <= elapsed <= delay + 1.0,
                          {"configured_delay": delay, "elapsed_world_seconds": elapsed})
            for current, maximum in (("Health", "MaxHealth"), ("Mana", "MaxMana"), ("Stamina", "MaxStamina")):
                _recovery_row(name + " " + current + " 최대치 복구", abs(values[current] - values[maximum]) < 0.05,
                              {"actual": values[current], "maximum": values[maximum]})
            _recovery_row(name + " Dead 태그·사망 상태 해제", "State.Dead" not in _recovery_tags(player)
                          and not _recovery_combat(player).get_editor_property("bIsDead"), _recovery_tags(player))
            _recovery_row(name + " 방 체크포인트 좌표 복구", abs(actual[0] - expected[0]) < 2.0
                          and abs(actual[1] - expected[1]) < 2.0 and abs(actual[2] - expected[2]) < 30.0,
                          {"expected_arrow": expected, "actual": actual, "z_tolerance": "접지 후 캡슐 위치 30cm"})
            _recovery_row(name + " 입출구 상태 유지", after["doors"] == _recovery_state["before"]["doors"],
                          {"before": _recovery_state["before"]["doors"], "after": after["doors"]})
            _recovery_row(name + " 웨이브·생존 적·보스 부분 진행 유지", after == _recovery_state["before"],
                          {"before": _recovery_state["before"], "after": after})
            _recovery_state["rooms"].append({"room": name, "before_death": _recovery_state["before"],
                                             "after_respawn": after, "attributes": values,
                                             "checkpoint": expected, "location": actual})
            _recovery_state["index"] += 1
            if _recovery_state["index"] == len(_recovery_rooms):
                _recovery_finish()
            else:
                _recovery_begin_travel(world)
    except Exception:
        _recovery_row("복구 검사 실행", False, {"phase": _recovery_state["phase"], "error": traceback.format_exc()})
        _recovery_finish()


_recovery_save()
_recovery_handle = unreal.register_slate_post_tick_callback(_recovery_tick)
_recovery_level.editor_request_begin_play()
result = {"started": True, "output": _recovery_output, "rooms": [item[0] for item in _recovery_rooms]}
