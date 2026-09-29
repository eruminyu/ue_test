// SoulCombat의 유일한 C++ 모듈.
// GAS를 쓰는 데 C++가 꼭 필요한 부분(AttributeSet, 어빌리티 세트 데이터 에셋)만 둔다. 게임 로직은 전부 블루프린트다.

using UnrealBuildTool;

public class SoulCombat : ModuleRules
{
	public SoulCombat(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] {
			"Core",
			"CoreUObject",
			"Engine",
			"GameplayAbilities",
			"GameplayTags",
			"GameplayTasks"
		});
	}
}
