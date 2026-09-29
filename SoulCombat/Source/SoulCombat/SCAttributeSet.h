#pragma once

#include "CoreMinimal.h"
#include "AttributeSet.h"
#include "AbilitySystemComponent.h"
#include "SCAttributeSet.generated.h"

/**
 * 플레이어, 몬스터, 보스, 파괴 오브젝트가 함께 쓰는 속성 세트.
 *
 * GAS의 AttributeSet은 블루프린트로 만들 수 없어서 C++에 둔다. 여기에는 수치 보관과 보정만 있고
 * 게임 로직(가드 판정, 경직, 사망 처리 등)은 블루프린트에 있다.
 *
 * 블루프린트에서 쓰는 방법
 * - 초기화: ASC의 "Init Stats" 노드 (Attributes = SCAttributeSet, Data Table = 행 구조체 AttributeMetaData,
 *   행 이름 "SCAttributeSet.Health" 형식).
 * - 데미지: Instant GE가 IncomingDamage에 SetByCaller(Data.Damage) 값을 더한다.
 *   이 세트가 방어력을 반영해 Health를 깎고 IncomingDamage를 0으로 되돌린다.
 * - 읽기: "Get Float Attribute", 변화 감지: "Wait for Attribute Changed".
 *
 * 이름으로 찾는 태그 (Config/DefaultGameplayTags.ini에 정의)
 * - State.Invulnerable: 데미지 무시 (대시 무적 등)
 * - State.Dead: 데미지 무시
 *
 * 싱글 플레이 프로토타입이라 복제(Replication)는 하지 않는다.
 */
UCLASS()
class SOULCOMBAT_API USCAttributeSet : public UAttributeSet
{
	GENERATED_BODY()

public:

	USCAttributeSet();

	UPROPERTY(BlueprintReadOnly, Category="Vital")
	FGameplayAttributeData Health;
	ATTRIBUTE_ACCESSORS_BASIC(USCAttributeSet, Health)

	UPROPERTY(BlueprintReadOnly, Category="Vital")
	FGameplayAttributeData MaxHealth;
	ATTRIBUTE_ACCESSORS_BASIC(USCAttributeSet, MaxHealth)

	/** 스킬 자원 (HUD에는 SP로 표시). */
	UPROPERTY(BlueprintReadOnly, Category="Vital")
	FGameplayAttributeData Mana;
	ATTRIBUTE_ACCESSORS_BASIC(USCAttributeSet, Mana)

	UPROPERTY(BlueprintReadOnly, Category="Vital")
	FGameplayAttributeData MaxMana;
	ATTRIBUTE_ACCESSORS_BASIC(USCAttributeSet, MaxMana)

	/** 대시 자원. */
	UPROPERTY(BlueprintReadOnly, Category="Vital")
	FGameplayAttributeData Stamina;
	ATTRIBUTE_ACCESSORS_BASIC(USCAttributeSet, Stamina)

	UPROPERTY(BlueprintReadOnly, Category="Vital")
	FGameplayAttributeData MaxStamina;
	ATTRIBUTE_ACCESSORS_BASIC(USCAttributeSet, MaxStamina)

	UPROPERTY(BlueprintReadOnly, Category="Combat")
	FGameplayAttributeData AttackPower;
	ATTRIBUTE_ACCESSORS_BASIC(USCAttributeSet, AttackPower)

	/** 받는 데미지 = 원래 데미지 × 100 / (100 + Defense). */
	UPROPERTY(BlueprintReadOnly, Category="Combat")
	FGameplayAttributeData Defense;
	ATTRIBUTE_ACCESSORS_BASIC(USCAttributeSet, Defense)

	/** 메타 속성. 데미지 GE가 여기에 더하면 Health 감소로 바뀌고 0으로 초기화된다. */
	UPROPERTY(BlueprintReadOnly, Category="Meta")
	FGameplayAttributeData IncomingDamage;
	ATTRIBUTE_ACCESSORS_BASIC(USCAttributeSet, IncomingDamage)

	virtual void PreAttributeChange(const FGameplayAttribute& Attribute, float& NewValue) override;
	virtual void PostAttributeChange(const FGameplayAttribute& Attribute, float OldValue, float NewValue) override;
	virtual void PostGameplayEffectExecute(const FGameplayEffectModCallbackData& Data) override;

private:

	/** Max 값이 줄었을 때 현재 값을 새 Max 이하로 맞춘다. */
	void ClampCurrentToMax(const FGameplayAttribute& CurrentAttribute, float NewMax);
};
