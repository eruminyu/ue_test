# CLAUDE.md

이 저장소는 언리얼 엔진 팀 프로젝트(비상업 포트폴리오, 소울워커식 액션 RPG)의 준비 저장소다. 지금은 UE 5.8의 Unreal MCP로 Claude가 블루프린트를 얼마나 만들 수 있는지 확인하는 데모 `ActionDemo`를 진행 중이다.

## 대화 규칙

- 사용자에게는 항상 **한국어**로 답한다.
- 사용자는 C++ 작업을 최소화하고 BP로 만들기를 원한다. C++는 `ActionDemo/Source/ActionDemo/DemoAttributeSet.*` 하나만 있다. 새 C++ 클래스를 추가하지 말고, BP로 불가능해 보이면 이유와 대안을 먼저 사용자에게 말한다.

## 문서

- `docs/demo/01-setup-windows.md`: PC 설치와 연결 방법
- `docs/demo/02-demo-spec.md`: 데모 사양(조작, 수치, 태그, 에셋 목록, 완료 기준)
- `docs/demo/03-mcp-build-plan.md`: 작업 순서. 여기 순서대로 진행한다
- `docs/demo/04-mcp-test-log.md`: 결과 기록. 단계마다 채운다

## Unreal MCP 사용 규칙

- 에디터가 먼저 켜져 있어야 한다. 끊기면 `/mcp`로 재연결을 요청한다.
- 툴 이름과 인자는 추측하지 말고 `list_toolsets`, `describe_toolset`으로 확인한다.
- **한 번에 한 작업.** 같은 에셋을 바꾸는 호출은 순서대로 한다. 결과를 항상 읽고 다음으로 넘어간다. 실패해도 예외 없이 상태값만 돌아오는 툴이 많다.
- PIE 중에는 에셋을 편집하지 않는다. 컴파일, 레벨 로딩 중에는 호출이 멈출 수 있으니 기다렸다 다시 시도한다.
- 모달 창이 뜰 만한 작업(변수 타입 변경, 렌더 타깃 크기 변경 등)은 피한다. 멈추면 사용자에게 창을 닫아 달라고 한다.
- 템플릿 원본 에셋은 수정하지 않는다. `/Game/Demo`로 복제해서 쓴다.
- 새 에셋은 모두 `/Game/Demo` 아래, `02-demo-spec.md`의 이름 그대로 만든다.
- Enhanced Input 이벤트 노드는 MCP로 만들면 안 불릴 수 있다. 계획서 단계 7의 절차대로 확인한다.
- 전용 툴이 없으면 ProgrammaticToolset의 Python 실행을 써도 되지만, 기록에 "Python"으로 남긴다.
- 스크린샷은 컨텍스트를 많이 먹는다. 검증 단계에서만 찍는다.

## Git

- 단계가 하나 끝날 때마다 커밋한다. 대상은 `ActionDemo/Content/Demo`, `ActionDemo/Config`, `ActionDemo/Source`, `docs/`.
- 템플릿 원본 콘텐츠(`ActionDemo/Content`의 나머지)는 `.gitignore`로 제외돼 있다. 강제로 추가하지 않는다.
- 커밋 전에 에디터에서 모두 저장(Save All)됐는지 확인한다.
