#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameplayTagContainer.h"
#include "SCAbilitySet.generated.h"

class UGameplayAbility;
class UGameplayEffect;
class UDataTable;

/** 어빌리티 세트의 한 줄: 어떤 어빌리티를 어떤 요청 태그로 발동하는지. */
USTRUCT(BlueprintType)
struct FSCAbilityGrant
{
	GENERATED_BODY()

	/** 부여할 어빌리티 클래스. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Ability")
	TSubclassOf<UGameplayAbility> Ability;

	/**
	 * 발동 요청 태그. 플레이어는 입력(InputTag.*), 몬스터 AI는 행동(InputTag.AI.*) 태그를 쓴다.
	 * 블루프린트 전투 컴포넌트가 이 태그로 어빌리티 핸들을 찾아 발동한다.
	 */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Ability", meta=(Categories="InputTag"))
	FGameplayTag InputTag;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Ability")
	int32 Level = 1;
};

/**
 * 캐릭터 하나가 시작할 때 받는 GAS 구성(어빌리티, 상시 이펙트, 초기 스탯 테이블).
 *
 * 데이터만 담는다. 부여 로직은 블루프린트(AC_CombatComponent)에 있다.
 * C++에 둔 이유: 블루프린트 변수로는 GA/GE "클래스" 배열을 MCP로 만들 수 없고,
 * GAS 프로젝트에서 흔히 쓰는 AbilitySet 패턴(Lyra)과 같은 데이터 구조를 쓰기 위해서다.
 */
UCLASS(BlueprintType, Const)
class SOULCOMBAT_API USCAbilitySet : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Abilities", meta=(TitleProperty="Ability"))
	TArray<FSCAbilityGrant> Abilities;

	/** 시작할 때 자기 자신에게 적용하는 이펙트 (자원 회복 등). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Effects")
	TArray<TSubclassOf<UGameplayEffect>> StartupEffects;

	/** 행 구조체 AttributeMetaData, 행 이름 "SCAttributeSet.<속성>" 형식의 초기 스탯 테이블. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Attributes")
	TObjectPtr<UDataTable> AttributeTable;
};
