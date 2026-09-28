# ue_test

언리얼 엔진 팀 프로젝트(비상업 포트폴리오, 소울워커식 스킬 시스템 기반 액션 RPG)의 준비 저장소다.

- 진행 보고서: [UE 액션 RPG 팀 프로젝트 진행 보고서](https://claude.ai/code/artifact/a30d57c0-d178-4e7f-a28a-42b41b864db5)
- 지금 하는 일: UE 5.8의 Unreal MCP로 Claude가 블루프린트를 어디까지 만들 수 있는지 확인하는 데모 `ActionDemo`

## ActionDemo 빠른 시작

1. [01-setup-windows.md](docs/demo/01-setup-windows.md)대로 UE 5.8, Visual Studio 2022, Git, Claude Code를 설치한다.
2. UE 5.8에서 **Third Person / Blueprint** 프로젝트를 저장소 폴더에 `ActionDemo`라는 이름으로 만들고 에디터를 닫는다.
3. `powershell -ExecutionPolicy Bypass -File DemoKit\install.ps1 -Build`
4. `ActionDemo\OpenEditor_EN.bat`으로 에디터를 연다.
5. 저장소 폴더에서 Claude Code를 열고 "docs/demo/03-mcp-build-plan.md 순서대로 진행해줘"라고 한다.

## 구성

| 경로 | 내용 |
| --- | --- |
| `DemoKit/` | 설치 스크립트와 C++ 모듈 원본. C++ 클래스는 `UDemoAttributeSet` 하나뿐이다 |
| `docs/demo/` | 설치 방법, 데모 사양, MCP 작업 계획, 테스트 기록 |
| `CLAUDE.md` | PC에서 도는 Claude Code 세션이 지킬 규칙 |
| `.mcp.json` | Unreal MCP 서버 주소 (`http://127.0.0.1:8000/mcp`) |
| `.claude/settings.json` | Epic 공식 Claude Code 플러그인과 MCP 서버 사용 설정 |
| `ActionDemo/` | 2번 단계에서 생기는 UE 프로젝트. 템플릿 콘텐츠는 커밋하지 않고 `Content/Demo`만 커밋한다 |
