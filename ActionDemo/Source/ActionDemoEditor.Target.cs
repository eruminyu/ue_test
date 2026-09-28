// Editor target for the ActionDemo MCP test project. Copied into ActionDemo/Source by DemoKit/install.ps1.

using UnrealBuildTool;
using System.Collections.Generic;

public class ActionDemoEditorTarget : TargetRules
{
	public ActionDemoEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("ActionDemo");
	}
}
