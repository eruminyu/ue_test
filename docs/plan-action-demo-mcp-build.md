# 계획: ActionDemo MCP 제작 (단계 0~11)

## 목적

UE 5.8 에디터 내장 Unreal MCP로 ActionDemo의 블루프린트를 만들고, 단계마다 "MCP로 된 것과 안 된 것"을 `docs/demo/04-mcp-test-log.md`에 기록한다. 데모 완성보다 기록이 우선이다.

## 기준 문서

- 작업 순서: `docs/demo/03-mcp-build-plan.md` (단계 0~11 그대로)
- 사양: `docs/demo/02-demo-spec.md`
- 규칙: 저장소 루트 `CLAUDE.md`

## 변경 파일

- `ActionDemo/Content/Demo/**` (새 에셋 전부)
- `ActionDemo/Config/DefaultGameplayTags.ini`, `DefaultEngine.ini`(기본 맵), 필요 시 `DefaultGame.ini`
- `docs/demo/04-mcp-test-log.md`, `docs/demo/assets.md`, `docs/demo/screenshots/`
- C++는 `ActionDemo/Source/ActionDemo/DemoAttributeSet.*` 외에 추가하지 않는다

## 진행 방식

- MCP 호출은 **한 번에 하나씩** 순차로 한다. 단계 1에서 동시 호출 시 응답이 뒤섞이는 현상을 확인했다.
- 단계 1(읽기 전용 조사)은 서브에이전트에게 맡기되 에이전트도 하나씩 순차 실행한다.
- 전용 툴을 묶어 부르는 ProgrammaticToolset 사용은 "성공"으로, 전용 툴 대신 우회한 경우만 "Python"으로 기록한다. 단, ProgrammaticToolset은 `unreal` 모듈을 못 쓰므로 계획서의 Python 대체안은 대부분 불가하다.
- 단계마다 로컬 커밋. 푸시는 사용자가 말할 때만.

## 멈추고 사용자를 부르는 경우

모달 창으로 멈춤, Enhanced Input 이벤트 노드가 PIE에서 안 불림, Fab 다운로드 필요, 에디터 크래시.

## 예상 영향 범위

템플릿 원본 콘텐츠는 수정하지 않는다(`/Game/Demo`로 복제). 프로젝트 설정 중 게임플레이 태그와 기본 맵만 바뀐다.
