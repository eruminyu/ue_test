param(
    [string]$EngineDir = 'D:\Program Files\Epic Games\UE_5.8',
    [string]$ArchiveDir = '',
    [switch]$PlanOnly
)

$ErrorActionPreference = 'Stop'
$repoPath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$projectPath = Join-Path $repoPath 'SoulCombat\SoulCombat.uproject'
$automationPath = Join-Path $EngineDir 'Engine\Build\BatchFiles\RunUAT.bat'
if (-not (Test-Path -LiteralPath $projectPath)) { throw "프로젝트 없음: $projectPath" }
if (-not (Test-Path -LiteralPath $automationPath)) { throw "엔진 RunUAT 없음: $automationPath" }
if ([string]::IsNullOrWhiteSpace($ArchiveDir)) {
    $ArchiveDir = Join-Path $repoPath 'SoulCombat\Saved\Packages\Win64Shipping'
}
$ArchiveDir = [System.IO.Path]::GetFullPath($ArchiveDir)
$prerequisitePaths = @(
    (Join-Path $ArchiveDir 'Engine\Extras\Redist\en-us\vc_redist.x64.exe'),
    (Join-Path $ArchiveDir 'Engine\Extras\Redist\en-us\vc_redist.arm64.exe')
)
$arguments = @(
    'BuildCookRun', "-project=$projectPath", '-noP4', '-platform=Win64',
    '-clientconfig=Shipping', '-build', '-cook',
    '-map=/Game/SoulCombat/Maps/L_CombatField+/Game/SoulCombat/Maps/L_Dungeon_01',
    '-stage', '-pak', '-iostore', '-prereqs', '-archive',
    "-archivedirectory=$ArchiveDir", '-utf8output'
)
if ($PlanOnly) {
    Write-Output "엔진: $automationPath"
    Write-Output "프로젝트: $projectPath"
    Write-Output "출력: $ArchiveDir"
    foreach ($prerequisitePath in $prerequisitePaths) {
        Write-Output "의존 설치 파일 예상 경로: $prerequisitePath"
    }
    Write-Output ($arguments -join [Environment]::NewLine)
    exit 0
}
$editors = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" |
    Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($EngineDir, [StringComparison]::OrdinalIgnoreCase) }
if ($editors) {
    $runningIds = ($editors.ProcessId -join ', ')
    throw "같은 엔진의 에디터가 실행 중입니다(PID $runningIds). 저장·종료를 확인한 뒤 패키징합니다."
}
& $automationPath @arguments
if ($LASTEXITCODE -ne 0) { throw "패키징 실패: ExitCode $LASTEXITCODE" }
$launcherPath = Join-Path $ArchiveDir 'SoulCombat.exe'
if (-not (Test-Path -LiteralPath $launcherPath)) { throw '패키지 실행 파일이 없습니다.' }
foreach ($prerequisitePath in $prerequisitePaths) {
    if (-not (Test-Path -LiteralPath $prerequisitePath)) {
        throw "런타임 의존 설치 프로그램이 없습니다: $prerequisitePath"
    }
}
Write-Output "패키징 완료: $launcherPath"
