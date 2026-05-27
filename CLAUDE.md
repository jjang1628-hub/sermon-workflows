# sermon-workflows — Logos-Max v2.1 설교 연구 워크플로우

> 현재 버전: **Logos-Max v2.1** (Logos-first, Quality-Aware Gate)
> 구 워크플로우(v1 run_all.py 계열)는 `input/` + `output/` 경로에 유지됨

---

## Claude의 역할

이 프로젝트에서 Claude는 **설교 연구 파트너 · 파이프라인 엔지니어**다.

- `pastoral-ministry` 스킬을 항상 먼저 로드한다
- 설교·본문·신학 요청 → 스킬 기반 직접 분석
- 파이프라인 작업 → 스크립트 실행 + 결과 검증
- "설교자가 본문 아래 서 있는가"를 항상 먼저 점검한다

---

## 트리거 → 자동 수행

| 트리거 | 수행 |
|--------|------|
| "XXX 연구해줘" / "XXX 설교 준비해줘" | pastoral-ministry 스킬 로드 → 20-Pass 직접 분석 |
| "XXX 본문 연구" / "XXX 분석해줘" | pastoral-ministry 스킬 로드 → 본문 분석 |
| "파이프라인 현황" / "status" | `python scripts/status.py` 실행 |
| "다음 단계 진행" | status.py 확인 → 막힌 단계 파악 → 실행 |

---

## Logos-Max v2.1 파이프라인

### 전체 흐름

```
[Logos 연구] → [Gate] → [AI 심층 분석] → [설교 방향 확정] → [설교 후 반성]
     ↓              ↓           ↓                  ↓                  ↓
   00–05         06 ctx       07 deep            08 dir            09 debrief
```

### 파이프라인 단계 (docs/{book}/{passage}/ 기준)

| 번호 | 파일 | 생성 방법 | 역할 |
|------|------|-----------|------|
| 00 | `00-passage.yaml` | `--step setup` | 본문 메타데이터 |
| 01 | `01-logos-recipe.md` | `--step recipe` | Logos 연구 레시피 |
| 02 | `02-logos-capture-checklist.md` | `--step recipe` | 캡처 체크리스트 |
| 03 | `03-logos-coverage-report.md` | `--step audit` | Coverage Score (0–100) |
| 04 | `04-capture-quality-report.md` | `--step quality` | Quality Score (0–100) |
| 05 | `05-logos-integration-summary.md` | **목사님 직접 작성** | 통찰 + Big Idea + 질문 |
| 06 | `06-research-context.md` | `--step deep` 자동 (Phase A) | AI 분석 교정 기준 주입 |
| 07 | `07-deep-research.md` | `--step deep` (API 필요) | 20-Pass + Pass 21 감사 |
| 08 | `08-final-direction.md` | `--step deep` 자동 (Phase B) | 수렴 분석 + 설교 방향 |
| 09 | `09-pulpit-debrief.md` | `--step debrief` (설교 후) | 강단 데브리프 |

### Gate 임계값

- Coverage Score ≥ 90 **AND** Quality Score ≥ 80 → `logos_max_deep_eligible`
- Coverage Score ≥ 75 **AND** Quality Score ≥ 70 → `deep_eligible`
- Coverage Score 60–74 → `capture_incomplete` (보강 필요)
- Coverage Score < 60 → `gate_blocked` (deep research 차단)
- Coverage Score ≥ 75 이지만 Quality Score < 60 → `quality_blocked`
- `--force-deep`은 테스트 또는 예외 상황에서만 사용하며, 정상 PASS가 아니다.

---

## 주요 명령어

### 현황 확인
```powershell
python scripts/status.py
python scripts/status.py --passage docs/john/13-14/00-passage.yaml
python scripts/status.py --save   # docs/STATUS.md 저장
```

### 새 본문 설정
```powershell
python scripts/run_logos_max.py `
  --book John --passage 13:14 --context 13:1-17 `
  --genre gospel_farewell_discourse --step setup
```

### 전체 파이프라인 (Gate 통과 시)
```powershell
$env:ANTHROPIC_API_KEY = "<ANTHROPIC_API_KEY>"
python scripts/run_logos_max.py `
  --passage docs/john/13-14/00-passage.yaml --step all
```

### Gate 강행 (Coverage 낮아도 진행)
```powershell
python scripts/run_logos_max.py `
  --passage docs/john/13-14/00-passage.yaml `
  --step deep --force-deep --force-reason "Coverage 70, 수동 강행"
```

주의: FORCE는 정상 Gate 통과가 아니다. `status.py`에서 FORCE가 보이면 자료 보강 또는 목회자 확인이 먼저다.

### 단계별 독립 실행
```powershell
python scripts/run_logos_max.py --passage ... --step direction  # 08 재생성
python scripts/run_logos_max.py --passage ... --step debrief    # 09 생성 (설교 후)
python scripts/status.py --passage ...                           # 상세 현황
```

### --dry-run (API 호출 없이 프롬프트 미리보기)
```powershell
python scripts/run_deep_research_with_claude.py `
  --passage "요한복음 13:14" `
  --research-context docs/john/13-14/06-research-context.md `
  --dry-run
```

---

## 핵심 스크립트 맵

| 스크립트 | 역할 |
|---------|------|
| `run_logos_max.py` | 마스터 파이프라인 오케스트레이터 |
| `build_v21_research_context.py` | Phase A: 03+04+05 → 06 (BRIEF+CALIBRATION) |
| `run_deep_research_with_claude.py` | Step 7: Claude API 20-Pass 분석 |
| `generate_final_direction.py` | Phase B: 05+07 → 08 (수렴 분석) |
| `generate_pulpit_debrief.py` | Phase D: 09 강단 데브리프 템플릿 |
| `status.py` | Phase C: 전체 현황 대시보드 |
| `audit_logos_coverage.py` | Step 4: Coverage Score 산출 |
| `audit_capture_quality.py` | Step 5: Quality Score 산출 |
| `gate_deep_research.py` | Step 6: 게이트 판정 |
| `create_passage.py` | Step 1: passage.yaml 생성 |
| `build_logos_recipe.py` | Step 2-3: Logos 레시피·체크리스트 |

---

## 파일 구조

```
docs/
  {book}/
    {passage}/
      00-passage.yaml
      01-logos-recipe.md
      02-logos-capture-checklist.md
      03-logos-coverage-report.md      ← Coverage N/100
      04-capture-quality-report.md     ← Quality N/100
      05-logos-integration-summary.md  ← 목사님 직접 작성 (Gate 통과 전)
      06-research-context.md           ← Phase A 자동 생성
      07-deep-research.md              ← Claude API 생성
      08-final-direction.md            ← Phase B 자동 생성
      09-pulpit-debrief.md             ← 설교 후 작성

tmp/logos-capture/raw/                 ← Logos 수동 캡처 보관
  *.md / *.txt

scripts/                               ← 모든 파이프라인 스크립트

input/                                 ← v1 구 워크플로우 (유지됨)
output/                                ← v1 구 워크플로우 출력 (유지됨)
```

---

## v2.1 핵심 설계 원칙

### 06-research-context.md 구조 (두 구역)
```
── BRIEF 구역 ─────────────────────────────────────────
  Gate Summary · 자료군 강도 지도 · Big Idea · 해석 경계선
  → 20-Pass 시작 전 Claude에 주입 (모든 Pass 안내)

<!-- V21_CALIBRATION_START -->

── CALIBRATION 구역 ────────────────────────────────────
  Per-Pass 표 · 약한 카테고리 금지 지시 · 자동 질문 4개
  → Pass 20 직후 주입 (Pass 21 자체 감사 트리거)
```

### 약한 카테고리 처리 원칙 (환각 방지)
- `MEDIUM`: "Logos 캡처에 있는 내용만 인용. **없는 주석·사실은 생성하지 말고** '추가 Logos 연구 필요'로 대체"
- `MISSING`: "**생성 금지** — 해당 Pass 항목을 '이 카테고리 Logos 연구 필요 [미수집]'으로 대체"

### Phase B 수렴 판정 기준
- Big Idea 한국어 단어 겹침 ≥ 45% → ✅ 수렴
- 20–44% → ⚠️ 부분 수렴
- < 20% → ❌ 발산 (목사님이 07 Pass 18 직접 확인)

---

## 신학 원칙 (항상 적용)

- 개혁주의 (합동측), 언약적·구속사적 해석
- Big Idea: "인간의 문제에도 불구하고 하나님께서 그리스도 안에서 **무엇을** 하시며, 우리는 **어떻게** 응답하는가"
- 그리스도 연결: 억지 알레고리 금지, 본문 자체의 논리에서 자연스럽게
- 인물 영웅화 금지 — 인간의 두려움·욕망·자기보호를 정직하게 드러낸다
- 적용: 복음의 은혜 → 동기 변화 → 순종의 열매

---

## 보안·제약 (항상 준수)

- `ANTHROPIC_API_KEY`는 환경변수로만 사용, 절대 커밋 금지
- Logos 내부 DB 직접 접근 금지 — 공식 UI/Copy/Export로 확보한 자료만 분석
- 유료 자료 대량 스크래핑 금지
- 기존 파일 덮어쓰기 시 backup(.bak) + temp replace(.tmp→rename) 패턴 유지
- `output/` 생성물은 git에서 제외

