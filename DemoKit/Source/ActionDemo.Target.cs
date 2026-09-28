// Game target for the ActionDemo MCP test project. Copied into ActionDemo/Source by DemoKit/install.ps1.

using UnrealBuildTool;
using System.Collections.Generic;

public class ActionDemoTarget : TargetRules
{
	public ActionDemoTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("ActionDemo");
	}
}
