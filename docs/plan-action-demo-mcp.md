# 계획: ActionDemo MCP 블루프린트 제작 검증

## 목적

UE 5.8 에디터에 내장된 Unreal MCP로 Claude가 블루프린트를 어디까지 만들 수 있는지 검증한다. 데모 완성보다 **단계별 판정 기록**(`docs/demo/04-mcp-test-log.md`)이 목표다.

## 1단계 현황 (2026-09-28)

| 항목 | 값 |
| --- | --- |
| 저장소 | `D:\Project\UE\ClaudeTest\ue_test`, 브랜치 `claude/elegant-einstein-ezzm7z` |
| 기존 프로젝트 | `D:\Project\UE\ClaudeTest\test\test.uproject` (C++ 템플릿, 저장소 밖). 사용하지 않고 그대로 둔다 |
| 엔진 | UE 5.8.3 (CL 58210709), `D:\Program Files\Epic Games\UE_5.8` (HKLM 5.8 키 없음, HKCU Builds에 GUID로 등록) |
| 컴파일러 | VS Community 2026 18.10.0, MSVC 14.51.36231, Windows SDK 10.0.26100.0 |

## 결정

- 저장소 루트에 **Third Person / Blueprint** 템플릿으로 `ActionDemo`를 새로 만든다(사용자 작업).
- 이유: 설치 스크립트, `.gitignore`, `CLAUDE.md`, 문서 경로가 모두 이 구성을 전제로 한다. C++ 템플릿은 템플릿 C++ 약 90개가 `Source`에 섞이고, 공격 판정 인터페이스 `ICombatAttacker`가 `NotBlueprintable`이라 BP에서 구현할 수 없다.
- 스크립트 적용 후에도 C++ 클래스는 `UDemoAttributeSet` 하나뿐인 C++ 프로젝트가 된다(GAS AttributeSet 요건 충족).

## 진행 순서

1. 사용자가 BP 템플릿 `ActionDemo`를 만들고 에디터를 닫는다.
2. `powershell -ExecutionPolicy Bypass -File DemoKit\install.ps1 -Build -EngineDir "D:\Program Files\Epic Games\UE_5.8"`
3. `ActionDemo\OpenEditor_EN.bat`으로 영어 UI 에디터를 연다. Output Log에서 MCP 서버의 8000번 포트 시작을 확인한다.
4. `/mcp`로 `unreal-mcp`를 연결한다. Epic 플러그인이 없으면 사용자에게 설치 명령을 안내한다.
5. `docs/demo/03-mcp-build-plan.md` 단계 0~11을 진행하면서 단계마다 04 기록표를 채우고 로컬 커밋한다.

## 변경 파일

| 경로 | 내용 |
| --- | --- |
| `ActionDemo/` | 새 UE 프로젝트. 커밋 대상은 `Content/Demo`, `Config`, `Source`, `.uproject` |
| `ActionDemo/Source/ActionDemo/*` | 스크립트가 복사하는 DemoAttributeSet 모듈. 빌드 에러가 나면 이 파일만 수정한다 |
| `docs/demo/04-mcp-test-log.md` | 단계별 판정 기록 |
| `docs/demo/assets.md` | 단계 1의 템플릿 조사 결과 |
| `docs/demo/screenshots/` | 단계 10의 PIE 스크린샷 |
| `docs/checklist.md`, `docs/done-action-demo-mcp.md` | 작업 기록 |

## 예상 영향과 주의

- 새 C++ 클래스는 추가하지 않는다. BP로 불가능해 보이면 이유와 대안을 먼저 사용자에게 말한다.
- MSVC 14.51은 금지 범위가 아니지만 UE 5.8의 권장 범위(14.50.x)가 아니라서 UBT 경고가 나올 수 있다.
- 에디터는 처음에 한국어로 열리므로 반드시 `OpenEditor_EN.bat`(`-culture=en`)으로 연다.
- Codex CLI는 이번 작업의 MCP 제작에 쓰지 않는다. 이번 실험은 "Claude가 MCP로 어디까지 하는가"를 재는 것이라, 다른 에이전트가 끼면 기록이 오염된다.
- 푸시는 사용자가 말할 때만 한다.
