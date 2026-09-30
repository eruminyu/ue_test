# 06. 다른 PC에서 이어서 하기 (지시문)

다른 컴퓨터에서 SoulCombat 작업을 이어갈 때 쓴다. 1장은 사람이 할 준비이고, 2장은 코딩 에이전트에 붙여넣는 지시문이다. Codex는 저장소의 `AGENTS.md`, Claude Code는 `CLAUDE.md`도 읽는다.

2026-09-30 현재는 **게임 제작과 개선을 우선하고, 학습은 나중으로** 미룬다. 가능한 독립 작업은 여러 에디터로 병행한다. 초기 PC 준비 결과는 `08-pc-validation.md`, 현재 제작 범위와 통합 기록은 `09-production-plan.md`, 조작·배포 절차는 `10-play-guide.md`에서 확인한다. `AGENTS.md`의 작업 분리·통합 규칙을 따른다. `07-study-guide.md`는 이후 학습용 참고 자료다. 포트폴리오 직군이나 애니메이션 팩 결정은 해당 개선 작업을 시작할 때만 필요하다.

## 1. 사람이 할 준비

1. 설치: UE 5.8(Epic 런처), Visual Studio 2022 이상(C++를 사용한 게임 개발 워크로드), Git, Git LFS. LFS는 처음 한 번 `git lfs install`을 실행한다.
2. 저장소를 받는다. LFS 에셋(약 68MB)도 같이 받아진다.
   ```
   git clone https://github.com/eruminyu/ue_test.git
   ```
3. 저장소 루트에서 템플릿 콘텐츠를 복사하고 C++ 모듈을 빌드한다. 엔진이 `C:\Program Files\Epic Games\UE_5.8`에 없으면 `-EngineDir "<엔진 경로>"`를 붙인다.
   ```
   powershell -ExecutionPolicy Bypass -File Tools\Setup-Project.ps1 -Build
   ```
4. 에디터를 켠다. `L_CombatField`가 열리고 MCP 서버가 `http://127.0.0.1:8000/mcp`에서 시작된다. 처음에는 셰이더 컴파일 때문에 오래 걸린다.
   ```
   powershell -ExecutionPolicy Bypass -File Tools\Setup-Project.ps1 -Launch
   ```
5. 에디터에서 Play를 눌러 좌클릭 콤보, Q/E/R, 게이트 앞 F가 되는지 본다.
6. Claude Code를 저장소 루트에서 열고, `.mcp.json`의 `unreal-mcp` 서버 사용을 승인한다. 에디터가 켜진 뒤에 연결된다.
7. 아래 2장의 지시문을 붙여넣는다.

### 현재 PC에서 다시 켜기

저장소는 `D:\Project\UE\AstraTest\ue_test`, 엔진은 `D:\Program Files\Epic Games\UE_5.8`이다. 이 저장소 루트에서 실행한다. 이미 같은 프로젝트의 에디터가 실행 중이면 중복 실행하지 않는다.

```powershell
powershell -ExecutionPolicy Bypass -File Tools\Setup-Project.ps1 -EngineDir "D:\Program Files\Epic Games\UE_5.8" -Launch
```

현재 PC의 통합 에디터는 `.mcp.json`과 일치하는 8000을 사용한다. 병행 제작 사본 A/B는 각각 8001/8002를 사용했으며 반환 후 종료했다. 빌드·패키징을 다시 할 때는 Live Coding 충돌을 피하도록 실행 중인 UE 에디터를 먼저 저장·종료한다.

## 2. 작업 재개 지시문

```
SoulCombat 작업을 다른 PC에서 이어서 한다. 이전 세션의 대화 기록은 없고, 필요한 맥락은 저장소 문서에 있다.

먼저 읽을 것
- AGENTS.md와 CLAUDE.md(규칙), README.md(구성), docs/09-production-plan.md(현재 제작 범위), docs/11-production-validation.md(최신 검증 근거), docs/10-play-guide.md(실행·조작), docs/checklist.md(남은 확인)
- 초기 PC 준비와 이후 학습이 필요할 때: docs/08-pc-validation.md, docs/07-study-guide.md
- 개선 후보를 검토할 때: docs/05-portfolio-roadmap.md. 이 문서를 학습 필수 순서로 취급하지 않는다.
- MCP로 에셋을 만들기 전: docs/mcp-cookbook.md와 docs/parallel/*-cookbook.md에서 그 작업에 해당하는 부분
- 필요할 때만: docs/01-game-spec.md(사양), docs/02-build-plan.md(에셋별 설계), docs/03-build-log.md(제작 기록), docs/04-final-qa.md(QA), docs/engine-api-notes.md

1. 환경 점검 (각 에디터의 MCP 호출은 한 번에 하나)
- unreal-mcp가 연결되는지 list_toolsets로 확인한다. 안 되면 에디터가 켜져 있는지 나에게 묻는다.
- 현재 레벨이 /Game/SoulCombat/Maps/L_CombatField인지, /Game/SoulCombat의 실제 블루프린트 목록 전체가 에러·경고 없이 컴파일되는지 확인한다. 초기 기록의 BP72/에셋104를 현재 개수로 고정하지 않는다.
- 점검만 했으면 에셋을 저장하지 않는다. 끝나고 git status에 변경이 없는지 확인한 뒤 결과를 짧게 보고한다.
- 현재 회귀 소스와 실행 절차는 Tools/tests/README.md에 있다. PythonScriptPlugin을 테스트 프로세스에서 활성화하고 Tools/tests/ue_test_bridge.py로 실제 PIE 액터를 검사한다. 검사 도중 에셋을 편집하거나 저장하지 않고 결과 JSON의 done=true까지 기다린다. 초기 QA의 /Game/_Scratch 테스트 에셋은 현재 회귀에 필요하지 않다.

2. 다음 작업: 게임 제작과 개선
- 지금은 게임 제작을 우선하고 공부는 나중에 한다. 내가 요청한 기능은 승인된 범위에서 구현·검증·통합한다. 입력·피해·취소를 함께 공부하는 활동을 제작의 선행 작업으로 넣지 않는다.
- 나중에 비슷한 기능을 공부 목적으로 물으면 해결 방향과 힌트, 관찰할 변수와 작은 실험을 먼저 알려 준다. 현재 구현을 유일한 정답으로 설명하지 않는다.
- Shipping 빌드와 시작 확인은 이 PC에서 완료했다. 새 PC에서는 환경에 맞게 다시 검증하고, 사람의 실제 조작 검증은 별도 기록한다. 오류를 수정해야 하면 먼저 원인과 해결안을 설명하고 확인을 받는다.
- 포트폴리오 로드맵을 실제로 시작할 때 지원 직군과 애니메이션 교체 여부를 정한다. 1단계를 시작하기 전에 docs/02-build-plan.md 형식으로 상세 설계를 써서 내 확인을 받는다.
- MCP로 되는지 모르는 작업(몽타주 노티파이 추가, Niagara, 카메라 셰이크, StateTree 편집)은 /Game/_Scratch에서 먼저 시험하고, 결과를 docs/mcp-cookbook.md에 남긴다.

규칙 요약 (자세한 것은 CLAUDE.md)
- 나에게는 한국어로 답한다.
- C++를 더 써야 할 것 같으면 먼저 이유와 BP 대안을 말한다. 프로그래머 트랙을 고르면 이 규칙부터 나와 다시 정한다.
- 단계마다 로컬에 커밋한다. 푸시는 내가 요청할 때만 한다.
- 커밋 전에 docs/checklist.md와 작업 기록을 갱신한다.
- 사용자는 가능한 작업의 여러 에디터 병행을 승인했다. 독립 작업은 같은 기준 커밋의 별도 프로젝트 사본·고유 포트·담당 에셋으로 나눈다. 같은 에디터의 MCP 호출, 같은 에셋 수정, 클립보드/UI 작업은 겹치지 않는다. 결과의 실제 변경과 검증 근거를 회수하고 통합 후 관련 회귀를 수행한다. 상세 규칙은 AGENTS.md의 병행 작업 절을 따른다.
- 템플릿 원본 에셋은 수정하지 않는다. 새 에셋은 /Game/SoulCombat에, 실험용 에셋은 /Game/_Scratch에 만든다.
```
