<#
.SYNOPSIS
  Turns a fresh "Third Person" Blueprint project named ActionDemo into the MCP demo project.

.DESCRIPTION
  1. Copies the one C++ module (UDemoAttributeSet only) into ActionDemo\Source.
  2. Adds that module and the GameplayAbilities, Unreal MCP and All Toolsets plugins to ActionDemo.uproject.
  3. Turns on "Auto Start Server" for Unreal MCP in Config\DefaultEditorPerProjectUserSettings.ini.
  4. Writes ActionDemo\OpenEditor_EN.bat, which opens the editor in English (MCP Blueprint tools
     misbehave in non-English editors).
  5. With -Build, compiles the editor target so compile errors show up in this window.

  Run it with the editor closed. It is safe to run more than once.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File DemoKit\install.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File DemoKit\install.ps1 -Build
#>
param(
	[string]$ProjectDir = (Join-Path (Split-Path -Parent $PSScriptRoot) 'ActionDemo'),
	[string]$EngineDir = 'C:\Program Files\Epic Games\UE_5.8',
	[switch]$Build
)

$ErrorActionPreference = 'Stop'
$ProjectName = 'ActionDemo'

# Windows PowerShell 5.1 can serialize arrays as {"value":[...],"Count":n}; this type data causes it.
Remove-TypeData -TypeName System.Array -ErrorAction SilentlyContinue
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-Step([string]$Message) { Write-Host "==> $Message" -ForegroundColor Cyan }

# --- 0. Checks ---------------------------------------------------------------------------------
$ProjectDir = [System.IO.Path]::GetFullPath($ProjectDir)
$UProject = Join-Path $ProjectDir "$ProjectName.uproject"
if (-not (Test-Path -LiteralPath $UProject)) {
	throw "Could not find $UProject. Create the project first: Games > Third Person > Blueprint, name 'ActionDemo', location = the repository root."
}

if (Get-Process -Name 'UnrealEditor' -ErrorAction SilentlyContinue) {
	Write-Warning 'Unreal Editor is running. Close it before continuing, or the .uproject change may be overwritten.'
}

if (-not (Test-Path -LiteralPath $EngineDir)) {
	$Reg = Get-ItemProperty -Path 'HKLM:\SOFTWARE\EpicGames\Unreal Engine\5.8' -ErrorAction SilentlyContinue
	if ($Reg -and $Reg.InstalledDirectory) { $EngineDir = $Reg.InstalledDirectory }
}

# --- 1. C++ module ------------------------------------------------------------------------------
Write-Step 'Copying the ActionDemo C++ module (DemoAttributeSet only)'
$SourceFrom = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'Source')).Path
$SourceTo = Join-Path $ProjectDir 'Source'
Get-ChildItem -LiteralPath $SourceFrom -Recurse -File | ForEach-Object {
	$Relative = $_.FullName.Substring($SourceFrom.Length).TrimStart('\', '/')
	$Destination = Join-Path $SourceTo $Relative
	New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
	Copy-Item -LiteralPath $_.FullName -Destination $Destination -Force
	Write-Host "    Source\$Relative"
}

# --- 2. .uproject -------------------------------------------------------------------------------
Write-Step 'Updating ActionDemo.uproject (module + plugins)'
$Backup = "$UProject.bak"
if (-not (Test-Path -LiteralPath $Backup)) { Copy-Item -LiteralPath $UProject -Destination $Backup }

$Project = Get-Content -Raw -LiteralPath $UProject | ConvertFrom-Json

function Set-JsonProperty($Object, [string]$Name, $Value) {
	if ($Object.PSObject.Properties.Name -contains $Name) { $Object.$Name = $Value }
	else { $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value }
}

$Modules = @()
if ($Project.PSObject.Properties.Name -contains 'Modules') { $Modules = @($Project.Modules | Where-Object { $_ }) }
if (-not ($Modules | Where-Object { $_.Name -eq $ProjectName })) {
	$Modules += [pscustomobject]@{
		Name = $ProjectName
		Type = 'Runtime'
		LoadingPhase = 'Default'
		AdditionalDependencies = @('Engine')
	}
}
Set-JsonProperty $Project 'Modules' $Modules

$Plugins = @()
if ($Project.PSObject.Properties.Name -contains 'Plugins') { $Plugins = @($Project.Plugins | Where-Object { $_ }) }
$Wanted = @(
	@{ Name = 'GameplayAbilities'; EditorOnly = $false },
	@{ Name = 'ModelContextProtocol'; EditorOnly = $true },
	@{ Name = 'AllToolsets'; EditorOnly = $true }
)
foreach ($Want in $Wanted) {
	$Existing = $Plugins | Where-Object { $_.Name -eq $Want.Name } | Select-Object -First 1
	if ($Existing) {
		Set-JsonProperty $Existing 'Enabled' $true
	}
	else {
		$Entry = [pscustomobject]@{ Name = $Want.Name; Enabled = $true }
		if ($Want.EditorOnly) { $Entry | Add-Member -NotePropertyName 'TargetAllowList' -NotePropertyValue @('Editor') }
		$Plugins += $Entry
	}
	Write-Host "    plugin $($Want.Name)"
}
Set-JsonProperty $Project 'Plugins' $Plugins

$Json = $Project | ConvertTo-Json -Depth 20
[System.IO.File]::WriteAllText($UProject, $Json, $Utf8NoBom)

# Sanity check: the module must be listed and no array may have been turned into {"value", "Count"}.
$Check = Get-Content -Raw -LiteralPath $UProject | ConvertFrom-Json
if ($Json -match '"Count"\s*:' -or -not (@($Check.Modules) | Where-Object { $_.Name -eq $ProjectName })) {
	Copy-Item -LiteralPath $Backup -Destination $UProject -Force
	throw 'Writing ActionDemo.uproject went wrong, so the original was restored. Please report this output.'
}

# --- 3. Unreal MCP auto start -------------------------------------------------------------------
Write-Step 'Enabling Unreal MCP auto start (Config\DefaultEditorPerProjectUserSettings.ini)'
$ConfigDir = Join-Path $ProjectDir 'Config'
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
$UserSettings = Join-Path $ConfigDir 'DefaultEditorPerProjectUserSettings.ini'
$Section = '[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]'
$Existing = ''
if (Test-Path -LiteralPath $UserSettings) { $Existing = Get-Content -Raw -LiteralPath $UserSettings }
if ($Existing -notmatch [regex]::Escape($Section)) {
	$Block = @(
		'',
		$Section,
		'bAutoStartServer=True',
		'ServerPortNumber=8000',
		'ServerUrlPath=/mcp',
		'bEnableToolSearch=True',
		''
	) -join "`r`n"
	[System.IO.File]::WriteAllText($UserSettings, ($Existing + $Block), $Utf8NoBom)
	Write-Host '    added'
}
else {
	Write-Host '    already present'
}

# --- 4. English editor shortcut -----------------------------------------------------------------
Write-Step 'Writing ActionDemo\OpenEditor_EN.bat'
$EditorExe = [System.IO.Path]::Combine($EngineDir, 'Engine', 'Binaries', 'Win64', 'UnrealEditor.exe')
$Bat = @(
	'@echo off',
	'rem Opens the ActionDemo project with the editor UI in English (needed for reliable MCP Blueprint tools).',
	"start `"`" `"$EditorExe`" `"%~dp0ActionDemo.uproject`" -culture=en"
) -join "`r`n"
[System.IO.File]::WriteAllText((Join-Path $ProjectDir 'OpenEditor_EN.bat'), $Bat, $Utf8NoBom)

# --- 5. Optional build --------------------------------------------------------------------------
if ($Build) {
	$BuildBat = [System.IO.Path]::Combine($EngineDir, 'Engine', 'Build', 'BatchFiles', 'Build.bat')
	if (-not (Test-Path -LiteralPath $BuildBat)) {
		throw "Could not find $BuildBat. Pass -EngineDir with your UE 5.8 install folder."
	}
	Write-Step 'Building ActionDemoEditor (Win64 Development)'
	& $BuildBat "${ProjectName}Editor" Win64 Development "-Project=$UProject" -WaitMutex
	if ($LASTEXITCODE -ne 0) { throw "Build failed with exit code $LASTEXITCODE. The compiler errors are printed above." }
}

Write-Host ''
Write-Host 'Done. Next: open ActionDemo\OpenEditor_EN.bat. If the editor asks to rebuild the ActionDemo module, answer Yes.' -ForegroundColor Green
