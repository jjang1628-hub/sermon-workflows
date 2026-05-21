# Logos-Max 본문중심 연구 자동화 — 전체 워크플로우

## 시스템 개요

Logos-Max는 Logos Bible Software의 원전 자료를 최대한 활용하여
개혁주의 구속사적 관점의 설교 연구를 자동화하는 시스템이다.

**핵심 원칙**: Logos가 먼저, Claude가 분석, 목사님이 최종 판단

---

## 4개 에이전트 역할

```
Logos ──→ Ollama ──→ Claude ──→ 목사님
(출처)   (1차 초안)  (심층 분석)  (최종 권위)
```

| 에이전트 | 역할 | 한계 |
|---------|------|------|
| Logos | 원전 자료 수집 | UI 조작 + Copy만 허용 |
| Ollama | 1차 분석 초안 | 최종 신학 판단 불가 |
| Claude | 심층 신학 분석 | 설교 최종 결론 불가 |
| 목사님 | 최종 권위 | 없음 |

---

## 7단계 자동화 흐름

### 1단계: Logos 연구 레시피 추천

```powershell
python scripts\recommend_logos_research_recipe.py --passage "요한복음 13:14" --mode standard
```

- 본문 장르 자동 감지 (복음서/서신서/시편/예언/내러티브/율법)
- 어떤 Logos 도구를 어떤 순서로 사용할지 레시피 생성
- 출력: `output/research_packs/{slug}-logos-recipe.md`

### 2단계: Logos 캡처 (수동)

Logos에서 직접 자료 캡처:
1. `logos4:` URI로 본문 열기 또는 Logos 앱에서 검색
2. Passage Guide, Exegetical Guide, Bible Word Study 등 열기
3. Ctrl+A → Ctrl+C로 복사
4. `tmp/logos-capture/raw/` 폴더에 `.md` 파일로 저장

```powershell
# 캡처 파일 검증
python scripts\validate_logos_capture.py --capture tmp\logos-capture\raw\<파일명>.md --passage "요한복음 13:14"
```

### 3단계: 연구 팩 준비

```powershell
python scripts\prepare_research_pack.py --passage "요한복음 13:14" --mode standard
```

- 11섹션 연구 팩 생성
- 출력: `output/research_packs/{slug}-research-pack.md`

### 4단계: Ollama 1차 분석 (옵션)

```powershell
python scripts\run_local_research_with_ollama.py ^
  --passage "요한복음 13:14" ^
  --logos-capture tmp\logos-capture\raw\<파일명>.md ^
  --model qwen3:1.7b ^
  --research-mode quick
```

- 로컬 LLM으로 1차 초안 생성
- 반드시 "1차 분석 초안" 레이블 포함
- 출력: `output/local_research/{slug}-local-research.md`

### 5단계: Claude 심층 연구

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python scripts\run_deep_research_with_claude.py ^
  --passage "요한복음 13:14" ^
  --mode deep ^
  --research-pack output\research_packs\jn-13-14-research-pack.md
```

- 20-Pass Multi-Pass Deep Research
- 출력: `output/deep_research/{slug}-deep-research.md`

### 6단계: 감사 3종 세트

```powershell
# Evidence Ledger
python scripts\build_evidence_ledger.py --passage "요한복음 13:14" --research output\deep_research\jn-13-14-deep-research.md

# Claim Audit (12문항)
python scripts\audit_research_claims.py --passage "요한복음 13:14" --ledger output\evidence_ledgers\jn-13-14-evidence-ledger.md

# Counter-Reading (8관점)
python scripts\run_counter_reading.py --passage "요한복음 13:14" --research output\deep_research\jn-13-14-deep-research.md
```

### 7단계: 출력 계약 검증

```powershell
python scripts\validate_output_contract.py --passage "요한복음 13:14" --mode standard
```

---

## 마스터 오케스트레이터 (전체 7단계 한번에)

```powershell
python scripts\run_logos_max_research.py ^
  --passage "요한복음 13:14" ^
  --mode standard ^
  --capture tmp\logos-capture\raw\john-13-14-passage-guide-20260521.md
```

### 옵션

| 옵션 | 설명 |
|------|------|
| `--mode quick\|standard\|deep\|expert` | 운영 모드 |
| `--capture <파일>` | 특정 캡처 파일 지정 |
| `--capture-dir <경로>` | 캡처 파일 검색 경로 |
| `--skip-ollama` | Ollama 1차 분석 건너뜀 |
| `--skip-deep` | Claude 심층 연구 건너뜀 |
| `--skip-audit` | 감사 3종 건너뜀 |
| `--force` | 기존 파일 백업 후 덮어쓰기 |

---

## 운영 모드별 필수 출력

| 모드 | 필수 출력 | 예상 시간 |
|------|-----------|-----------|
| Quick | 7항목 | 15–20분 |
| Standard | 11항목 | 40–60분 |
| Deep | 28항목 | 2–3시간 |
| Expert | 31항목 | 4시간+ |

---

## 파일 구조

```
sermon-workflows/
├── AGENTS.md                          ← 에이전트 역할 정의
├── CLAUDE.md                          ← Claude 트리거 워크플로우
├── prompts/
│   ├── theological_core.md            ← 신학 운영 헌법
│   ├── logos_recipe_planner.md        ← 레시피 플래너 프롬프트
│   ├── ollama_first_pass.md           ← Ollama 1차 분석 프롬프트
│   ├── claude_deep_research.md        ← Claude 심층 연구 프롬프트
│   ├── evidence_ledger_prompt.md      ← Evidence Ledger 프롬프트
│   ├── claim_audit_prompt.md          ← Claim Audit 12문항
│   ├── counter_reading_prompt.md      ← Counter-Reading 8관점
│   └── preacher_internalization.md    ← 설교자 내면화 7가지
├── configs/
│   ├── agent_roles.yaml               ← 에이전트 역할·워크플로우
│   ├── logos_library_categories.yaml  ← 자료 분류 체계
│   ├── logos_resource_priorities.yaml ← 자료 우선순위
│   ├── logos_research_recipes.yaml    ← 장르별 연구 레시피
│   ├── output_contracts.yaml          ← 모드별 필수 출력
│   └── safety_rules.yaml              ← 불변 안전 규칙
├── data/
│   ├── logos_library_inventory.csv    ← 소유 자료 목록
│   └── logos_library_classified.csv   ← 분류된 자료 목록
├── scripts/
│   ├── run_logos_max_research.py      ← 마스터 오케스트레이터 ⭐
│   ├── recommend_logos_research_recipe.py
│   ├── validate_logos_capture.py
│   ├── classify_logos_capture.py
│   ├── prepare_research_pack.py
│   ├── run_local_research_with_ollama.py
│   ├── run_deep_research_with_claude.py
│   ├── build_evidence_ledger.py
│   ├── audit_research_claims.py
│   ├── run_counter_reading.py
│   ├── validate_output_contract.py
│   └── classify_logos_library.py
├── tmp/logos-capture/
│   ├── raw/                           ← Logos 캡처 원본
│   ├── validated/                     ← 검증 통과
│   └── rejected/                      ← 검증 실패
└── output/
    ├── research_packs/                ← 11섹션 연구 팩
    ├── deep_research/                 ← Claude 심층 연구
    ├── evidence_ledgers/              ← Evidence Ledger
    ├── claim_audits/                  ← Claim Audit
    ├── local_research/                ← Ollama 1차 분석
    └── final_sermon_direction/        ← 최종 설교 방향
```
