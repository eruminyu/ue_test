# 03. SoulCombat 제작 기록

`02-build-plan.md`의 단계를 진행하면서 채운다. 판정: **성공**(전용 MCP 툴만으로) / **우회**(다른 툴·UI 자동화·설계 변경으로) / **사람**(사용자가 에디터에서 직접) / **실패**.

## 진행 상태

- 2026-09-29 준비: 이전 ActionDemo 파일 삭제. 새 프로젝트 `SoulCombat`(UE 5.8.2) 생성: 템플릿 콘텐츠 복사(`Tools/Setup-Project.ps1`), C++ 모듈(`SCAttributeSet`, `SCAbilitySet`) 빌드 성공, 게임플레이 태그 ini 작성, 에디터 실행과 MCP 서버 자동 시작 확인. 커밋 `fa30f08`.
- 2026-09-29 MCP 기능 탐색(`docs/mcp/`, `docs/mcp-cookbook.md`)과 엔진 API 검증(`docs/engine-api-notes.md`) 진행.

## 환경

| 항목 | 값 |
| --- | --- |
| 엔진 | UE 5.8.2 (CL 56702186, 런처 설치, `C:\Program Files\Epic Games\UE_5.8`) |
| 컴파일러 | Visual Studio Community 2026 |
| 프로젝트 | `SoulCombat/SoulCombat.uproject` (Third Person BP 템플릿 콘텐츠 + Combat, Platforming 변형 팩) |
| 에디터 실행 | `-culture=en -ModelContextProtocolStartServer`, MCP `http://127.0.0.1:8000/mcp` |
| 날짜 | 2026-09-29 |

## 단계별 기록

| 단계 | 작업 | 사용한 툴 | 판정 | 사람 개입 | 메모 |
| --- | --- | --- | --- | --- | --- |
| 준비 | 프로젝트 생성, C++ 빌드, 태그, 설정 | 파일 직접 작성, UBT | 해당 없음 (MCP 불필요) | 없음 | 텍스트 파일(C++, ini)은 MCP 없이 직접 작성. 에디터 시작 시 GameFeatures 경고(에셋 매니저 GameFeatureData 항목)가 떴고, "Add entry"로 DefaultGame.ini에 추가됨 |

## 문제와 해결 기록

| 시각 | 증상 | 원인 | 해결 |
| --- | --- | --- | --- |
