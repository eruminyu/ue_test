# SoulCombat

언리얼 엔진 5.8 팀 프로젝트(비상업 포트폴리오)의 전투 프로토타입. 소울워커식 스킬 전투를 GAS로 만들었다. C++는 GAS에 꼭 필요한 속성 세트(`SCAttributeSet`)와 어빌리티 세트 데이터 에셋(`SCAbilitySet`)뿐이고, 나머지는 전부 블루프린트다. 블루프린트는 Unreal MCP로 만들었고, 모든 그래프는 정리돼 있으며 기능 단위 한국어 주석 박스가 달려 있다.

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
4. 시작 맵 `L_CombatField`에서 PIE(Play)를 누른다.

## 조작

| 입력 | 동작 |
| --- | --- |
| WASD, 마우스 | 이동, 카메라 |
| 좌클릭 | 기본 공격 4콤보 |
| 우클릭 (누르는 동안) | 가드 (정면 공격 피해 20%, 경직 없음) |
| Left Shift | 대시 (0.35초 무적, 공격·스킬·경직 캔슬) |
| Space | 점프 |
| Q / E / R | 돌진 베기 / 대지 강타(띄우기) / 검기 날리기(관통 투사체) |
| F | 상호작용 (던전 게이트 열기) |

## 플레이 흐름

1. **전투 테스트 필드**: 훈련 더미 3개(죽으면 3초 뒤 부활), 스파링 구역의 잡몹 2마리(가드 연습용), 북쪽의 던전 게이트.
2. 게이트 앞에서 **F** → 문이 열리고 포털이 빛난다 → 포털에 들어가면 **던전 입장 확인 창** → [입장].
3. **던전 "시련의 회랑"**: Start → Mob(웨이브 2) → Event(30초 안에 봉인석 3개 파괴, 성공하면 회복과 공격력 버프) → Mob(웨이브 2) → Boss(수호자: 연속 베기, 예고원 내려찍기, 돌진, HP 50%에 분노).
4. 보스를 쓰러뜨리면 **DUNGEON CLEAR** 창(클리어 시간, 5초 카운트다운) → 필드의 게이트 앞으로 복귀.

## 구성

| 경로 | 내용 |
| --- | --- |
| `SoulCombat/` | UE 프로젝트. 직접 만든 에셋은 `Content/SoulCombat`에만 있다(블루프린트 72개 포함 104개) |
| `SoulCombat/Source/SoulCombat/` | C++: `SCAttributeSet`, `SCAbilitySet` |
| `Tools/` | 준비 스크립트, MCP HTTP 클라이언트, 그래프 배치·주석 도구 |
| `docs/01-game-spec.md` | 게임 사양 |
| `docs/02-build-plan.md` | 에셋별 상세 설계와 MCP 작업 순서 |
| `docs/03-build-log.md`, `docs/parallel/` | 단계별 제작 기록 (두 번째 에디터 작업분은 parallel) |
| `docs/04-final-qa.md` | 최종 QA 결과 |
| `docs/05-portfolio-roadmap.md` | 포트폴리오 발전 로드맵 |
| `docs/mcp-cookbook.md` | UE 5.8.2 Unreal MCP 사용법과 제약 |
| `docs/engine-api-notes.md` | GAS·엔진 API 검증 노트 |
| `docs/screenshots/` | 레벨 평면도, PIE 화면, 그래프 스크린샷 |
| `CLAUDE.md` | Claude Code 세션 규칙 |

## 주요 설계

- **전투 컴포넌트 `AC_CombatComponent`**: ASC 초기화(스탯 테이블, 어빌리티 세트), 입력 태그 → 어빌리티 발동, 대상 찾기·피해·가드 판정·넉백, 사망·부활. 플레이어, 몬스터, 보스, 봉인석, 검기 투사체가 같이 쓴다.
- **어빌리티**: `GA_SCBase`(공통) → `GA_ActionBase`(몽타주 + 타격 시점 행동) → 스킬 3종·몬스터 공격. 기본 공격은 템플릿 콤보 몽타주의 섹션 점프 + 차지 공격 피니시. 캔슬 규칙은 태그로(대시 > 스킬 > 가드 > 평타).
- **UI**: 재사용 위젯(`WBP_AttributeBar`, `WBP_SkillSlot`)을 조립한 HUD. 게임 쪽 BP는 플레이어 컨트롤러의 공개 함수로만 UI를 부른다.
- **던전**: 방 BP 상속 구조(`BP_DungeonRoom` → Start/Mob/Event/Boss), 휴면 상태로 배치한 몬스터를 방이 웨이브별로 깨운다.
