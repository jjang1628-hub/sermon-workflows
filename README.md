# sermon-workflows

Logos Bible Study 캡처 자료를 기반으로 설교 연구를 자동화하는 워크플로우입니다.
Ollama 로컬 LLM 1차 분석 → Quality Gate v2 판별 → Claude 심층 연구까지 8단계 파이프라인을 제공합니다.

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
├── scripts/              # 파이프라인 스크립트 (Python)
├── prompts/              # 프롬프트 템플릿
├── configs/              # 설정 파일 (YAML)
├── templates/            # 출력 템플릿
├── docs/                 # 설계 문서 및 트러블슈팅
├── input/                # 설교 개요 입력
├── tmp/logos-capture/raw/  # Logos 캡처 원본 (연구 자산, git 포함)
├── requirements.txt
├── SETUP.md              # 새 컴퓨터 셋업 가이드
└── .gitignore
```

---

## 참고

- `docs/troubleshooting.md` — 발생한 버그와 해결책 기록
- `docs/logos_max_workflow.md` — 파이프라인 상세 설계
- `SETUP.md` — 새 컴퓨터 셋업 체크리스트
