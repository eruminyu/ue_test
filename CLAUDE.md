# CLAUDE.md

이 저장소는 언리얼 엔진 5.8 팀 프로젝트(비상업 포트폴리오)의 전투 프로토타입 `SoulCombat`이다. 소울워커식 스킬 전투가 중심이고 GAS(Gameplay Ability System)를 쓴다. 블루프린트는 Unreal MCP로 만든다.

## 대화 규칙

- 사용자에게는 항상 **한국어**로 답한다.
- **C++는 GAS에 꼭 필요한 것만** 둔다: `SoulCombat/Source/SoulCombat/SCAttributeSet.*`(속성 세트), `SCAbilitySet.*`(어빌리티 세트 데이터 에셋). 게임 로직은 전부 블루프린트다. 새 C++ 클래스가 필요해 보이면 먼저 이유와 BP 대안을 사용자에게 말한다.
- 푸시하지 않는다(사용자 요청). 커밋은 로컬에만 한다.

## 문서

- `docs/01-game-spec.md`: 게임 사양(조작, 수치, 태그, 에셋 목록, 던전 흐름, 완료 기준)
- `docs/02-build-plan.md`: MCP 작업 순서
- `docs/03-build-log.md`: 단계별 결과 기록
- `docs/mcp-cookbook.md`: 이 에디터 버전에서 확인한 MCP 툴 사용법과 제약

## Unreal MCP 사용 규칙

- 에디터가 먼저 켜져 있어야 한다: `powershell -ExecutionPolicy Bypass -File Tools\Setup-Project.ps1 -Launch` (MCP 서버 `http://127.0.0.1:8000/mcp` 자동 시작).
- 툴 이름과 인자는 추측하지 말고 `list_toolsets`, `describe_toolset`, `docs/mcp-cookbook.md`로 확인한다.
- **에디터 하나에 MCP 호출은 한 번에 하나.** 여러 에이전트가 동시에 MCP를 부르면 응답이 섞인다. MCP를 쓰는 에이전트는 반드시 순차로 돌린다. 같은 에셋을 바꾸는 호출은 순서대로 하고, 결과를 항상 읽고 다음으로 넘어간다(실패해도 예외 없이 상태값만 돌아오는 툴이 많다).
- PIE 중에는 에셋을 편집하지 않는다. 컴파일, 레벨 로딩 중에는 호출이 멈출 수 있으니 기다렸다 다시 시도한다.
- 모달 창이 뜰 만한 작업(변수 타입 변경, 저장 안 된 레벨에서 레벨 전환 등)은 피한다. 멈추면 사용자에게 창을 닫아 달라고 한다.
- 템플릿 원본 에셋(`/Game/ThirdPerson`, `/Game/Characters`, `/Game/Variant_*`, `/Game/LevelPrototyping`, `/Game/Input`)은 수정하지 않는다. 필요하면 `/Game/SoulCombat`로 복제해서 쓴다.
- 새 에셋은 모두 `/Game/SoulCombat` 아래, `docs/01-game-spec.md`의 이름 그대로 만든다. 실험용 에셋은 `/Game/_Scratch`에 만들고 끝나면 지운다.
- 에셋을 바꾸면 `AssetTools.save_assets`로 저장한다. 블루프린트는 `compile_blueprint`가 에러·경고 없이 통과해야 끝난 것이다.
- 전용 툴이 없으면 ProgrammaticToolset(툴 묶어 호출)이나 SlateInspectorToolset(UI 조작)을 쓰되, 기록에 그렇게 남긴다.
- 스크린샷은 컨텍스트를 많이 먹는다. 검증 단계에서만 찍고, 이미지는 파일로 저장한다.

## 블루프린트 작성 규칙

- 그래프는 사람이 읽기 쉽게 정리한다: 실행 흐름은 왼쪽에서 오른쪽, 기능 단위로 주석 박스(Comment)를 두르고 한국어로 무엇을 하는지 적는다.
- 함수와 변수에는 카테고리와 설명(Tooltip)을 단다. 매직 넘버는 변수(인스턴스 편집 가능)로 뺀다.
- 모듈화: 공통 기능은 부모 BP나 액터 컴포넌트로, UI는 재사용 위젯(바, 슬롯)을 조립해서 만든다. BP 사이 통신은 이벤트 디스패처나 게임플레이 이벤트로 하고 하드 캐스트는 최소화한다.

## Git

- 단계가 하나 끝날 때마다 커밋한다. 대상은 `SoulCombat/Content/SoulCombat`, `SoulCombat/Config`, `SoulCombat/Source`, `docs/`, `Tools/`.
- 템플릿 콘텐츠(`SoulCombat/Content`의 나머지)는 `.gitignore`로 제외돼 있다. 강제로 추가하지 않는다.
- 커밋 전에 에디터에서 모두 저장됐는지 확인한다.
