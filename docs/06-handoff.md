# 06. 다른 PC에서 이어서 하기 (지시문)

다른 컴퓨터에서 SoulCombat 작업을 이어갈 때 쓴다. 1장은 사람이 할 준비이고, 2장은 코딩 에이전트에 붙여넣는 지시문이다. Codex는 저장소의 `AGENTS.md`, Claude Code는 `CLAUDE.md`도 읽는다.

2026-09-30 현재 목적은 **언리얼 학습용 참고 사례**다. `07-study-guide.md`에서 학습 순서와 힌트 방식을, `08-pc-validation.md`에서 현재 PC 재검증 결과를 확인한다. 포트폴리오 직군이나 애니메이션 팩 결정은 해당 개선 작업을 시작할 때만 필요하다.

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

현재 PC 점검에서는 포트 8001을 사용했지만, 작업 재개용 에디터는 `.mcp.json`과 일치하는 8000으로 확인했다. 빌드·패키징을 다시 할 때는 Live Coding 충돌을 피하도록 실행 중인 UE 에디터를 먼저 종료한다.

## 2. 작업 재개 지시문

```
SoulCombat 작업을 다른 PC에서 이어서 한다. 이전 세션의 대화 기록은 없고, 필요한 맥락은 저장소 문서에 있다.

먼저 읽을 것
- AGENTS.md와 CLAUDE.md(규칙), README.md(구성), docs/07-study-guide.md(학습 목적), docs/08-pc-validation.md(현재 PC 검증), docs/checklist.md(남은 확인)
- 개선 후보를 검토할 때: docs/05-portfolio-roadmap.md. 이 문서를 학습 필수 순서로 취급하지 않는다.
- MCP로 에셋을 만들기 전: docs/mcp-cookbook.md와 docs/parallel/*-cookbook.md에서 그 작업에 해당하는 부분
- 필요할 때만: docs/01-game-spec.md(사양), docs/02-build-plan.md(에셋별 설계), docs/03-build-log.md(제작 기록), docs/04-final-qa.md(QA), docs/engine-api-notes.md

1. 환경 점검 (MCP 호출은 한 번에 하나)
- unreal-mcp가 연결되는지 list_toolsets로 확인한다. 안 되면 에디터가 켜져 있는지 나에게 묻는다.
- 현재 레벨이 /Game/SoulCombat/Maps/L_CombatField인지, /Game/SoulCombat의 블루프린트 72개가 에러·경고 없이 컴파일되는지 확인한다(docs/04-final-qa.md 1-1과 같은 방법).
- 점검만 했으면 에셋을 저장하지 않는다. 끝나고 git status에 변경이 없는지 확인한 뒤 결과를 짧게 보고한다.
- 자동 테스트용 에셋(/Game/_Scratch의 BP_TestPlayerDriver, BP_TestKiller, BP_TestGateDriver와 테스트 맵)은 저장소에 없다. PIE 테스트가 필요해지면 docs/04-final-qa.md의 설명대로 다시 만든다.

2. 다음 작업: 학습과 필요한 개선
- 나는 언리얼 게임 개발을 배우며 이 프로젝트를 참고 교재로 쓴다. 비슷한 구현을 물으면 먼저 해결 방향과 힌트, 관찰할 변수와 작은 실험을 알려 준다. 완성 구현은 내가 요청한 범위에서 한다.
- 입력·피해·취소 중 하나의 실제 경로를 따라가고, 현재 선택을 유일한 정답으로 설명하지 않는다. 학습 안내의 개선 후보는 구현 승인이 아니다.
- Shipping 빌드와 시작 확인은 이 PC에서 완료했다. 새 PC에서는 환경에 맞게 다시 검증하고, 사람의 실제 조작 검증은 별도 기록한다. 오류를 수정해야 하면 먼저 원인과 해결안을 설명하고 확인을 받는다.
- 포트폴리오 로드맵을 실제로 시작할 때 지원 직군과 애니메이션 교체 여부를 정한다. 1단계를 시작하기 전에 docs/02-build-plan.md 형식으로 상세 설계를 써서 내 확인을 받는다.
- MCP로 되는지 모르는 작업(몽타주 노티파이 추가, Niagara, 카메라 셰이크, StateTree 편집)은 /Game/_Scratch에서 먼저 시험하고, 결과를 docs/mcp-cookbook.md에 남긴다.

규칙 요약 (자세한 것은 CLAUDE.md)
- 나에게는 한국어로 답한다.
- C++를 더 써야 할 것 같으면 먼저 이유와 BP 대안을 말한다. 프로그래머 트랙을 고르면 이 규칙부터 나와 다시 정한다.
- 단계마다 로컬에 커밋한다. 푸시는 내가 요청할 때만 한다.
- 커밋 전에 docs/checklist.md와 작업 기록을 갱신한다.
- 템플릿 원본 에셋은 수정하지 않는다. 새 에셋은 /Game/SoulCombat에, 실험용 에셋은 /Game/_Scratch에 만든다.
```
