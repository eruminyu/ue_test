// The only C++ class in the ActionDemo MCP test project.
// Gameplay Ability System attribute sets must be native code in UE 5.8. Everything else
// (character setup, abilities, effects, cues, UI) is built as Blueprint through Unreal MCP.

#pragma once

#include "CoreMinimal.h"
#include "AttributeSet.h"
#include "AbilitySystemComponent.h"
#include "DemoAttributeSet.generated.h"

/**
 * Health, mana and attack power for the player and the training dummies.
 *
 * Blueprint usage:
 * - Create it on an Ability System Component with the "Init Stats" node (Attributes = DemoAttributeSet),
 *   optionally with a DataTable of row type AttributeMetaData and row names like "DemoAttributeSet.Health".
 * - Deal damage with an instant Gameplay Effect that adds to IncomingDamage
 *   (magnitude: SetByCaller, tag Data.Damage). This set turns it into a Health loss.
 * - Read values with "Get Float Attribute" and react with "Wait for Attribute Changed".
 *
 * Tags looked up by name, created in the editor through MCP:
 * - State.Invulnerable: damage is ignored (dodge i-frames).
 * - State.Dead: damage is ignored.
 *
 * The demo is single player, so the attributes are not replicated.
 */
UCLASS()
class ACTIONDEMO_API UDemoAttributeSet : public UAttributeSet
{
	GENERATED_BODY()

public:

	UDemoAttributeSet();

	UPROPERTY(BlueprintReadOnly, Category="Attributes")
	FGameplayAttributeData Health;
	ATTRIBUTE_ACCESSORS_BASIC(UDemoAttributeSet, Health)

	UPROPERTY(BlueprintReadOnly, Category="Attributes")
	FGameplayAttributeData MaxHealth;
	ATTRIBUTE_ACCESSORS_BASIC(UDemoAttributeSet, MaxHealth)

	UPROPERTY(BlueprintReadOnly, Category="Attributes")
	FGameplayAttributeData Mana;
	ATTRIBUTE_ACCESSORS_BASIC(UDemoAttributeSet, Mana)

	UPROPERTY(BlueprintReadOnly, Category="Attributes")
	FGameplayAttributeData MaxMana;
	ATTRIBUTE_ACCESSORS_BASIC(UDemoAttributeSet, MaxMana)

	UPROPERTY(BlueprintReadOnly, Category="Attributes")
	FGameplayAttributeData AttackPower;
	ATTRIBUTE_ACCESSORS_BASIC(UDemoAttributeSet, AttackPower)

	/** Meta attribute. Damage effects add to it; it is converted into Health loss and reset to 0. */
	UPROPERTY(BlueprintReadOnly, Category="Meta")
	FGameplayAttributeData IncomingDamage;
	ATTRIBUTE_ACCESSORS_BASIC(UDemoAttributeSet, IncomingDamage)

	virtual void PreAttributeChange(const FGameplayAttribute& Attribute, float& NewValue) override;
	virtual void PostGameplayEffectExecute(const FGameplayEffectModCallbackData& Data) override;
};
