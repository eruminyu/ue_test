# SoulCombat

언리얼 엔진 5.8 팀 프로젝트(비상업 포트폴리오)의 전투 프로토타입. 소울워커식 스킬 전투를 GAS로 만든다. C++는 GAS에 꼭 필요한 속성 세트와 어빌리티 세트 데이터 에셋뿐이고, 나머지는 전부 블루프린트다. 블루프린트는 Unreal MCP로 만들었다.

## 빠른 시작 (Windows)

1. UE 5.8(런처 설치)과 Visual Studio 2022 이상(C++ 게임 개발 워크로드)을 설치한다.
2. 저장소 루트에서 템플릿 콘텐츠를 복사하고 C++ 모듈을 빌드한다.
   ```
   powershell -ExecutionPolicy Bypass -File Tools\Setup-Project.ps1 -Build
   ```
   엔진이 기본 위치가 아니면 `-EngineDir "D:\Epic Games\UE_5.8"`을 붙인다.
3. 에디터를 연다(MCP 서버가 `http://127.0.0.1:8000/mcp`에서 자동 시작).
   ```
   powershell -ExecutionPolicy Bypass -File Tools\Setup-Project.ps1 -Launch
   ```
4. PIE로 `L_CombatField`를 플레이한다.

## 조작

WASD 이동, 마우스 카메라, 좌클릭 4콤보, 우클릭 가드, Shift 대시, Space 점프, Q/E/R 스킬, F 상호작용.

## 구성

| 경로 | 내용 |
| --- | --- |
| `SoulCombat/` | UE 프로젝트. 직접 만든 에셋은 `Content/SoulCombat`에만 있다 |
| `SoulCombat/Source/SoulCombat/` | C++: `SCAttributeSet`, `SCAbilitySet` |
| `Tools/Setup-Project.ps1` | 템플릿 콘텐츠 복사, 빌드, 에디터 실행 |
| `docs/01-game-spec.md` | 게임 사양 |
| `docs/02-build-plan.md` | MCP 작업 순서 |
| `docs/03-build-log.md` | 단계별 결과 기록 |
| `docs/mcp-cookbook.md` | UE 5.8.2 Unreal MCP 사용법과 제약 |
| `CLAUDE.md` | Claude Code 세션 규칙 |
