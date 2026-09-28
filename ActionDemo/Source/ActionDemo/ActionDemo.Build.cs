// The only C++ module of the ActionDemo MCP test project.
// It holds a single class, UDemoAttributeSet, because attribute sets cannot be made in Blueprint.

using UnrealBuildTool;

public class ActionDemo : ModuleRules
{
	public ActionDemo(ReadOnlyTargetRules Target) : base(Target)
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
