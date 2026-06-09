# DESIGN_TOKENS — ModernizePro Compare GUI 디자인 토큰 (정본)

> **재작성 완료(D-044, 2026-06-08).** 형제 제품 ModernizePro의 **셸 구조(상단바+사이드바+탭)·디자인 언어를
> 공유**하되, **주색은 그래파이트(딥 그레이)** 로 분기한다(형제=틸/그린, 우리=그래파이트 → 가족이되 구분).
> ★주색은 **추후 변경 가능**(임시 확정). 모든 화면은 아래 CSS 변수(`:root`)만 참조하므로 한 곳만 바꾸면 전환됨.
> ★**절대 원칙**: "그레이라서 비활성·미완성처럼 보이면 안 된다" — 주요 액션은 **솔리드 딥 그래파이트**(검정 버튼처럼
> 의도적으로), 활성 상태는 **고대비**로. 중간 회색은 *진짜 muted/disabled*에만. 색(상태색)은 *의미*에만 쓴다.

## 1. 색 (hex 정본)

### 그래파이트 스케일 (크롬·주색)
| 토큰 | 값 | 용도 |
|---|---|---|
| `--c-topbar` | `#0F172A` | 상단 앱바 배경(최심 그래파이트) |
| `--c-topbar-fg` | `#E2E8F0` | 앱바 글자 |
| `--c-primary` | `#1E293B` | **주요 액션 버튼 채움**·활성 마커(솔리드=비활성 아님) |
| `--c-primary-hover` | `#0F172A` | 주요 버튼 hover |
| `--c-primary-fg` | `#FFFFFF` | 주색 위 글자 |
| `--c-accent` | `#334155` | 링크·활성 탭 밑줄·강조 텍스트 |

### 중립 (면·테두리·텍스트)
| 토큰 | 값 | 용도 |
|---|---|---|
| `--c-bg` | `#F8FAFC` | 본문 영역 배경 |
| `--c-surface` | `#FFFFFF` | 카드·패널·사이드바 면 |
| `--c-surface-2` | `#F1F5F9` | 보조 면(수치카드·요약줄·테이블 hover) |
| `--c-selected` | `#F1F5F9` | 사이드바 활성 항목 배경 |
| `--c-border` | `#E2E8F0` | 기본 테두리(연) |
| `--c-border-strong` | `#CBD5E1` | 활성 테두리·보조버튼 테두리(진) |
| `--c-text` | `#0F172A` | 본문 강(제목·수치) |
| `--c-text-mut` | `#64748B` | 본문 약(설명·라벨) |
| `--c-text-faint` | `#94A3B8` | 힌트·**비활성/disabled 전용** |

### 상태색 (의미에만 — 무채 셸 위에서 또렷이 튐)
| 토큰 | 값 | soft 배경 | 용도 |
|---|---|---|---|
| `--c-ok` | `#16A34A` | `--c-ok-soft #DCFCE7` | OK·점검통과 |
| `--c-ng` | `#DC2626` | `--c-ng-soft #FEE2E2` | NG·불일치(As-Is↔To-Be) |
| `--c-warn` | `#D97706` | `--c-warn-soft #FEF3C7` | 警告·MISSING |
| `--c-info` | `#2563EB` | `--c-info-soft #DBEAFE` | 실행중/정보(배지에만, 절제) |
| `--c-error` | `#B45309` | — | ERROR(가라앉은 호박) |

> 상태색은 **배지·수치·아이콘·테두리 강조**에만. 큰 면을 채우지 않는다(경고가 비명 지르지 않게).
> 주색(그래파이트)이 무채라 상태색이 **자동으로 강조**된다 = 검증툴에 적합(색=결과).

## 2. 셸 레이아웃 (형제 구조)
- **상단 앱바**: 높이 `40px`, bg `--c-topbar`, 좌측=제품명(`ModernizePro Compare`)·프로젝트 컨텍스트, 우측=알림 등.
- **좌측 사이드바**: 폭 `240px`, bg `--c-surface`, `border-right:1px solid --c-border`.
  - 항목: `padding:8px 12px`, 글자 `13px`. **활성** = bg `--c-selected` + 좌측 `2px` 바 `--c-primary` + 글자 `--c-text`(강).
- **상단 탭바**: 높이 `44px`, bg `--c-surface`, `border-bottom:1px solid --c-border`.
  - 탭: `padding:0 14px`, `13px/500`. **활성** = 글자 `--c-text` + 하단 `2px` `--c-primary`. 비활성 = `--c-text-mut`.
- **본문**: bg `--c-bg`, `padding:20px 24px`.

## 3. 컴포넌트
- **카드/패널**: `border-radius:8px`, `border:1px solid --c-border`, bg `--c-surface`, `padding:16px`. 그림자 최소(테두리 위주).
- **수치 카드**(PROJECTS/TABLES/件数): bg `--c-surface`, 테두리, `radius:8px`, 라벨 `11px` 대문자 `--c-text-mut`, 수치 `22px/600 --c-text`.
- **진행바**: 트랙 `--c-border`, 채움 `--c-ok`(또는 분절 셀). 경고분은 `--c-warn`.
- **데이터 테이블**: 헤더 `11px` 대문자 `--c-text-mut`, 행 `border-bottom:1px --c-border`, hover `--c-surface-2`.
- **버튼**
  - 주요: bg `--c-primary` / 글자 흰색 / `radius:6px` / `padding:8px 16px` / `500`. hover `--c-primary-hover`. (솔리드 딥 = 비활성 아님)
  - 보조(ghost): bg 흰색 / `border:1px --c-border-strong` / 글자 `--c-text` / `radius:6px`.
  - 위험(삭제): 글자·테두리 `--c-ng`.
  - **disabled만** `--c-text-faint` + `opacity:.55` — 활성과 시각적으로 확실히 다르게.
- **상태 배지/pill**: soft 배경 + 상태색 글자, `radius:4px`, `11px/500`, `padding:2px 8px`. (예: `OK` `NG` `MISSING` `ERROR` `RUNNING`)
- **★커스텀 드롭다운**(시스템 select 금지 — 프로그램다운): 트리거=흰 면·`border:1px --c-border-strong`·`radius:6px`·우측 chevron 아이콘; 메뉴=흰 카드·`border:1px --c-border`·`radius:8px`·그림자·항목 hover `--c-surface-2`·선택 항목 체크. 키보드(↑↓/Enter/Esc) 동작. 모든 `<select>`를 이걸로 대체.

## 4. 타이포·아이콘
- 폰트: 시스템 산세리프(한/일 포함) — `-apple-system, "Segoe UI", "Hiragino Kaku Gothic ProN", "Noto Sans JP", sans-serif`.
- 굵기 **400/500/600**(600은 수치·제목 강조만, 700 금지).
- 크기: 앱 제목 `14px/600`, 탭 `13px/500`, 패널 제목 `15px/600`, 본문 `13px/400`, 라벨 `11px/500` 대문자, 수치 `22px/600`.
- 아이콘: Tabler outline, 인라인 `14~17px`, 색 부모 상속(상태 아이콘만 상태색).

## 5. 적용 규칙
- 위 값을 `:root` CSS 변수로 정의하고 **전 화면이 변수만 참조**(하드코딩 hex 산재 금지) → 주색 변경은 변수 한 곳.
- **화면(템플릿/CSS/JS)만 변경. 라우트·코어·스키마 손대지 말 것. 270 테스트 녹색 유지.**
- 일관성: 같은 의미는 같은 토큰. 임의 회색 추가 금지(스케일 안에서).
- 시안(채팅 렌더)은 폰트·미세여백이 실제와 다를 수 있음 — **이 문서의 값이 정본.**
