"""실제 스파링 AI의 범위·접근·공격·대상 사망을 새 PIE에서 관찰한다.

검증 대상의 기존 Think 타이머와 Tick은 변경하지 않는다. Think와
PressInput을 직접 호출하지 않고, 다른 AI만 실제 SetDormant로 격리한다.
플레이어의 PIE CharacterMovement만 비활성화해 낙하·넉백 이동을 분리한다.
HP 증가는 허용하며, 공격 피해량은 실제 컨트롤러의 숫자 위젯과 대조한다.
게임 에셋은 수정·저장하지 않으며 전체 실시간 제한은 40초다.
"""
import json
import math
import os
import time
import traceback
import unreal


if globals().get("_ai_handle") is not None:
    raise RuntimeError("이전 자율 AI 검사가 아직 진행 중이다.")
_ai_editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
_ai_level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if _ai_editor.get_game_world() is not None:
    raise RuntimeError("기존 PIE를 종료한 뒤 새 자율 AI 검사를 시작한다.")
_ai_output = os.path.join(unreal.Paths.project_saved_dir(), "ai-autonomy-result.json")
_ai_state = {"phase": "waiting", "created": time.monotonic(), "since": 0.0,
             "done": False, "checks": [], "samples": [], "config": {},
             "last_sample": -1.0, "dormant_others": [], "player": None}
_ai_handle = None


def _ai_valid(actor):
    return actor is not None and unreal.SystemLibrary.is_valid(actor)


def _ai_attributes(actor):
    component = actor.get_component_by_class(unreal.AbilitySystemComponent)
    if component is None:
        raise RuntimeError(actor.get_path_name() + "에 ASC가 없다.")
    values = {}
    for attribute in component.get_all_attributes():
        name = unreal.AbilitySystemLibrary.get_debug_string_from_gameplay_attribute(attribute).split(".")[-1]
        value, found = component.get_gameplay_attribute_value(attribute)
        if found:
            values[name] = value
    return values


def _ai_tags(actor):
    component = actor.get_component_by_class(unreal.AbilitySystemComponent)
    container = unreal.GameplayTagLibrary.get_owned_gameplay_tags(component)
    return sorted(unreal.GameplayTagLibrary.get_debug_string_from_gameplay_tag(tag)
                  for tag in unreal.GameplayTagLibrary.break_gameplay_tag_container(container))


def _ai_position(actor):
    location = actor.get_actor_location()
    return [location.x, location.y, location.z]


def _ai_damage_numbers():
    numbers = []
    for actor in _ai_state["feedback"].get_editor_property("DamageActors"):
        if not _ai_valid(actor):
            continue
        component = actor.get_component_by_class(unreal.WidgetComponent)
        widget = component.get_user_widget_object() if component is not None else None
        valid_widget = _ai_valid(widget) and widget.get_class() == _ai_state["number_widget_class"]
        numbers.append({"actor": actor.get_path_name(),
                        "widget": widget.get_path_name() if _ai_valid(widget) else None,
                        "valid_widget": bool(valid_widget),
                        "damage": float(widget.get_editor_property("DamageValue")) if valid_widget else None,
                        "guarded": bool(widget.get_editor_property("bGuardedValue")) if valid_widget else None})
    return numbers


def _ai_save(error=None):
    output = {key: _ai_state[key] for key in ("phase", "done", "checks", "samples", "config")}
    output.update({"passed": _ai_state["done"] and error is None
                   and all(row["passed"] for row in _ai_state["checks"]), "error": error,
                   "test": "실제 스파링 AI의 자연 타이머·이동·공격·대상 사망",
                   "fixture": "다른 AI 휴면, PIE 플레이어 MovementMode.NONE, 단계별 플레이어 배치",
                   "limits": "장애물 우회·던전 난이도·물리 입력·화면·소리는 검사하지 않는다."})
    with open(_ai_output, "w", encoding="utf-8") as stream:
        json.dump(output, stream, ensure_ascii=False, indent=2)


def _ai_check(name, condition, details=None):
    _ai_state["checks"].append({"name": name, "passed": bool(condition), "details": details})
    if not condition:
        raise AssertionError(name + ": " + str(details))


def _ai_finish(error=None):
    global _ai_handle
    if _ai_state["done"]:
        return
    cleanup_errors = []
    if _ai_valid(_ai_state.get("player")) and "movement" in _ai_state:
        try:
            _ai_state["movement"].set_movement_mode(_ai_state["original_mode"], _ai_state["original_custom_mode"])
        except Exception:
            cleanup_errors.append(traceback.format_exc())
    for actor, was_active in _ai_state["dormant_others"]:
        if _ai_valid(actor):
            try:
                actor.call_method("SetDormant", args=(not was_active,))
            except Exception:
                cleanup_errors.append(traceback.format_exc())
    if cleanup_errors:
        error = (error or "") + "\nPIE 설정 복원 실패:\n" + "\n".join(cleanup_errors)
    _ai_state["done"] = True
    _ai_state["phase"] = "finished"
    try:
        _ai_save(error)
    finally:
        if _ai_handle is not None:
            unreal.unregister_slate_post_tick_callback(_ai_handle)
            _ai_handle = None
        _ai_level.editor_request_end_play()


def _ai_phase(name, now):
    _ai_state["phase"] = name
    _ai_state["since"] = now
    _ai_save()


def _ai_place(distance):
    # 원래 스파링 위치에서 +Y 방향을 사용한다. 재배치는 현재 적 위치 기준이다.
    enemy_location = _ai_state["enemy"].get_actor_location()
    location = unreal.Vector(enemy_location.x, enemy_location.y + distance, _ai_state["target_z"])
    _ai_state["movement"].stop_movement_immediately()
    _ai_state["movement"].disable_movement()
    _ai_state["player"].set_actor_location_and_rotation(location, unreal.Rotator(yaw=-90), False, True)
    _ai_state["placed_at"] = [location.x, location.y, location.z]


def _ai_snapshot(world, now):
    player = _ai_state["player"]
    enemy = _ai_state["enemy"]
    controller = _ai_state["controller"]
    player_at, enemy_at = _ai_position(player), _ai_position(enemy)
    anim = enemy.mesh.get_anim_instance()
    montage = anim.get_current_active_montage() if anim else None
    hp = _ai_attributes(player)["Health"]
    return {"phase": _ai_state["phase"], "elapsed_real": now - _ai_state["created"],
            "world_seconds": unreal.GameplayStatics.get_time_seconds(world),
            "player": player_at, "enemy": enemy_at,
            "distance": math.dist(player_at, enemy_at),
            "player_hp": hp, "previous_player_hp": _ai_state["last_player_hp"],
            "hp_change": hp - _ai_state["last_player_hp"], "player_tags": _ai_tags(player),
            "damage_numbers": _ai_damage_numbers(),
            "enemy_tags": _ai_tags(enemy), "bChasing": bool(controller.get_editor_property("bChasing")),
            "enemy_active": bool(enemy.get_editor_property("bActive")),
            "timer_active": bool(unreal.SystemLibrary.is_timer_active(controller, "Think")),
            "tick_enabled": bool(controller.is_actor_tick_enabled()),
            "montage": montage.get_path_name() if montage else None,
            "montage_position": anim.montage_get_position(montage) if montage else None}


def _ai_setup(world, now):
    _ai_check("실제 전투 필드 PIE", "L_CombatField" in world.get_name(), world.get_name())
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
    enemy = next(actor for actor in actors if actor.get_actor_label() == "SparringGrunt_1")
    player = unreal.GameplayStatics.get_player_pawn(world, 0)
    controller = enemy.get_controller()
    _ai_check("스파링에 실제 AI 컨트롤러", _ai_valid(controller)
              and controller.get_class().get_name() == "BP_EnemyAIController_C")
    _ai_check("원래 스파링 활성 상태", enemy.get_editor_property("bActive"))
    movement = player.get_component_by_class(unreal.CharacterMovementComponent)
    _ai_state.update({"player": player, "enemy": enemy, "controller": controller,
                      "movement": movement, "original_mode": movement.get_editor_property("movement_mode"),
                      "original_custom_mode": movement.get_editor_property("custom_movement_mode"),
                      "target_z": player.get_actor_location().z, "enemy_origin": _ai_position(enemy)})
    for pawn in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Pawn):
        other_controller = pawn.get_controller()
        if pawn != enemy and _ai_valid(other_controller) and other_controller.get_class().get_name() == "BP_EnemyAIController_C":
            _ai_state["dormant_others"].append((pawn, bool(pawn.get_editor_property("bActive"))))
            pawn.call_method("SetDormant", args=(True,))
    cdo = unreal.get_default_object(enemy.get_class())
    aggro = float(enemy.get_editor_property("AggroRange"))
    ranges = [float(value) for value in enemy.get_editor_property("AttackRanges")]
    minima = [float(value) for value in enemy.get_editor_property("AttackMinRanges")]
    attack_tags = [unreal.GameplayTagLibrary.get_debug_string_from_gameplay_tag(tag)
                   for tag in enemy.get_editor_property("AttackTags")]
    combat_class = unreal.load_class(None, "/Game/SoulCombat/Components/AC_CombatComponent.AC_CombatComponent_C")
    player_combat = player.get_component_by_class(combat_class)
    feedback_class = unreal.load_class(None, "/Game/SoulCombat/Components/AC_CombatFeedback.AC_CombatFeedback_C")
    number_widget_class = unreal.load_class(None, "/Game/SoulCombat/UI/WBP_DamageNumber.WBP_DamageNumber_C")
    player_controller = unreal.GameplayStatics.get_player_controller(world, 0)
    feedback = player_controller.get_component_by_class(feedback_class) if feedback_class is not None else None
    if feedback is None or number_widget_class is None:
        raise RuntimeError("실제 플레이어 컨트롤러의 전투 피드백 또는 피해 숫자 위젯을 찾지 못했다.")
    melee_class = unreal.load_class(None, "/Game/SoulCombat/GAS/Abilities/GA_Enemy_Melee.GA_Enemy_Melee_C")
    coefficient = float(unreal.get_default_object(melee_class).get_editor_property("Coefficient"))
    expected = _ai_attributes(enemy)["AttackPower"] * coefficient * 100 / (100 + _ai_attributes(player)["Defense"])
    interval = float(controller.get_editor_property("ThinkInterval"))
    respawn_delay = float(player_combat.get_editor_property("RespawnDelay"))
    approach = min(700.0, aggro - 100.0)
    _ai_state["config"] = {"map": world.get_name(), "enemy_label": enemy.get_actor_label(),
                           "enemy_origin": _ai_state["enemy_origin"], "cdo_aggro_range": float(cdo.get_editor_property("AggroRange")),
                           "instance_aggro_range": aggro, "cdo_attack_ranges": [float(v) for v in cdo.get_editor_property("AttackRanges")],
                           "instance_attack_ranges": ranges, "attack_min_ranges": minima, "attack_tags": attack_tags,
                           "think_interval": interval, "approach_distance": approach, "outside_distance": aggro + 200.0,
                           "expected_damage": expected, "respawn_delay": respawn_delay,
                           "damage_observation": "직전 프레임보다 HP 감소 + PC 피드백의 유효 WBP_DamageNumber 피해량 일치",
                           "dormant_others": [a.get_actor_label() for a, unused in _ai_state["dormant_others"]]}
    _ai_check("실제 스파링 범위와 공격 배열", len(ranges) == len(minima) == len(attack_tags) == 1
              and 0 <= minima[0] < ranges[0] and aggro > ranges[0] + 100
              and ranges[0] + 100 < approach < aggro and expected > 0, _ai_state["config"])
    _ai_check("Think 간격과 부활 전 관찰 구간", 0 < interval <= 0.5 and respawn_delay > 1.0,
              {"think_interval": interval, "respawn_delay": respawn_delay})
    _ai_state.update({"aggro": aggro, "approach": approach, "expected_damage": expected,
                      "player_combat": player_combat, "last_player_hp": _ai_attributes(player)["Health"],
                      "feedback": feedback, "number_widget_class": number_widget_class,
                      "death_observation": min(2.4, respawn_delay - 0.2)})
    _ai_place(aggro + 200.0)
    _ai_phase("outside_settle", now)


def _ai_tick(delta):
    try:
        now = time.monotonic()
        if now - _ai_state["created"] > 40:
            raise TimeoutError("자율 AI 전체 40초 제한: " + _ai_state["phase"])
        world = _ai_editor.get_game_world()
        if _ai_state["phase"] == "waiting":
            if world is None or unreal.GameplayStatics.get_time_seconds(world) < 0.4:
                if now - _ai_state["created"] > 12:
                    raise TimeoutError("자율 AI PIE 준비 12초 초과")
                return
            _ai_setup(world, now)
            return
        if world is None:
            raise RuntimeError("검사 도중 PIE 월드가 종료됐다.")
        # 적의 Tick·타이머는 건드리지 않고 플레이어 이동만 테스트 월드에서 고정한다.
        _ai_state["movement"].stop_movement_immediately()
        _ai_state["movement"].disable_movement()
        sample = _ai_snapshot(world, now)
        _ai_state["last_player_hp"] = sample["player_hp"]
        _ai_state["last_observation"] = sample
        if now - _ai_state["last_sample"] >= 0.1:
            _ai_state["samples"].append(sample)
            _ai_state["last_sample"] = now
        if not sample["timer_active"] or not sample["tick_enabled"] or not sample["enemy_active"]:
            raise AssertionError("기존 AI 타이머·Tick·활성이 유지되지 않음: " + str(sample))
        if abs(sample["enemy"][2] - _ai_state["enemy_origin"][2]) > 150:
            raise RuntimeError("스파링 접근 경로의 지면 이탈 또는 낙하: " + str(sample))
        phase = _ai_state["phase"]
        elapsed = now - _ai_state["since"]
        attacking = "State.Attacking" in sample["enemy_tags"]
        if phase == "outside_settle" and elapsed >= 0.8:
            _ai_check("초기 범위 밖에서 추격 해제", sample["distance"] > _ai_state["aggro"]
                      and not sample["bChasing"] and not attacking, sample)
            _ai_phase("outside_observe", now)
        elif phase == "outside_observe":
            if sample["bChasing"] or attacking or sample["hp_change"] < 0:
                raise AssertionError("초기 범위 밖에서 추격·공격·피해 발생: " + str(sample))
            if elapsed >= 1.5:
                _ai_check("범위 밖 대기에서 새 피해 없음", True, sample)
                _ai_place(_ai_state["approach"])
                _ai_state.update({"attack_seen": False,
                                  "chase_seen": False, "distance_decreased": False})
                _ai_phase("approach", now)
        elif phase in ("approach", "reapproach"):
            _ai_state["attack_seen"] |= attacking
            _ai_state["chase_seen"] |= sample["bChasing"]
            _ai_state["distance_decreased"] |= sample["distance"] < _ai_state["approach"] - 100
            # 자연 회복을 유지하며 프레임 간 HP 감소와 실제 GE 훅의 피해 숫자를 대조한다.
            damage = -sample["hp_change"]
            if damage > 0:
                prefix = "재진입" if phase == "reapproach" else "범위 진입"
                _ai_check(prefix + "에서 자연 추격·접근·공격", _ai_state["chase_seen"]
                          and _ai_state["distance_decreased"] and _ai_state["attack_seen"], sample)
                matched = [row for row in sample["damage_numbers"] if row["valid_widget"]
                           and row["damage"] == _ai_state["expected_damage"] and not row["guarded"]]
                _ai_check(prefix + "에서 실제 GE 피해", bool(matched),
                          {"expected": _ai_state["expected_damage"], "net_hp_decrease": damage,
                           "matched_numbers": matched, "sample": sample})
                if phase == "approach":
                    _ai_place(_ai_state["aggro"] + 200.0)
                    _ai_phase("exit_settle", now)
                else:
                    asc = _ai_state["player"].get_component_by_class(unreal.AbilitySystemComponent)
                    damage_class = unreal.load_class(None, "/Game/SoulCombat/GAS/Effects/GE_Damage.GE_Damage_C")
                    tag = unreal.GameplayTag()
                    tag.import_text('(TagName="Data.Damage")')
                    spec = asc.make_outgoing_spec(damage_class, 1.0, asc.make_effect_context())
                    spec = unreal.AbilitySystemLibrary.assign_tag_set_by_caller_magnitude(spec, tag, 1000000.0)
                    asc.apply_gameplay_effect_spec_to_self(spec)
                    _ai_check("실제 GE로 플레이어 사망", _ai_attributes(_ai_state["player"])["Health"] == 0
                              and _ai_state["player_combat"].get_editor_property("bIsDead"))
                    _ai_state["death_world"] = unreal.GameplayStatics.get_time_seconds(world)
                    _ai_phase("dead_settle", now)
            elif elapsed > 9:
                raise TimeoutError(phase + " 자연 접근·공격 9초 초과: " + str(sample))
        elif phase == "exit_settle":
            # 이미 시작한 몽타주는 취소를 요구하지 않고 실제 종료까지 기다린다.
            if elapsed >= 0.8 and not attacking and sample["montage"] is None:
                _ai_check("이탈 후 기존 공격 종료·추격 해제", sample["distance"] > _ai_state["aggro"]
                          and not sample["bChasing"], sample)
                _ai_phase("exit_observe", now)
            elif elapsed > 6:
                raise TimeoutError("이탈 뒤 기존 몽타주 종료 6초 초과: " + str(sample))
        elif phase == "exit_observe":
            if attacking or sample["bChasing"] or sample["hp_change"] < 0:
                raise AssertionError("범위 이탈 안정화 후 새 공격·추격·피해 발생: " + str(sample))
            if elapsed >= 1.5:
                _ai_check("범위 이탈 뒤 새 공격·피해 없음", True, sample)
                _ai_place(_ai_state["approach"])
                _ai_state.update({"attack_seen": False,
                                  "chase_seen": False, "distance_decreased": False})
                _ai_phase("reapproach", now)
        elif phase == "dead_settle" and elapsed >= 0.4:
            _ai_check("사망 대상에서 자연 추격 해제", not sample["bChasing"]
                      and "State.Dead" in sample["player_tags"], sample)
            _ai_state["dead_attack_previous"] = attacking
            _ai_phase("dead_observe", now)
        elif phase == "dead_observe":
            since_death = sample["world_seconds"] - _ai_state["death_world"]
            if sample["bChasing"] or (attacking and not _ai_state["dead_attack_previous"]):
                raise AssertionError("사망 대상에 새 추격·공격 발동: " + str(sample))
            if sample["player_hp"] != 0 or "State.Dead" not in sample["player_tags"]:
                raise AssertionError("설정된 부활 전 관찰 구간에 사망 상태가 해제됨: " + str(sample))
            _ai_state["dead_attack_previous"] = attacking
            if since_death >= _ai_state["death_observation"]:
                _ai_check("부활 전 사망 대상에 새 추격·공격 없음", True, sample)
                _ai_check("최종 자연 Think 타이머·Tick 유지", sample["timer_active"] and sample["tick_enabled"])
                _ai_finish()
    except Exception:
        # 실패 직전 상태가 정기 샘플 사이에 생긴 경우도 결과에 남긴다.
        if _ai_state.get("last_observation") is not None:
            _ai_state["samples"].append(_ai_state["last_observation"])
        _ai_finish(traceback.format_exc())


_ai_handle = unreal.register_slate_post_tick_callback(_ai_tick)
_ai_save()
_ai_level.editor_request_begin_play()
result = {"started": True, "output": _ai_output, "maximum_real_seconds": 40}
