#include "SCAttributeSet.h"
#include "GameplayEffect.h"
#include "GameplayEffectExtension.h"
#include "GameplayTagContainer.h"

namespace
{
	/** 태그를 이름으로 찾는다. 태그가 없으면 assert 없이 false. */
	bool OwnerHasTag(const UAbilitySystemComponent& ASC, const TCHAR* TagName)
	{
		const FGameplayTag Tag = FGameplayTag::RequestGameplayTag(FName(TagName), false);
		return Tag.IsValid() && ASC.HasMatchingGameplayTag(Tag);
	}
}

USCAttributeSet::USCAttributeSet()
{
	// 실제 값은 DataTable(Init Stats)로 덮어쓴다. 여기 값은 테이블이 없을 때의 안전값이다.
	InitHealth(100.f);
	InitMaxHealth(100.f);
	InitMana(100.f);
	InitMaxMana(100.f);
	InitStamina(100.f);
	InitMaxStamina(100.f);
	InitAttackPower(10.f);
	InitDefense(0.f);
	InitIncomingDamage(0.f);
}

void USCAttributeSet::PreAttributeChange(const FGameplayAttribute& Attribute, float& NewValue)
{
	Super::PreAttributeChange(Attribute, NewValue);

	if (Attribute == GetHealthAttribute())
	{
		NewValue = FMath::Clamp(NewValue, 0.f, GetMaxHealth());
	}
	else if (Attribute == GetManaAttribute())
	{
		NewValue = FMath::Clamp(NewValue, 0.f, GetMaxMana());
	}
	else if (Attribute == GetStaminaAttribute())
	{
		NewValue = FMath::Clamp(NewValue, 0.f, GetMaxStamina());
	}
	else if (Attribute == GetMaxHealthAttribute() || Attribute == GetMaxManaAttribute() || Attribute == GetMaxStaminaAttribute())
	{
		NewValue = FMath::Max(NewValue, 0.f);
	}
	else if (Attribute == GetDefenseAttribute())
	{
		// 100 + Defense가 0 이하가 되지 않게 한다.
		NewValue = FMath::Max(NewValue, -50.f);
	}
}

void USCAttributeSet::PostAttributeChange(const FGameplayAttribute& Attribute, float OldValue, float NewValue)
{
	Super::PostAttributeChange(Attribute, OldValue, NewValue);

	if (Attribute == GetMaxHealthAttribute())
	{
		ClampCurrentToMax(GetHealthAttribute(), NewValue);
	}
	else if (Attribute == GetMaxManaAttribute())
	{
		ClampCurrentToMax(GetManaAttribute(), NewValue);
	}
	else if (Attribute == GetMaxStaminaAttribute())
	{
		ClampCurrentToMax(GetStaminaAttribute(), NewValue);
	}
}

void USCAttributeSet::ClampCurrentToMax(const FGameplayAttribute& CurrentAttribute, float NewMax)
{
	UAbilitySystemComponent* ASC = GetOwningAbilitySystemComponent();
	if (!ASC)
	{
		return;
	}

	const float Current = ASC->GetNumericAttribute(CurrentAttribute);
	if (Current > NewMax)
	{
		ASC->ApplyModToAttribute(CurrentAttribute, EGameplayModOp::Override, NewMax);
	}
}

void USCAttributeSet::PostGameplayEffectExecute(const FGameplayEffectModCallbackData& Data)
{
	Super::PostGameplayEffectExecute(Data);

	if (Data.EvaluatedData.Attribute == GetIncomingDamageAttribute())
	{
		const float RawDamage = GetIncomingDamage();
		SetIncomingDamage(0.f);

		if (RawDamage <= 0.f)
		{
			return;
		}

		if (OwnerHasTag(Data.Target, TEXT("State.Invulnerable")) || OwnerHasTag(Data.Target, TEXT("State.Dead")))
		{
			return;
		}

		const float Mitigated = RawDamage * 100.f / (100.f + GetDefense());
		SetHealth(FMath::Clamp(GetHealth() - Mitigated, 0.f, GetMaxHealth()));
	}
	else if (Data.EvaluatedData.Attribute == GetHealthAttribute())
	{
		SetHealth(FMath::Clamp(GetHealth(), 0.f, GetMaxHealth()));
	}
	else if (Data.EvaluatedData.Attribute == GetManaAttribute())
	{
		SetMana(FMath::Clamp(GetMana(), 0.f, GetMaxMana()));
	}
	else if (Data.EvaluatedData.Attribute == GetStaminaAttribute())
	{
		SetStamina(FMath::Clamp(GetStamina(), 0.f, GetMaxStamina()));
	}
}
