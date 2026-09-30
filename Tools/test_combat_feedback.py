"""실제 PIE 전용 명중 연출 계약·수명 회귀 검사.

게임 에셋을 편집하지 않는다. 새 PIE의 PC에 독립 테스트 컴포넌트를 붙이고
검사 초기 히트스톱을 명시적으로 끈다. 실제 GE_Damage의 Data.Damage를 적용해
얻은 HP 감소량을 이 컴포넌트에만 전달한다. 통합 ApplyHit를 호출하면 PC의
게임 컴포넌트에도 ReportHit가 전달되어 복원 소유권이 겹치므로 여기서는
호출하지 않는다. 실제 ApplyHit 전달은 별도 통합 회귀 검사에서 확인한다.

에디터 Python 브리지에서 이 파일을 실행한 뒤 start_feedback_tests()를
호출한다. 결과는 프로젝트 Saved에 둔다. 최초 담당 B 반환 당시의 기본값
false·57개 통과 기록은 당시 구현의 증거이며, 이 검사는 통합 이후 게임
기본값과 무관하게 독립 수명·복원 계약을 검사한다.
"""
import json
import os
import traceback
import unreal

FEEDBACK_CLASS = "/Game/SoulCombat/Components/AC_CombatFeedback.AC_CombatFeedback_C"


def runtime_set(obj, name, value):
    """PIE 값 변경은 에디터의 생성 스크립트 재실행을 요청하지 않는다."""
    obj.set_editor_property(name, value, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)


def require_feedback_contract():
    feedback_class = unreal.load_class(None, FEEDBACK_CLASS)
    assert feedback_class is not None, "AC_CombatFeedback 계약 클래스가 아직 없다"
    return feedback_class


class FeedbackRuntimeTests:
    def __init__(self):
        self.feedback_class = require_feedback_contract()
        self.world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        assert self.world is not None, "실제 PIE 월드에서 실행해야 한다"
        self.player = unreal.GameplayStatics.get_player_pawn(self.world, 0)
        self.pc = unreal.GameplayStatics.get_player_controller(self.world, 0)
        assert self.player and self.pc
        actors = unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.Actor)
        self.target = next(a for a in actors if a.get_actor_label() == "Dummy_2")
        self.destroy_target = next(a for a in actors if a.get_actor_label() == "Dummy_3")
        for a in actors:
            if a.get_actor_label().startswith("SparringGrunt"):
                a.call_method("SetDormant", args=(True,))
        self.camera = self.player.get_component_by_class(unreal.CameraComponent)
        self.mesh = self.target.get_component_by_class(unreal.SkeletalMeshComponent)
        self.original_overlay = self.mesh.get_overlay_material()
        self.feedback = self.pc.call_method("AddComponentByClass", args=(self.feedback_class, False, unreal.Transform(), False))
        assert self.feedback is not None
        # 통합 게임의 기본값을 바꾸지 않고, 새 PIE 검사 객체만 초기화한다.
        runtime_set(self.feedback, "bEnableHitstop", False)
        assert unreal.SystemLibrary.is_valid(self.feedback)
        self.rows = []
        self.steps = []
        self.index = 0
        self.deadline = self.now()
        self.output = os.path.join(unreal.Paths.project_saved_dir(), "combat-feedback-tests.json")
        self.initial_fov = self.camera.get_editor_property("field_of_view")
        self.initial_player_dilation = self.player.get_editor_property("custom_time_dilation")
        self.initial_target_dilation = self.target.get_editor_property("custom_time_dilation")
        self.prepare()
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def now(self):
        return unreal.GameplayStatics.get_real_time_seconds(self.world)

    def value(self, name):
        return self.feedback.get_editor_property(name)

    def check(self, name, condition, actual=None):
        self.rows.append({"case": name, "passed": bool(condition), "actual": actual})
        self.persist()

    def persist(self, done=False, error=None):
        with open(self.output, "w", encoding="utf-8") as stream:
            json.dump({"done": done, "cases": self.rows,
                       "failures": [r["case"] for r in self.rows if not r["passed"]],
                       "error": error}, stream, ensure_ascii=False, indent=2, default=str)

    def add(self, delay, action):
        self.steps.append((delay, action))

    def report(self, damage=50.0, guarded=False, target=None):
        self.feedback.call_method("ReportHit", args=(self.player, target or self.target, damage, guarded))

    def reset(self):
        self.feedback.call_method("ResetAllFeedback")
        runtime_set(self.player, "custom_time_dilation", 0.75)
        runtime_set(self.target, "custom_time_dilation", 1.2)
        self.camera.set_field_of_view(97.0)
        self.mesh.set_overlay_material(self.original_overlay)

    def restored(self, prefix):
        p = self.player.get_editor_property("custom_time_dilation")
        t = self.target.get_editor_property("custom_time_dilation")
        f = self.camera.get_editor_property("field_of_view")
        self.check(prefix + " 최초 배율 복원", abs(p - 0.75) < 0.0001 and abs(t - 1.2) < 0.0001, [p, t])
        self.check(prefix + " 최초 FOV 복원", abs(f - 97.0) < 0.001, f)
        self.check(prefix + " 최초 오버레이 복원", self.mesh.get_overlay_material() == self.original_overlay)

    def apply_damage_effect(self, magnitude):
        """실제 GE로 HP를 변경하되 게임 PC의 ReportHit 경로는 호출하지 않는다."""
        asc = self.target.get_component_by_class(unreal.AbilitySystemComponent)
        source_asc = self.player.get_component_by_class(unreal.AbilitySystemComponent)
        effect = unreal.load_class(None, "/Game/SoulCombat/GAS/Effects/GE_Damage.GE_Damage_C")
        assert asc is not None and source_asc is not None and effect is not None
        attr = next(a for a in asc.get_all_attributes()
                    if unreal.AbilitySystemLibrary.get_debug_string_from_gameplay_attribute(a).endswith(".Health"))
        before = unreal.AbilitySystemLibrary.get_float_attribute(self.target, attr)[0]
        damage_tag = unreal.GameplayTag()
        damage_tag.import_text('(TagName="Data.Damage")')
        spec = source_asc.make_outgoing_spec(effect, 1.0, source_asc.make_effect_context())
        spec = unreal.AbilitySystemLibrary.assign_tag_set_by_caller_magnitude(spec, damage_tag, magnitude)
        asc.apply_gameplay_effect_spec_to_self(spec)
        after = unreal.AbilitySystemLibrary.get_float_attribute(self.target, attr)[0]
        return max(0.0, before - after)

    def real_damage(self):
        return self.apply_damage_effect(50.0)

    def begin_normal(self):
        self.reset()
        damage = self.real_damage()
        self.report(damage)
        self.check("기존 GE의 실제 피해 전달", abs(damage - 50.0) < 0.05, damage)
        self.check("독립 검사 초기 히트스톱 꺼짐", not self.value("bEnableHitstop"))
        self.check("꺼짐 상태 배율 보존", abs(self.player.get_editor_property("custom_time_dilation") - 0.75) < 0.0001)
        self.check("실제 숫자 액터 생성", len(self.value("DamageActors")) == 1)
        number = self.value("DamageActors")[0]
        widget = number.get_component_by_class(unreal.WidgetComponent).get_user_widget_object()
        self.check("실제 피해 숫자 값", abs(widget.get_editor_property("DamageValue") - damage) < 0.05)
        self.check("일반 명중 위젯 가드 여부", not widget.get_editor_property("bGuardedValue"))
        self.check("카메라 펄스 시작", self.camera.get_editor_property("field_of_view") > 97.0)
        self.check("플래시 시작", self.mesh.get_overlay_material() != self.original_overlay)

    def begin_stop(self):
        self.reset()
        runtime_set(self.feedback, "bEnableHitstop", True)
        self.check("런타임 플래그 변경 뒤 컴포넌트 유효", unreal.SystemLibrary.is_valid(self.feedback))
        self.report()
        self.check("히트스톱 양쪽 적용", self.player.get_editor_property("custom_time_dilation") < 0.75 and
                   self.target.get_editor_property("custom_time_dilation") < 1.2,
                   [self.player.get_editor_property("custom_time_dilation"), self.target.get_editor_property("custom_time_dilation")])
        self.check("PC 정상 시간 배율", abs(self.pc.get_editor_property("custom_time_dilation") - 1.0) < 0.0001)

    def external_change(self):
        self.begin_stop()
        runtime_set(self.player, "custom_time_dilation", 0.4)
        self.camera.set_field_of_view(113.0)
        self.external_overlay = unreal.MaterialLibrary.create_dynamic_material_instance(
            self.world, unreal.load_asset("/Game/SoulCombat/Materials/M_SC_HitFlash"))
        self.mesh.set_overlay_material(self.external_overlay)

    def guarded_number(self):
        self.report(10.0, True)
        numbers = self.value("DamageActors")
        self.check("가드 숫자 생성", len(numbers) == 1)
        widget = numbers[0].get_component_by_class(unreal.WidgetComponent).get_user_widget_object()
        self.check("가드 위젯 실제 피해10", abs(widget.get_editor_property("DamageValue") - 10.0) < 0.01)
        self.check("가드 위젯 구분", widget.get_editor_property("bGuardedValue"))

    def burst_numbers(self):
        self.reset()
        for _ in range(30):
            self.report()
        self.check("연속 명중 숫자24개 상한", len(self.value("DamageActors")) == 24)
        self.check("카메라 중첩 합산 방지", self.camera.get_editor_property("field_of_view") <= 101.001)

    def external_check(self):
        self.check("외부 배율 변경 보존", abs(self.player.get_editor_property("custom_time_dilation") - 0.4) < 0.0001)
        self.check("외부 FOV 변경 보존", abs(self.camera.get_editor_property("field_of_view") - 113.0) < 0.001)
        self.check("외부 오버레이 변경 보존", self.mesh.get_overlay_material() == self.external_overlay)

    def kill_target(self):
        self.begin_stop()
        # 이미 시작한 독립 히트스톱 중 실제 GE로 사망시킨다. 추가 ReportHit는 없다.
        self.apply_damage_effect(1000000.0)

    def respawn_target(self):
        combat = self.target.get_component_by_class(unreal.load_class(None, "/Game/SoulCombat/Components/AC_CombatComponent.AC_CombatComponent_C"))
        combat.call_method("Respawn")

    def paused_stop(self):
        self.begin_stop()
        unreal.GameplayStatics.set_game_paused(self.world, True)

    def slow_world_stop(self):
        self.begin_stop()
        unreal.GameplayStatics.set_global_time_dilation(self.world, 0.1)

    def destroy_actor(self):
        self.reset()
        self.report(target=self.destroy_target)
        self.destroy_target.destroy_actor()

    def destroy_component(self):
        self.begin_stop()
        self.numbers_before_end = list(self.value("DamageActors"))
        self.feedback.destroy_component(self.feedback)
        self.restored("EndPlay")
        self.check("EndPlay 숫자 파괴", all(not unreal.SystemLibrary.is_valid(a) for a in self.numbers_before_end))

    def prepare(self):
        self.add(0.0, lambda: self.check("피해0 무효 연출", self.report(0.0) is None and len(self.value("DamageActors")) == 0))
        self.add(0.0, self.begin_normal)
        self.add(0.35, lambda: self.restored("일반 만료"))
        self.add(0.5, lambda: self.check("숫자 실시간 수명", len(self.value("DamageActors")) == 0))
        self.add(0.0, self.guarded_number)
        self.add(0.0, self.burst_numbers)
        self.add(0.8, self.begin_stop)
        self.add(0.02, lambda: self.report(100.0))
        self.add(0.25, lambda: self.restored("재피격"))
        self.add(0.0, self.external_change)
        self.add(0.3, self.external_check)
        self.add(0.0, self.kill_target)
        self.add(0.035, lambda: self.check("사망 대상 배율 즉시 복원", abs(self.target.get_editor_property("custom_time_dilation") - 1.2) < 0.0001))
        self.add(0.0, self.respawn_target)
        self.add(0.3, lambda: self.restored("부활"))
        self.add(0.0, self.paused_stop)
        self.add(0.3, lambda: self.restored("일시정지"))
        self.add(0.0, lambda: unreal.GameplayStatics.set_game_paused(self.world, False))
        self.add(0.0, self.slow_world_stop)
        self.add(0.3, lambda: self.restored("전역0.1배"))
        self.add(0.0, lambda: unreal.GameplayStatics.set_global_time_dilation(self.world, 1.0))
        self.add(0.0, self.destroy_actor)
        self.add(0.3, lambda: self.check("파괴 대상 참조 정리", len(self.value("StoppedActors")) == 0 and len(self.value("FlashMeshes")) == 0))
        self.add(0.6, self.destroy_component)

    def tick(self, delta):
        try:
            if self.now() < self.deadline:
                return
            if self.index >= len(self.steps):
                self.finish()
                return
            delay, action = self.steps[self.index]
            action()
            self.index += 1
            next_delay = self.steps[self.index][0] if self.index < len(self.steps) else 0.0
            self.deadline = self.now() + next_delay
        except Exception:
            self.finish(traceback.format_exc())

    def finish(self, error=None):
        unreal.unregister_slate_post_tick_callback(self.handle)
        unreal.GameplayStatics.set_game_paused(self.world, False)
        unreal.GameplayStatics.set_global_time_dilation(self.world, 1.0)
        if unreal.SystemLibrary.is_valid(self.feedback):
            self.feedback.call_method("ResetAllFeedback")
            self.feedback.destroy_component(self.feedback)
        runtime_set(self.player, "custom_time_dilation", self.initial_player_dilation)
        if unreal.SystemLibrary.is_valid(self.target):
            runtime_set(self.target, "custom_time_dilation", self.initial_target_dilation)
            self.mesh.set_overlay_material(self.original_overlay)
        self.camera.set_field_of_view(self.initial_fov)
        self.persist(True, error)


def start_feedback_tests():
    return FeedbackRuntimeTests()
