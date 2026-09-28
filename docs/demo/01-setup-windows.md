# 01. Windows 설치 체크리스트

UE 5.8 MCP 데모(ActionDemo)를 돌리기 위해 PC에 준비할 것들이다. 위에서부터 순서대로 하면 된다.

## 1. 설치할 프로그램

| 프로그램 | 버전과 옵션 | 이유 |
| --- | --- | --- |
| Epic Games Launcher + Unreal Engine | 5.8 최신 핫픽스. 설치 옵션에서 "Templates and Feature Packs"와 "Starter Content"를 켠다 | Third Person 템플릿의 Combat, Platforming 변형 에셋을 그대로 쓴다 |
| Visual Studio 2022 Community | 17.14 최신 업데이트. 아래 워크로드 참고 | C++ 파일이 딱 하나(AttributeSet) 있어서 컴파일러가 필요하다 |
| Git for Windows | 최신. 설치 중 "Git LFS"를 체크한다 | 저장소 클론, Claude Code의 Bash 셸 |
| Claude Code | 데스크톱 앱(로컬 세션) 또는 CLI | 에디터 안의 MCP 서버에 붙는 쪽은 반드시 PC에서 돌아야 한다 |

Visual Studio 설치 관리자에서 고를 것:

- 워크로드: **C++를 사용한 게임 개발**, **C++를 사용한 데스크톱 개발**
- 개별 구성 요소: **MSVC v143 - VS 2022 C++ x64/x86 빌드 도구 (v14.44-17.14)**, **Windows 11 SDK (10.0.22621.0)**, **.NET Framework 4.6.2 타기팅 팩**
- 게임 개발 워크로드 오른쪽 목록의 **Unreal Engine용 IDE 지원**, **Unreal Engine 디버거**도 켜 두면 좋다

UE 5.8의 빌드 도구가 허용하는 MSVC 버전은 다음과 같다(엔진 설정 파일 `Engine/Config/Windows/Windows_SDK.json` 기준).

| 구분 | MSVC 버전 | 해당 Visual Studio |
| --- | --- | --- |
| 권장 | 14.44.35211 이상 | VS 2022 17.14 |
| 권장 | 14.50.35723 이상 | VS 2026 18.x |
| 금지 | 14.40 ~ 14.43, 14.44.35210 이하, 14.50.35722 이하 | 컴파일러 버그가 있는 버전 |

VS 2022를 17.14 최신으로 업데이트해 두면 가장 무난하다.

Claude Code 설치(CLI를 쓸 경우, PowerShell):

```powershell
irm https://claude.ai/install.ps1 | iex
```

## 2. 저장소 준비

```powershell
cd C:\Dev          # 원하는 폴더
git lfs install
git clone https://github.com/eruminyu/ue_test.git
cd ue_test
git checkout claude/elegant-einstein-ezzm7z
```

## 3. 데모 프로젝트 만들기

1. 에픽 런처에서 UE 5.8 실행 → **게임 → 삼인칭(Third Person)** 선택.
2. 프로젝트 유형은 **블루프린트**, 시작용 콘텐츠는 켜고, 레이트레이싱은 끈다.
3. 위치는 저장소 폴더(`C:\Dev\ue_test`), 이름은 **ActionDemo**로 정확히 입력한다. `C:\Dev\ue_test\ActionDemo\ActionDemo.uproject`가 생기면 된다.
4. 에디터가 열리면 **바로 닫는다.**
5. 저장소 폴더에서 설치 스크립트를 실행한다.

```powershell
powershell -ExecutionPolicy Bypass -File DemoKit\install.ps1 -Build
```

스크립트가 하는 일:

- `ActionDemo\Source`에 C++ 모듈을 복사한다. 클래스는 `UDemoAttributeSet` 하나뿐이다.
- `.uproject`에 모듈과 플러그인(GameplayAbilities, ModelContextProtocol, AllToolsets)을 추가한다. 원본은 `.uproject.bak`으로 남긴다.
- Unreal MCP 서버 자동 시작을 켠다(`Config\DefaultEditorPerProjectUserSettings.ini`).
- 에디터를 영어로 여는 `ActionDemo\OpenEditor_EN.bat`을 만든다.
- `-Build`를 붙이면 바로 컴파일해서 에러를 창에 보여준다. 엔진이 다른 곳에 설치됐으면 `-EngineDir "D:\Epic\UE_5.8"`처럼 경로를 준다.

6. `ActionDemo\OpenEditor_EN.bat`으로 에디터를 연다. 모듈을 다시 빌드하겠냐고 물으면 **예**.
7. 에디터 출력 로그(Window → Output Log)에 MCP 서버가 8000번 포트에서 시작됐다는 줄이 보이면 성공이다. 안 보이면 에디터 콘솔(` 키)에 `ModelContextProtocol.StartServer`를 입력한다.

에디터를 매번 영어로 열기 싫으면 Edit → Editor Preferences → Region & Language → Editor Language를 English로 바꿔도 된다. 한글 에디터에서는 MCP의 블루프린트 그래프 확인 도구가 로컬라이즈된 노드 이름 때문에 오작동한다는 보고가 있다.

## 4. Claude Code를 PC에서 연결하기

MCP 서버는 PC의 `127.0.0.1:8000`에만 열린다. 그래서 claude.ai 클라우드 세션은 여기에 닿을 수 없고, **PC에서 도는 Claude Code 세션**이 작업해야 한다. 방법은 둘 중 하나다.

- **데스크톱 앱:** Claude 데스크톱 앱 → Code 탭 → 환경을 **Local**로, 폴더를 `C:\Dev\ue_test`로 연다.
- **터미널 + 원격 제어:** `C:\Dev\ue_test`에서 `claude remote-control`을 실행하면 Claude 앱(웹, 모바일)에서 그 세션을 이어서 조종할 수 있다.

세션을 처음 열면:

1. 프로젝트의 MCP 서버 `unreal-mcp`와 Epic 공식 플러그인 사용을 허락한다. 둘 다 `.mcp.json`, `.claude/settings.json`에 미리 적어 두었다.
2. 플러그인이 설치 안 됐다고 나오면 `/plugin install unreal-engine-skills-for-claude-code@claude-plugins-official`을 입력한다.
3. `/mcp`로 `unreal-mcp`가 connected인지 확인한다. 에디터가 먼저 켜져 있어야 한다.
4. 그다음 "docs/demo/03-mcp-build-plan.md 순서대로 진행해줘"라고 시키면 된다. 규칙은 `CLAUDE.md`에 있다.

## 5. 자주 막히는 곳

| 증상 | 원인과 해결 |
| --- | --- |
| `/mcp`에 툴이 3개(list_toolsets 등)만 보인다 | 정상이다. Tool Search 모드라 필요할 때 툴셋을 불러온다 |
| list_toolsets 결과가 거의 비어 있다 | All Toolsets 플러그인이 꺼져 있다. 스크립트를 다시 돌리거나 Edit → Plugins에서 켠다 |
| 에디터 재시작 후 Claude 쪽 연결이 끊긴다 | 정상 동작이다. `/mcp`에서 재연결한다. Epic 플러그인의 stdio 프록시를 설치하면 끊기지 않는다 |
| 모듈 빌드 실패 | `DemoKit\install.ps1 -Build`로 에러를 보고, 그 출력을 Claude에게 준다 |
| Failed to listen on port 8000 | 다른 프로그램이 8000번을 쓰고 있다. Editor Preferences → Model Context Protocol에서 포트를 바꾸고 `.mcp.json`도 같이 바꾼다 |
