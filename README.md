# sermon-workflows

**Logos-first, AI-assisted, Pastor-finalized Sermon Research System**

> 이 프로젝트는 설교문 자동 생성기가 아닙니다.  
> **Logos 연구를 먼저 충분히 수행하도록 강제하는 설교 연구 자동화 시스템**입니다.  
> 필수 Logos 자료가 누락되면 심층 분석으로 넘어가지 않습니다.  
> 목표는 설교자를 대체하는 것이 아니라, 설교자가 본문 아래 더 오래 머물도록 돕는 것입니다.

**핵심 원칙**:
1. Scripture first — 본문이 먼저
2. Logos research second — Logos 연구가 두 번째
3. AI synthesis third — AI 통합이 세 번째
4. Pastor finalization last — 목사님의 확정이 마지막

---

---

## Logos-Max v2 워크플로우

### 새 본문 시작 (권장 흐름)

```powershell
# 1. 새 본문 설정
python scripts/run_logos_max.py `
  --book John --passage 13:14 --context 13:1-17 `
  --genre gospel --step setup

# 2. 레시피 + 체크리스트 자동 생성
python scripts/run_logos_max.py `
  --passage docs/john/13-14/00-passage.yaml --step recipe

# 3. (Logos에서 체크리스트 따라 캡처 → tmp/logos-capture/raw/ 에 저장)

# 4. 캡처 완료 후 Coverage Audit
python scripts/run_logos_max.py `
  --passage docs/john/13-14/00-passage.yaml --step audit

# 5. Coverage Gate 확인 (75점 미만이면 중단)
python scripts/run_logos_max.py `
  --passage docs/john/13-14/00-passage.yaml --step gate

# 6. 통과 시 Deep Research 실행
python scripts/run_logos_max.py `
  --passage docs/john/13-14/00-passage.yaml --step deep
```

### 한 번에 실행 (all 모드)

```powershell
python scripts/run_logos_max.py `
  --book John --passage 13:14 --context 13:1-17 --genre gospel
```

### Logos Coverage Score 기준

| 점수 | 상태 | 판정 |
|------|------|------|
| 90+ | `deep_eligible` | ✅ 심층 연구 즉시 가능 |
| 75–89 | `deep_eligible_with_warning` | ⚠️ 심층 연구 가능, 누락 경고 |
| 60–74 | `review_required` | 🔴 보강 필요, 보류 권장 |
| 0–59 | `insufficient` | 🛑 파이프라인 중단 |

---

## 1. 설치

```powershell
git clone https://github.com/jjang1628-hub/sermon-workflows.git
cd sermon-workflows

python -m venv .venv
.\.venv\Scripts\activate

pip install -r requirements.txt

# Ollama 로컬 모델 (https://ollama.com 에서 Ollama 먼저 설치)
ollama pull qwen3:1.7b     # 경량 (1.1GB)
ollama pull qwen3:8b       # 고품질 (5.2GB, 선택)
```

---

## 2. 실행

### 전체 파이프라인 (표준 모드, Claude API 없이)

```powershell
python scripts/run_logos_max_research.py `
  --passage "요한복음 13:14" `
  --mode standard `
  --capture tmp\logos-capture\raw\john-13-1-17-word-study-20260521.md `
  --skip-deep --force
```

### Claude 심층 분석 포함 (API 키 필요)

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."

python scripts/run_logos_max_research.py `
  --passage "요한복음 13:14" `
  --mode standard `
  --capture tmp\logos-capture\raw\john-13-1-17-word-study-20260521.md `
  --force
```

---

## 3. 파이프라인 구조

```
1단계  레시피 추천       recommend_logos_research_recipe.py
2단계  캡처 검증         validate_logos_capture.py
3단계  연구팩 준비       prepare_research_pack.py
4단계  Ollama 1차 분석   run_local_research_with_ollama.py  ← qwen3:1.7b
5단계  Claude 심층 분석  run_deep_research_with_claude.py   ← Anthropic API
6단계  반론 독해         run_counter_reading.py
7단계  주장 감사         audit_research_claims.py
8단계  증거 원장         build_evidence_ledger.py
```

### Quality Gate v2 판정 기준

| verdict_code | 의미 | 다음 단계 |
|---|---|---|
| `draft_usable` | 초안 사용 가능 | Claude 보강 권장 |
| `claude_required` | Claude 심층 분석 필수 | 5단계 실행 |
| `recapture_required` | Logos 캡처 재수집 필요 | 2단계 재시도 |
| `direct_use_forbidden` | 환각 주석 포함 — 직접 사용 금지 | 환각 항목 제거 후 재실행 |

> `claude_required`는 실패가 아닙니다. 요 13:8 구원론, 13:14 은혜→순종 같은
> 본문 특화 신학 분석은 Claude 심층 단계에서 처리하도록 설계된 정상 분기입니다.

---

## 4. 보안

- `.env`, API 키, 토큰은 **절대 커밋하지 않습니다**
- `output/` (생성 파일), `build/`, `.venv/` 는 `.gitignore`로 제외합니다
- Logos 캡처 원본(`tmp/logos-capture/raw/`)은 연구 자산으로 git에 포함합니다
- Claude API 키는 환경 변수(`ANTHROPIC_API_KEY`)로만 사용합니다

---

## 5. 동기화 (양쪽 컴퓨터 운영)

### 작업 후 저장

```powershell
cd sermon-workflows
git status
git add .
git commit -m "캡처 보강: 요 13:1-17 νίπτω 단어 연구"
git push
```

### 다른 컴퓨터에서 최신 받기

```powershell
git pull
```

### 충돌이 생기면

```powershell
git status           # 충돌 파일 확인
# 수동으로 편집 후
git add .
git commit -m "merge: 충돌 해결"
```

---

## 파일 구조

```
sermon-workflows/
├── config/                         # Logos-Max 설정 (v2 신규)
│   ├── logos_tool_categories.yaml  # 12개 Logos 자료군 정의
│   ├── logos_capture_checklist.yaml
│   ├── logos_resource_priorities.yaml
│   ├── logos_coverage_rubric.yaml
│   └── genre_recipes.yaml          # 장르별 레시피
│
├── templates/                      # 출력 템플릿
│   ├── passage.yaml.template
│   └── logos_coverage_report.md
│
├── scripts/                        # 파이프라인 스크립트
│   ├── create_passage.py           # 0단계: passage.yaml 생성 (v2 신규)
│   ├── build_logos_recipe.py       # 1–2단계: 레시피+체크리스트 (v2 신규)
│   ├── audit_logos_coverage.py     # 4단계: Coverage Audit (v2 신규)
│   ├── gate_deep_research.py       # 5단계: Coverage Gate (v2 신규)
│   ├── run_logos_max.py            # v2 마스터 파이프라인 (v2 신규)
│   ├── run_logos_max_research.py   # AI 7단계 파이프라인 (기존)
│   └── run_all.py                  # 설교 산출물 생성 (기존)
│
├── docs/{book}/{passage}/          # 설교 연구 패키지
│   ├── 00-passage.yaml             # 본문 설정
│   ├── 01-logos-recipe.md          # Logos 도구 사용 순서
│   ├── 02-logos-capture-checklist.md
│   ├── 03-logos-coverage-report.md # Coverage Score 보고서
│   ├── deep-research.md
│   ├── final-direction.md
│   ├── sermon-final.md             # 강단 최종 원고
│   ├── sermon-delivery-compression.md
│   ├── ppt-outline-preaching.md
│   ├── small-group-guide-member.md
│   └── rehearsal-guide.md
│
├── tmp/logos-capture/raw/          # Logos 캡처 원본 (git 포함)
├── requirements.txt
├── SETUP.md
└── .gitignore
```

---

## 참고

- `docs/troubleshooting.md` — 발생한 버그와 해결책 기록
- `docs/logos_max_workflow.md` — 파이프라인 상세 설계
- `SETUP.md` — 새 컴퓨터 셋업 체크리스트
