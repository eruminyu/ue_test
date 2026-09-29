# SoulCombat 프로젝트 준비 스크립트
#
# 템플릿 콘텐츠(마네킹, 애니메이션, 레벨 프로토타이핑 메시, Combat/Platforming 변형)는 저장소에 올리지 않는다.
# 이 스크립트가 엔진 설치 폴더의 템플릿에서 SoulCombat/Content로 복사한다. 이미 있는 폴더는 건너뛴다.
#
# 사용법 (저장소 루트에서):
#   powershell -ExecutionPolicy Bypass -File Tools\Setup-Project.ps1            # 콘텐츠 복사만
#   powershell -ExecutionPolicy Bypass -File Tools\Setup-Project.ps1 -Build     # 복사 + C++ 에디터 모듈 빌드
#   powershell -ExecutionPolicy Bypass -File Tools\Setup-Project.ps1 -Launch    # 에디터 실행 (MCP 서버 자동 시작)

param(
    [string]$EngineDir = "C:\Program Files\Epic Games\UE_5.8",
    [switch]$Build,
    [switch]$Launch
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ProjectDir = Join-Path $RepoRoot "SoulCombat"
$ProjectFile = Join-Path $ProjectDir "SoulCombat.uproject"
$Content = Join-Path $ProjectDir "Content"
$Templates = Join-Path $EngineDir "Templates"
$Resources = Join-Path $Templates "TemplateResources"

if (-not (Test-Path $ProjectFile)) { throw "프로젝트 파일이 없습니다: $ProjectFile" }
if (-not (Test-Path $Templates)) { throw "엔진 템플릿 폴더가 없습니다: $Templates (-EngineDir로 지정)" }

function Copy-Pack([string]$Source, [string]$Destination) {
    if (-not (Test-Path $Source)) { Write-Warning "원본 없음: $Source"; return }
    if (Test-Path $Destination) { Write-Host "건너뜀 (이미 있음): $Destination"; return }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    Copy-Item -Path $Source -Destination $Destination -Recurse
    Write-Host "복사: $Destination"
}

# 1. Third Person BP 템플릿 본체
$Tp = Join-Path $Templates "TP_ThirdPersonBP\Content"
Copy-Pack (Join-Path $Tp "ThirdPerson") (Join-Path $Content "ThirdPerson")
Copy-Pack (Join-Path $Tp "__ExternalActors__\ThirdPerson") (Join-Path $Content "__ExternalActors__\ThirdPerson")
Copy-Pack (Join-Path $Tp "__ExternalObjects__\ThirdPerson") (Join-Path $Content "__ExternalObjects__\ThirdPerson")

# 2. 공유 팩 (High): 마네킹, 레벨 프로토타이핑, 입력
foreach ($Pack in @("Characters", "LevelPrototyping", "Input")) {
    Copy-Pack (Join-Path $Resources "High\$Pack\Content") (Join-Path $Content $Pack)
}

# 3. 변형 팩 (Standard): Combat(콤보/차지 몽타주, 적 AI 참고), Platforming(대시 몽타주)
foreach ($Pack in @("Variant_Combat", "Variant_Platforming")) {
    $Base = Join-Path $Resources "Standard\$Pack"
    Copy-Pack (Join-Path $Base "Content") (Join-Path $Content $Pack)
    Copy-Pack (Join-Path $Base "__ExternalActors__") (Join-Path $Content "__ExternalActors__\$Pack")
    Copy-Pack (Join-Path $Base "__ExternalObjects__") (Join-Path $Content "__ExternalObjects__\$Pack")
}

if ($Build) {
    $BuildBat = Join-Path $EngineDir "Engine\Build\BatchFiles\Build.bat"
    & $BuildBat SoulCombatEditor Win64 Development "-Project=$ProjectFile" -WaitMutex
    if ($LASTEXITCODE -ne 0) { throw "빌드 실패 (exit $LASTEXITCODE)" }
}

if ($Launch) {
    $Editor = Join-Path $EngineDir "Engine\Binaries\Win64\UnrealEditor.exe"
    Start-Process -FilePath $Editor -ArgumentList @("`"$ProjectFile`"", "-culture=en", "-ModelContextProtocolStartServer")
    Write-Host "에디터 실행. MCP 서버: http://127.0.0.1:8000/mcp"
}
